from django.contrib import admin
from .models import (
    Appointment,
    AppointmentActivity,
    AppointmentProvider,
    AppointmentRecipient,
)


class AppointmentActivitiesInline(admin.TabularInline):
    model = AppointmentActivity
    extra = 1


class AppointmentProviderInline(admin.TabularInline):
    model = AppointmentProvider
    extra = 1


class AppointmentRecipientInline(admin.TabularInline):
    model = AppointmentRecipient
    extra = 1


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    inlines = [
        AppointmentActivitiesInline,
        AppointmentProviderInline,
        AppointmentRecipientInline,
    ]
