from django.shortcuts import render
import logging
from rest_framework import viewsets, generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from accounts.models import User
from accounts.permissions import IsAdminRole
from accounts.serializers import UserSerializer
from .filters import AppointmentFilter
from .models import Hospital, Patient, Appointment, Prescription
from .serializers import (HospitalSerializer, PatientSerializer,
                          AppointmentSerializer, PrescriptionSerializer)

log = logging.getLogger(__name__)

class AdminOnlyDelete:
    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminRole()]
        return super().get_permissions()

class HospitalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer

class DoctorListView(generics.ListAPIView):
    queryset = User.objects.filter(role="doctor")
    serializer_class = UserSerializer
    search_fields = ["first_name", "last_name", "email"]

class PatientViewSet(AdminOnlyDelete, viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    search_fields = ["name", "phone", "source_patient_id"]
    filterset_fields = ["hospital"]
    ordering_fields = ["name", "id"]

    def get_queryset(self):
        u = self.request.user
        qs = Patient.objects.select_related("hospital").order_by("id")
        if u.role == "admin":
            return qs
        if u.role == "doctor":
            return qs.filter(appointment__doctor=u).distinct()
        return qs.filter(user=u)

    def perform_create(self, serializer):
        u = self.request.user
        if u.role == "patient":
            if Patient.objects.filter(user=u).exists():
                raise ValidationError("You already have a patient profile.")
            obj = serializer.save(user=u, source_patient_id=f"SELF-{u.id}")
        elif u.role == "admin":
            if not serializer.validated_data.get("source_patient_id"):
                raise ValidationError({"source_patient_id": "This field is required."})
            obj = serializer.save()
        else:
            raise PermissionDenied("Doctors cannot create patients.")
        log.info("Patient created id=%s by user=%s", obj.id, u.id)

class AppointmentViewSet(AdminOnlyDelete, viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    filterset_class = AppointmentFilter
    search_fields = ["patient__name", "doctor__first_name", "doctor__last_name"]
    ordering_fields = ["slot"]

    def get_queryset(self):
        u = self.request.user
        qs = Appointment.objects.select_related("patient", "doctor").order_by("slot")
        if u.role == "admin":
            return qs
        if u.role == "doctor":
            return qs.filter(doctor=u)
        return qs.filter(patient__user=u)

    def perform_create(self, serializer):
        u = self.request.user
        if u.role == "patient":
            patient = Patient.objects.filter(user=u).first()
            if not patient:
                raise ValidationError("Create your patient profile first.")
            obj = serializer.save(patient=patient)
        elif u.role == "admin":
            if "patient" not in serializer.validated_data:
                raise ValidationError({"patient": "This field is required."})
            obj = serializer.save()
        else:
            raise PermissionDenied("Doctors cannot book appointments.")
        log.info("Appointment booked id=%s by user=%s", obj.id, u.id)

    def perform_update(self, serializer):
        u = self.request.user
        changed = set(serializer.validated_data)
        if u.role in ("patient", "doctor"):
            if changed - {"status"}:
                raise PermissionDenied("You can only change the status.")
            if u.role == "patient" and serializer.validated_data.get("status") != "cancelled":
                raise PermissionDenied("Patients can only cancel appointments.")
        obj = serializer.save()
        log.info("Appointment updated id=%s by user=%s", obj.id, u.id)

class PrescriptionViewSet(AdminOnlyDelete, viewsets.ModelViewSet):
    serializer_class = PrescriptionSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ["notes", "appointment__patient__name"]

    def get_queryset(self):
        u = self.request.user
        qs = Prescription.objects.select_related("appointment").order_by("-id")
        if u.role == "admin":
            return qs
        if u.role == "doctor":
            return qs.filter(appointment__doctor=u)
        return qs.filter(appointment__patient__user=u)

    def perform_create(self, serializer):
        if self.request.user.role == "patient":
            raise PermissionDenied("Patients cannot write prescriptions.")
        obj = serializer.save()
        log.info("Prescription created id=%s by user=%s", obj.id, self.request.user.id)

    def perform_update(self, serializer):
        if self.request.user.role == "patient":
            raise PermissionDenied("Patients cannot edit prescriptions.")
        serializer.save()
# Create your views here.
