
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = "patient"; DOCTOR = "doctor"; ADMIN = "admin"
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
# Create your models here.
