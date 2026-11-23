import pytest
from accounts.models import User
from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_register_always_creates_patient(api):
    r = api.post("/api/auth/register/", {"email": "new@test.com", "first_name": "New",
                                         "password": PASSWORD, "role": "admin"}, format="json")
    assert r.status_code == 201
    assert User.objects.get(email="new@test.com").role == "patient"


def test_register_duplicate_email_uses_error_format(api):
    body = {"email": "dup@test.com", "first_name": "D", "password": PASSWORD}
    api.post("/api/auth/register/", body, format="json")
    r = api.post("/api/auth/register/", body, format="json")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == 400


def test_register_weak_password_rejected(api):
    r = api.post("/api/auth/register/", {"email": "w@test.com", "first_name": "W",
                                         "password": "123"}, format="json")
    assert r.status_code == 400


def test_login_and_me(api, doctor):
    r = api.post("/api/auth/login/", {"email": "doc@test.com", "password": PASSWORD}, format="json")
    assert r.status_code == 200 and "access" in r.json() and "refresh" in r.json()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    me = api.get("/api/auth/me/")
    assert me.status_code == 200 and me.json()["role"] == "doctor"


def test_login_wrong_password(api, doctor):
    r = api.post("/api/auth/login/", {"email": "doc@test.com", "password": "wrong"}, format="json")
    assert r.status_code == 401


def test_me_requires_auth(api):
    assert api.get("/api/auth/me/").status_code == 401


def test_refresh_rotates_and_old_token_is_blacklisted(api, doctor):
    tokens = api.post("/api/auth/login/", {"email": "doc@test.com", "password": PASSWORD},
                      format="json").json()
    first = api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert first.status_code == 200
    again = api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert again.status_code == 401