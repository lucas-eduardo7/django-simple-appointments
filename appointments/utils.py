from django.apps import apps
from datetime import datetime, timedelta, date


def validate_appointments_conflicts(instance, provider):
    Appointment = apps.get_model("appointments", "Appointment")
    conflicts = Appointment.objects.filter(
        date=instance.date,
        start_time__lt=instance.end_time,
        end_time__gt=instance.start_time,
        providers__in=[provider],
    ).exclude(pk=instance.pk)

    if conflicts.exists():
        conflict = conflicts.first()
        return (
            f"Schedule conflict for provider {provider} on {instance.date} "
            f"between {instance.start_time} and {instance.end_time}. "
            f"Conflicts with existing appointment from {conflict.start_time} to {conflict.end_time}."
        )
    return None


def validate_time_cohesion(start_time, end_time):
    if not end_time:
        return None
    if start_time > end_time:
        return f"The start time ({start_time}) must be earlier than the end time ({end_time})."
    return None


def set_price(instance):
    if not instance.auto_price:
        return

    total = sum(a.price for a in instance.activities.all())
    instance.price = total
    instance.save(update_fields=["price"])


def set_end_time(instance):
    if not instance.auto_end_time:
        return

    total_duration = sum(
        (a.duration_time for a in instance.activities.all()), timedelta()
    )
    dummy_datetime = datetime.combine(date.min, instance.start_time)
    result_datetime = dummy_datetime + total_duration
    instance.end_time = result_datetime.time()
    instance.save(update_fields=["end_time"])
