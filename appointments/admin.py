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
    list_display = (
        "id",
        "start_time",
        "end_time",
        "price",
        "status",
        "get_providers",
        "get_recipients",
        "get_activities",
        "created_at",
        "updated_at",
    )
    inlines = [
        AppointmentActivitiesInline,
        AppointmentProviderInline,
        AppointmentRecipientInline,
    ]

    def get_providers(self, obj):
        return ", ".join(str(p) for p in obj.providers.all())

    get_providers.short_description = "Providers"

    def get_recipients(self, obj):
        return ", ".join(str(r) for r in obj.recipients.all())

    get_recipients.short_description = "Recipients"

    def get_activities(self, obj):
        return ", ".join(str(a) for a in obj.activities.all())

    get_activities.short_description = "Activities"
