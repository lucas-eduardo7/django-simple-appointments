from django.conf import settings


DEFAULTS = {
    "APPOINTMENTS_PROVIDER_MODEL": "auth.User",
    "APPOINTMENTS_RECIPIENT_MODEL": "auth.User",
}


def get_setting(name):
    return getattr(settings, name, DEFAULTS[name])
