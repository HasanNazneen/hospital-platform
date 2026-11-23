from django_filters import rest_framework as df
from .models import Appointment

class AppointmentFilter(df.FilterSet):
    slot_after = df.IsoDateTimeFilter(field_name="slot", lookup_expr="gte")
    slot_before = df.IsoDateTimeFilter(field_name="slot", lookup_expr="lte")

    class Meta:
        model = Appointment
        fields = ["status", "doctor", "patient"]