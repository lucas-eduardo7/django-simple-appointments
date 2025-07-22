from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Appointment


@receiver(m2m_changed, sender=Appointment)
def check_conflits(sender, instance, action, **kwargs):
    print("chamado")
    if action != "post_add":
        return
    for provider in instance.providers.all():
        conflicts = Appointment.objects.filter(
            providers=provider,
            date=instance.date,
            start_time__lt=instance.end_time,
            end_time__gt=instance.start_time,
        ).exclude(pk=instance.pk)

        if conflicts.exists():
            raise ValidationError("error")
