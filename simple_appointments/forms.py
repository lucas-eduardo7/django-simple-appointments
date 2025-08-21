from django import forms
from .models import Appointment
from .mixin_forms import AppointmentValidatorPipeline


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
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        super().clean()
        AppointmentValidatorPipeline(self).run()
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save(clean=False)
            self.save_m2m()
        return instance
