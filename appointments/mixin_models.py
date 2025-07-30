from datetime import datetime, date, timedelta
from django.apps import apps
from django.core.exceptions import ValidationError
from .utils import (
    validate_time_cohesion,
    validate_appointments_conflicts,
    validate_blocked_cohesion,
)


class AppointmentValidateMixin:
    def run_validations(self):
        self._set_null_end_time()
        self._validate_time()
        self._validate_blocked()
        self._validate_conflicts()

    def _get_queryset(self):
        Appointment = apps.get_model("appointments", "Appointment")
        return Appointment.objects.filter(
            prevents_overlap=True,
            date=self.date,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        )

    def _set_null_end_time(self):
        if self.end_time is None:
            self.end_time = self.start_time

    def _validate_time(self):
        time_cohesion = validate_time_cohesion(self.start_time, self.end_time)
        if time_cohesion:
            raise ValidationError(time_cohesion)

    def _validate_blocked(self):
        blocked_cohesion = validate_blocked_cohesion(
            self.is_blocked, self.prevents_overlap
        )
        if blocked_cohesion:
            raise ValidationError(blocked_cohesion)

    def _validate_conflicts(self):
        if not self.pk:
            return

        queryset = self._get_queryset()
        for provider in self.providers.all():
            conflict_message = validate_appointments_conflicts(self, provider, queryset)

            if conflict_message:
                raise ValidationError(conflict_message)


class ProviderValidateMixin:
    def run_validations(self):
        self._validate_conflicts()

    def _validate_conflicts(self):
        conflict_message = validate_appointments_conflicts(
            self.appointment, self.provider
        )
        if conflict_message:
            raise ValidationError(conflict_message)


class UpdateAutoFieldsMixin:
    def _get_instance(self):
        return self

    def update_fields(self):
        self._set_price()
        self._set_end_time()

    def _set_price(self):
        instance = self._get_instance()
        if not instance.auto_price or not instance.pk:
            return

        total = sum(a.price for a in instance.activities.all())
        instance.price = total

    def _set_end_time(self):
        instance = self._get_instance()
        if not instance.auto_end_time or not instance.pk:
            return

        total_duration = sum(
            (a.duration_time for a in instance.activities.all()), timedelta()
        )
        dummy_datetime = datetime.combine(date.min, instance.start_time)
        result_datetime = dummy_datetime + total_duration
        instance.end_time = result_datetime.time()


class ActivityMixin(UpdateAutoFieldsMixin):
    def _get_instance(self):
        return self.appointment

    def _set_price(self):
        super()._set_price()
        self.appointment.save(update_fields=["price"])

    def _set_end_time(self):
        super()._set_end_time()
        self.appointment.save(update_fields=["end_time"])
