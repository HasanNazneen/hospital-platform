from django.shortcuts import render

# Create your views here.
from django.core.cache import cache
from django.db import connection
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from clinic.models import Hospital


def _one(sql, params):
    with connection.cursor() as c:
        c.execute(sql, params)
        return c.fetchone()


def compute(hid=None):
    hp = [hid] if hid else []
    p_clause = "AND p.hospital_id = %s" if hid else ""   # fixed text, no user input inside

    los = _one(f"""SELECT ROUND(AVG(a.discharge_date - a.admit_date)::numeric, 2)
                   FROM clinic_admission a JOIN clinic_patient p ON p.id = a.patient_id
                   WHERE a.discharge_date IS NOT NULL {p_clause}""", hp)[0]

    total_beds = _one(f"SELECT COUNT(*) FROM clinic_bed {'WHERE hospital_id = %s' if hid else ''}", hp)[0]
    occupied = _one(f"""SELECT COUNT(DISTINCT a.bed_id)
                        FROM clinic_admission a JOIN clinic_bed b ON b.id = a.bed_id
                        WHERE a.discharge_date IS NULL AND a.data_quality_flag = ''
                        {'AND b.hospital_id = %s' if hid else ''}""", hp)[0]

    readmit, discharged = _one(f"""
        WITH adm AS (
          SELECT p.hospital_id, a.discharge_date,
                 LEAD(a.admit_date) OVER (
                   PARTITION BY COALESCE(p.master_patient_id, p.id) ORDER BY a.admit_date
                 ) AS next_admit
          FROM clinic_admission a JOIN clinic_patient p ON p.id = a.patient_id)
        SELECT COUNT(*) FILTER (WHERE next_admit - discharge_date BETWEEN 0 AND 30), COUNT(*)
        FROM adm WHERE discharge_date IS NOT NULL {'AND hospital_id = %s' if hid else ''}""", hp)

    flagged = _one(f"""SELECT COUNT(*) FROM clinic_admission a
                       JOIN clinic_patient p ON p.id = a.patient_id
                       WHERE a.data_quality_flag = 'missing_discharge' {p_clause}""", hp)[0]
    unmapped = _one(f"""SELECT COUNT(*) FROM clinic_admission a
                        JOIN clinic_patient p ON p.id = a.patient_id
                        WHERE a.diagnosis_code = '' AND a.diagnosis_raw <> '' {p_clause}""", hp)[0]

    return {
        "avg_length_of_stay_days": float(los) if los is not None else None,
        "bed_occupancy_pct": round(100 * occupied / total_beds, 1) if total_beds else 0,
        "readmission_rate_30d_pct": round(100 * readmit / discharged, 1) if discharged else 0,
        "total_beds": total_beds,
        "occupied_beds": occupied,
        "discharged_admissions": discharged,
        "data_quality": {"missing_discharge_flagged": flagged, "unmapped_diagnoses": unmapped},
    }


class DashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        hid = request.query_params.get("hospital")
        if hid is not None:
            if not hid.isdigit():
                raise ValidationError({"hospital": "Must be a number."})
            hid = int(hid)
        key = f"dashboard:v1:{hid or 'all'}"
        data = cache.get(key)
        if data is None:
            data = compute(hid)
            if hid is None:
                data["by_hospital"] = [{"id": h.id, "name": h.name, **compute(h.id)}
                                       for h in Hospital.objects.order_by("id")]
            cache.set(key, data, 300)   # 5-minute cache helps the under-2-second target
        return Response(data)