from django.apps import apps


def validate_appointments_conflicts(appointment, provider):
    Appointment = apps.get_model("appointments", "Appointment")
    conflicts = Appointment.objects.filter(
        providers=provider,
        date=appointment.date,
        start_time__lt=appointment.end_time,
        end_time__gt=appointment.start_time,
    ).exclude(pk=appointment.pk)

    if conflicts.exists():
        conflict = conflicts.first()
        return (
            f"Schedule conflict for provider {provider} on {appointment.date} "
            f"between {appointment.start_time} and {appointment.end_time}. "
            f"Conflicts with existing appointment from {conflict.start_time} to {conflict.end_time}."
        )
    return None


def validate_time_cohesion(start_time, end_time):
    if not end_time:
        return None
    if start_time >= end_time:
        return f"The start time ({start_time}) must be earlier than the end time ({end_time})."
    return None
