from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from clinic.models import Appointment, Hospital, Patient

PASSWORD = "Strong#Pass123"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(name="Test Hospital", city="Jaipur")


def make_user(email, role):
    return User.objects.create_user(username=email, email=email, password=PASSWORD, role=role)


@pytest.fixture
def doctor(db):
    return make_user("doc@test.com", "doctor")


@pytest.fixture
def admin(db):
    return make_user("admin@test.com", "admin")


def make_patient(email, hospital, name="Pat One"):
    user = make_user(email, "patient")
    patient = Patient.objects.create(user=user, hospital=hospital, source_patient_id=f"T-{user.id}",
                                     name=name, dob=date(1990, 1, 1), phone="9999999999")
    return user, patient


@pytest.fixture
def patient1(hospital):
    return make_patient("p1@test.com", hospital, "Pat One")


@pytest.fixture
def patient2(hospital):
    return make_patient("p2@test.com", hospital, "Pat Two")


def future_slot(days=5):
    return timezone.now() + timedelta(days=days)


def make_appointment(patient, doctor, days=5):
    return Appointment.objects.create(patient=patient, doctor=doctor, slot=future_slot(days))