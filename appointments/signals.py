from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Appointment, AppointmentProvider


@receiver(post_save, sender=AppointmentProvider)
def check_conflits(sender, instance, **kwargs):
    appointment = instance.appointment
    provider = instance.provider

    conflicts = Appointment.objects.filter(
        providers=provider,
        date=appointment.date,
        start_time__lt=appointment.end_time,
        end_time__gt=appointment.start_time,
    ).exclude(pk=appointment.pk)

    if conflicts.exists():
        raise ValidationError("Schedule conflict for the provider.")
