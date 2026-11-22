
from django.conf import settings
from django.db import models

class Hospital(models.Model):
    name = models.CharField(max_length=120); city = models.CharField(max_length=60)

class Bed(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="beds")
    label = models.CharField(max_length=20)

class Patient(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT)
    source_patient_id = models.CharField(max_length=40)        # original ID from the hospital
    master_patient = models.ForeignKey("self", null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name="duplicates")
    name = models.CharField(max_length=120, db_index=True)
    dob = models.DateField(null=True); phone = models.CharField(max_length=20, blank=True)

class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED="booked"; DONE="done"; CANCELLED="cancelled"
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="appointments")
    slot = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    class Meta:
        indexes = [models.Index(fields=["doctor", "slot"])]
        constraints = [models.UniqueConstraint(fields=["doctor", "slot"],
                       condition=~models.Q(status="cancelled"), name="no_double_booking")]

class Prescription(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    items = models.JSONField(default=list)       # [{drug, dose, days}]
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to="rx/", null=True, blank=True)

class Admission(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    bed = models.ForeignKey(Bed, null=True, on_delete=models.SET_NULL)
    admit_date = models.DateField()
    discharge_date = models.DateField(null=True, blank=True)   # NULL = still admitted / missing
    diagnosis_raw = models.TextField(blank=True)               # free text kept as-is
    diagnosis_code = models.CharField(max_length=10, blank=True)  # ICD-10 when mappable
    data_quality_flag = models.CharField(max_length=30, blank=True)
    class Meta:
        indexes = [models.Index(fields=["patient", "admit_date"])]
# Create your models here.
