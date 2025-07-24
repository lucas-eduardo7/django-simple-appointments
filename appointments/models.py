from django.core.exceptions import ValidationError
from django.db import models
from .conf import get_setting
from .utils import validate_appointments_conflicts, validate_time_cohesion


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
    activities = models.ManyToManyField(
        to=get_setting("APPOINTMENTS_ACTIVITIES_MODEL"),
        related_name="appointments_as_activities",
    )
    status = models.CharField(
        max_length=30,
        choices=get_setting("APPOINTMENTS_STATUS_CHOICES"),
        default="pending",
        blank=True,
    )
    price = models.DecimalField(max_digits=7, decimal_places=2)
    is_blocked = models.BooleanField(default=False)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self):
        super().clean()

        if not self.pk:
            return

        for provider in self.providers.all():
            time_cohesion = validate_time_cohesion(self.start_time, self.end_time)
            conflict_message = validate_appointments_conflicts(self, provider)

            if time_cohesion:
                raise ValidationError(time_cohesion)
            if conflict_message:
                raise ValidationError(conflict_message)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AppointmentProvider(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    provider = models.ForeignKey(
        to=get_setting("APPOINTMENTS_PROVIDER_MODEL"), on_delete=models.CASCADE
    )

    def clean(self):
        super().clean()

        conflict_message = validate_appointments_conflicts(
            self.appointment, self.provider
        )
        if conflict_message:
            raise ValidationError(conflict_message)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AppointmentRecipient(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    provider = models.ForeignKey(
        to=get_setting("APPOINTMENTS_RECIPIENT_MODEL"), on_delete=models.CASCADE
    )
