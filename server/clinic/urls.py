from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (HospitalViewSet, PatientViewSet, AppointmentViewSet,
                    PrescriptionViewSet, DoctorListView)

router = DefaultRouter()
router.register("hospitals", HospitalViewSet, basename="hospital")
router.register("patients", PatientViewSet, basename="patient")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("prescriptions", PrescriptionViewSet, basename="prescription")

urlpatterns = [
    path("doctors/", DoctorListView.as_view()),
    path("", include(router.urls)),
]