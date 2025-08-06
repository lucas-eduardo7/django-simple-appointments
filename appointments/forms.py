from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import (
    Appointment,
    AppointmentProvider,
    AppointmentRecipient,
    AppointmentActivity,
)


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

    # M2M fields that use intermediate models
    M2M_CONFIG = [
        ("providers", AppointmentProvider, "provider"),
        ("recipients", AppointmentRecipient, "recipient"),
        ("activities", AppointmentActivity, "activity"),
    ]

    def clean(self):
        cleaned_data = super().clean()

        temp_appointment = self._build_temp_instance(cleaned_data)
        errors = self._validate_all_m2m(temp_appointment, cleaned_data)

        if errors:
            raise ValidationError(errors)

        return cleaned_data

    def _build_temp_instance(self, cleaned_data):
        temp_appointment = self.instance or Appointment()
        for field, value in cleaned_data.items():
            if field not in ["providers", "recipients", "activities"]:
                setattr(temp_appointment, field, value)
        return temp_appointment

    def _validate_all_m2m(self, temp_appointment, cleaned_data):
        errors = []
        for form_field, model_class, fk_field in self.M2M_CONFIG:
            items = cleaned_data.get(form_field) or []
            errors.extend(
                self._validate_m2m_field(
                    form_field, items, model_class, fk_field, temp_appointment
                )
            )
        return errors

    def _validate_m2m_field(
        self, form_field, items, model_class, fk_field, temp_appointment
    ):
        errors = []
        for item in items:
            obj = model_class(**{"appointment": temp_appointment, fk_field: item})
            try:
                obj.full_clean(exclude=["appointment"])
            except ValidationError as e:
                errors.append(
                    ValidationError(
                        f"Invalid {form_field[:-1]} '{item}': {', '.join(e.messages)}"
                    )
                )
        return errors

    def save(self, commit=True):
        with transaction.atomic():
            instance = super().save(commit=False)

            if commit:
                instance.save(clean=False)
                self.save_m2m()
        return instance
