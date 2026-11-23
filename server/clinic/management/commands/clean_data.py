import re
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from clinic.models import Admission, Patient

# Order matters: specific rules first. Codes are illustrative ICD-10 mappings.
ICD_RULES = [
    (r"dengue|ns1", "A90"),
    (r"malaria", "B54"),
    (r"\buti\b|urinary|micturition", "N39.0"),
    (r"chest pain|\bmi\b|cardiac", "R07.9"),
    (r"diabet|\bdm\d?\b", "E11.9"),
    (r"\bhtn\b|hypertension|high bp", "I10"),
    (r"gastroenteritis|loose motion", "A09"),
    (r"pneumonia|\blrti\b", "J18.9"),
    (r"fracture", "S52.9"),
    (r"appendicitis", "K37"),
    (r"asthma", "J45.9"),
    (r"fever|pyrexia", "R50.9"),
]


def norm_name(s):
    s = s.lower()
    s = re.sub(r"\b(mr|mrs|ms|dr|shri|smt)\b\.?", " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_phone(p):
    digits = re.sub(r"\D", "", p or "")
    return digits[-10:] if len(digits) >= 10 else ""


class Command(BaseCommand):
    help = "Deduplicate patients, map diagnoses to ICD-10, flag bad admission records"

    @transaction.atomic
    def handle(self, *args, **opts):
        # 1. Link duplicate patients to a master record (nothing is deleted)
        by_name, by_phone, linked = {}, {}, 0
        for p in Patient.objects.order_by("id"):
            if not p.dob:
                continue
            k1 = (norm_name(p.name), p.dob)
            ph = norm_phone(p.phone)
            k2 = (ph, p.dob) if ph else None
            master_id = by_name.get(k1) or (by_phone.get(k2) if k2 else None)
            if master_id and master_id != p.id:
                if p.master_patient_id != master_id:
                    p.master_patient_id = master_id
                    p.save(update_fields=["master_patient"])
                    linked += 1
            else:
                by_name[k1] = p.id
                if k2:
                    by_phone[k2] = p.id

        # 2. Map free-text diagnoses to codes; leave unmappable ones blank
        mapped = 0
        for a in Admission.objects.filter(diagnosis_code="").exclude(diagnosis_raw=""):
            text = a.diagnosis_raw.lower()
            for pattern, code in ICD_RULES:
                if re.search(pattern, text):
                    a.diagnosis_code = code
                    a.save(update_fields=["diagnosis_code"])
                    mapped += 1
                    break

        # 3. Flag admissions with no discharge date that are too old to still be inpatients
        cutoff = date.today() - timedelta(days=60)
        flagged = Admission.objects.filter(
            discharge_date__isnull=True, admit_date__lt=cutoff, data_quality_flag=""
        ).update(data_quality_flag="missing_discharge")

        total = Admission.objects.count()
        unmapped = Admission.objects.filter(diagnosis_code="").count()
        self.stdout.write(self.style.SUCCESS(
            f"Duplicates linked: {linked}\n"
            f"Diagnoses mapped: {mapped}\n"
            f"Still unmapped/blank: {unmapped} of {total} ({unmapped * 100 / max(total, 1):.1f}%)\n"
            f"Flagged missing discharge: {flagged}"))