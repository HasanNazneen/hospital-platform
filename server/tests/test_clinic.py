import pytest
from clinic.models import Prescription
from .conftest import future_slot, make_appointment

pytestmark = pytest.mark.django_db


def test_patient_books_appointment(api, patient1, doctor):
    api.force_authenticate(patient1[0])
    r = api.post("/api/appointments/", {"doctor": doctor.id, "slot": future_slot().isoformat()}, format="json")
    assert r.status_code == 201 and r.json()["status"] == "booked"


def test_double_booking_rejected(api, patient1, patient2, doctor):
    slot = future_slot().isoformat()
    api.force_authenticate(patient1[0])
    assert api.post("/api/appointments/", {"doctor": doctor.id, "slot": slot}, format="json").status_code == 201
    api.force_authenticate(patient2[0])
    r = api.post("/api/appointments/", {"doctor": doctor.id, "slot": slot}, format="json")
    assert r.status_code == 400 and "error" in r.json()


def test_past_slot_rejected(api, patient1, doctor):
    api.force_authenticate(patient1[0])
    r = api.post("/api/appointments/", {"doctor": doctor.id, "slot": future_slot(-2).isoformat()}, format="json")
    assert r.status_code == 400


def test_patient_cannot_book_with_non_doctor(api, patient1, patient2):
    api.force_authenticate(patient1[0])
    r = api.post("/api/appointments/", {"doctor": patient2[0].id, "slot": future_slot().isoformat()}, format="json")
    assert r.status_code == 400


def test_patient_only_sees_own_appointments(api, patient1, patient2, doctor):
    make_appointment(patient1[1], doctor, 5)
    make_appointment(patient2[1], doctor, 6)
    api.force_authenticate(patient1[0])
    assert api.get("/api/appointments/").json()["count"] == 1


def test_patient_can_only_cancel(api, patient1, doctor):
    appt = make_appointment(patient1[1], doctor)
    api.force_authenticate(patient1[0])
    assert api.patch(f"/api/appointments/{appt.id}/", {"status": "done"}, format="json").status_code == 403
    assert api.patch(f"/api/appointments/{appt.id}/", {"status": "cancelled"}, format="json").status_code == 200


def test_search_and_filter_appointments(api, admin, patient1, patient2, doctor):
    make_appointment(patient1[1], doctor, 5)
    make_appointment(patient2[1], doctor, 6)
    api.force_authenticate(admin)
    assert api.get("/api/appointments/?search=Pat One").json()["count"] == 1
    assert api.get("/api/appointments/?status=cancelled").json()["count"] == 0


def test_doctor_writes_prescription_patient_cannot(api, patient1, doctor):
    appt = make_appointment(patient1[1], doctor)
    body = {"appointment": appt.id, "items": [{"drug": "Paracetamol", "dose": "500mg", "days": 3}]}
    api.force_authenticate(patient1[0])
    assert api.post("/api/prescriptions/", body, format="json").status_code == 403
    api.force_authenticate(doctor)
    assert api.post("/api/prescriptions/", body, format="json").status_code == 201


def test_prescription_needs_medicines(api, patient1, doctor):
    appt = make_appointment(patient1[1], doctor)
    api.force_authenticate(doctor)
    r = api.post("/api/prescriptions/", {"appointment": appt.id, "items": []}, format="json")
    assert r.status_code == 400


def test_patient_sees_only_own_prescriptions(api, patient1, patient2, doctor):
    for _, p in (patient1, patient2):
        appt = make_appointment(p, doctor, 5 + p.id)
        Prescription.objects.create(appointment=appt, items=[{"drug": "X", "dose": "1"}])
    api.force_authenticate(patient1[0])
    assert api.get("/api/prescriptions/").json()["count"] == 1


def test_unauthenticated_access_blocked(api):
    for url in ("/api/appointments/", "/api/patients/", "/api/prescriptions/"):
        assert api.get(url).status_code == 401