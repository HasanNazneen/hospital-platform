from django.utils import timezone
from rest_framework import serializers
from .models import Hospital, Patient, Appointment, Prescription

MAX_UPLOAD = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}

class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ["id", "name", "city"]

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "hospital", "source_patient_id", "name", "dob", "phone"]
        extra_kwargs = {"source_patient_id": {"required": False}}

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ["id", "patient", "patient_name", "doctor", "doctor_name", "slot", "status"]
        extra_kwargs = {"patient": {"required": False}}

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.email

    def validate_doctor(self, value):
        if value.role != "doctor":
            raise serializers.ValidationError("Selected user is not a doctor.")
        return value

    def validate_slot(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Slot must be in the future.")
        return value

    def validate(self, data):
        doctor = data.get("doctor", getattr(self.instance, "doctor", None))
        slot = data.get("slot", getattr(self.instance, "slot", None))
        qs = Appointment.objects.filter(doctor=doctor, slot=slot).exclude(status="cancelled")
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This slot is already booked.")
        return data

class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ["id", "appointment", "items", "notes", "attachment"]

    def validate_items(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Add at least one medicine.")
        for item in value:
            if not item.get("drug") or not item.get("dose"):
                raise serializers.ValidationError("Each medicine needs a drug name and dose.")
        return value

    def validate_attachment(self, f):
        if f.size > MAX_UPLOAD:
            raise serializers.ValidationError("File must be 5 MB or smaller.")
        if f.content_type not in ALLOWED_TYPES:
            raise serializers.ValidationError("Only JPG, PNG or PDF files are allowed.")
        return f

    def validate_appointment(self, appt):
        user = self.context["request"].user
        if user.role == "doctor" and appt.doctor_id != user.id:
            raise serializers.ValidationError("This is not your appointment.")
        return appt