from django import forms
from .models import Appointment


class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            "providers",
            "recipients",
            "activities",
            "price",
            "auto_price",
            "is_blocked",
            "date",
            "start_time",
            "end_time",
            "auto_end_time",
            "prevents_overlap",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save(clean=False)

        return instance
