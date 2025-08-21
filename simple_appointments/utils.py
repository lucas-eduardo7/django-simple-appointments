from django.apps import apps


def validate_appointments_conflicts(instance, provider, queryset=None):
    if not instance.prevents_overlap:
        return None

    Appointment = apps.get_model("simple_appointments", "Appointment")

    if queryset is None:
        queryset = Appointment.objects.filter(
            prevents_overlap=True,
            date=instance.date,
            start_time__lt=instance.end_time,
            end_time__gt=instance.start_time,
        )

    conflicts = queryset.filter(
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
    if start_time is None or start_time > end_time:
        return f"The start time ({start_time}) must be earlier than the end time ({end_time})."
    return None


def validate_blocked_cohesion(is_blocked, prevents_overlap):
    if is_blocked and not prevents_overlap:
        return (
            "An appointment cannot be marked as blocked while allowing overlaps. "
            "Set 'prevents_overlap=True' when 'is_blocked=True'."
        )
    return None
