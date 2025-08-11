from .models import Appointment
from datetime import datetime, timedelta, date
from .utils import (
    validate_time_cohesion,
    validate_blocked_cohesion,
    validate_appointments_conflicts,
)


class TimeValidationMixin:
    @staticmethod
    def validate_time(form):
        start_time = form.cleaned_data.get("start_time")
        time_cohesion = validate_time_cohesion(
            start_time, form.cleaned_data.get("end_time")
        )
        if time_cohesion:
            form.add_error("start_time", time_cohesion)


class BlockedValidationMixin:
    @staticmethod
    def validate_blocked(form):
        blocked_cohesion = validate_blocked_cohesion(
            form.cleaned_data.get("is_blocked"),
            form.cleaned_data.get("prevents_overlap"),
        )
        if blocked_cohesion:
            form.add_error("is_blocked", blocked_cohesion)


class ConflictValidationMixin:
    @staticmethod
    def validate_conflicts(form):
        queryset = ConflictValidationMixin._get_queryset(form)
        temp_instance = ConflictValidationMixin._build_temp_instance(form)
        for provider in form.cleaned_data.get("providers"):
            conflict_message = validate_appointments_conflicts(
                temp_instance, provider, queryset
            )

            if conflict_message:
                form.add_error("start_time", conflict_message)
                break

    @staticmethod
    def _get_queryset(form):
        return Appointment.objects.filter(
            prevents_overlap=True,
            date=form.cleaned_data.get("date"),
            start_time__lt=form.cleaned_data.get("end_time"),
            end_time__gt=form.cleaned_data.get("start_time"),
        )

    @staticmethod
    def _build_temp_instance(form):
        temp_appointment = form.instance or Appointment()
        for field, value in form.cleaned_data.items():
            if field not in ["providers", "recipients", "activities"]:
                setattr(temp_appointment, field, value)
        return temp_appointment


class AutoEndTimeMixin:
    @staticmethod
    def set_end_time(form):
        end_time = form.cleaned_data.get("end_time")
        start_time = form.cleaned_data.get("start_time")
        auto_end_time = form.cleaned_data.get("auto_end_time")
        activities = form.cleaned_data.get("activities")

        if not auto_end_time or activities is None:
            if end_time is None:
                form.cleaned_data["end_time"] = start_time
            return

        total_duration = sum(
            (activity.duration_time for activity in activities), timedelta()
        )

        start_datetime = datetime.combine(date.min, start_time)
        calculated_end = start_datetime + total_duration

        form.cleaned_data["end_time"] = calculated_end.time()


class AutoPriceMixin:
    @staticmethod
    def set_price(form):
        auto_price = form.cleaned_data.get("auto_price")
        activities = form.cleaned_data.get("activities")
        if not auto_price or activities is None:
            return

        total = sum(a.price for a in form.cleaned_data.get("activities").all())
        form.cleaned_data["price"] = total


class AppointmentValidatorPipeline:
    def __init__(self, form):
        self.form = form
        self.steps = [
            TimeValidationMixin.validate_time,
            BlockedValidationMixin.validate_blocked,
            AutoEndTimeMixin.set_end_time,
            AutoPriceMixin.set_price,
            ConflictValidationMixin.validate_conflicts,
        ]

    def run(self):
        for step in self.steps:
            step(self.form)
            if self.form.errors:
                break
