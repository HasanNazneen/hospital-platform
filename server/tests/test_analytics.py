from datetime import date

import pytest
from analytics.views import compute
from clinic.management.commands.clean_data import norm_name, norm_phone
from clinic.models import Admission, Bed
from .conftest import make_patient

pytestmark = pytest.mark.django_db


def test_name_and_phone_normalisation():
    assert norm_name("Mr.  RAJ   Kumar") == norm_name("raj kumar")
    assert norm_phone("+91 98765-43210") == "9876543210"
    assert norm_phone("123") == ""


def test_length_of_stay_and_readmission(hospital):
    _, p = make_patient("a@test.com", hospital)
    Admission.objects.create(patient=p, admit_date=date(2026, 1, 1), discharge_date=date(2026, 1, 4))
    Admission.objects.create(patient=p, admit_date=date(2026, 1, 14), discharge_date=date(2026, 1, 17))
    data = compute()
    assert data["avg_length_of_stay_days"] == 3.0
    assert data["readmission_rate_30d_pct"] == 50.0


def test_duplicate_patient_counts_as_same_person_for_readmission(hospital):
    _, master = make_patient("m@test.com", hospital)
    _, dup = make_patient("d@test.com", hospital, "Pat Dup")
    dup.master_patient = master
    dup.save()
    Admission.objects.create(patient=master, admit_date=date(2026, 1, 1), discharge_date=date(2026, 1, 3))
    Admission.objects.create(patient=dup, admit_date=date(2026, 1, 10), discharge_date=date(2026, 1, 12))
    assert compute()["readmission_rate_30d_pct"] == 50.0


def test_bed_occupancy(hospital):
    _, p = make_patient("b@test.com", hospital)
    beds = [Bed.objects.create(hospital=hospital, label=f"B{i}") for i in range(4)]
    Admission.objects.create(patient=p, bed=beds[0], admit_date=date.today())
    assert compute()["bed_occupancy_pct"] == 25.0


def test_dashboard_is_admin_only(api, admin, patient1):
    api.force_authenticate(patient1[0])
    assert api.get("/api/analytics/dashboard/").status_code == 403
    api.force_authenticate(admin)
    assert api.get("/api/analytics/dashboard/").status_code == 200