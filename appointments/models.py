from django.db import models
from .conf import get_setting
from .abstract_models import BaseModel, AppointmentAcitivityBaseModel
from .mixin_models import (
    AppointmentValidateMixin,
    ProviderValidateMixin,
    ActivityMixin,
)


class Appointment(BaseModel, AppointmentValidateMixin):
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
        through="AppointmentActivity",
        related_name="appointments_as_activities",
    )
    status = models.CharField(
        max_length=30,
        choices=get_setting("APPOINTMENTS_STATUS_CHOICES"),
        default="pending",
        blank=True,
    )
    price = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    auto_price = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=False)
    auto_end_time = models.BooleanField(default=True)
    prevents_overlap = models.BooleanField(default=True)


class AppointmentProvider(BaseModel, ProviderValidateMixin):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    provider = models.ForeignKey(
        to=get_setting("APPOINTMENTS_PROVIDER_MODEL"), on_delete=models.CASCADE
    )


class AppointmentRecipient(BaseModel):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    recipient = models.ForeignKey(
        to=get_setting("APPOINTMENTS_RECIPIENT_MODEL"), on_delete=models.CASCADE
    )


class AppointmentActivity(AppointmentAcitivityBaseModel, ActivityMixin):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    activity = models.ForeignKey(
        to=get_setting("APPOINTMENTS_ACTIVITIES_MODEL"), on_delete=models.CASCADE
    )
