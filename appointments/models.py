from django.db import models
from .conf import get_setting


class Appointment(models.Model):
    providers = models.ManyToManyField(
        to=get_setting("APPOINTMENTS_PROVIDER_MODEL"),
        through="AppointmentProvider",
        related_name="appointments_as_provider",
    )
    recipients = models.ManyToManyField(
        to=get_setting("APPOINTMENTS_RECIPIENT_MODEL"),
        through="AppointmentRecipient",
        related_name="appointments_as_recipient",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=30,
        choices=get_setting("APPOINTMENTS_STATUS_CHOICES"),
        default="pending",
        blank=True,
    )
    is_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True, null=True)


class AppointmentProvider(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    provider = models.ForeignKey(
        to=get_setting("APPOINTMENTS_PROVIDER_MODEL"), on_delete=models.CASCADE
    )


class AppointmentRecipient(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    provider = models.ForeignKey(
        to=get_setting("APPOINTMENTS_RECIPIENT_MODEL"), on_delete=models.CASCADE
    )
