from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Hospital, Bed, Patient, Appointment, Prescription, Admission,LabTest, Billing

for m in (Hospital, Bed, Patient, Appointment, Prescription, Admission, LabTest,Billing ):
    admin.site.register(m)