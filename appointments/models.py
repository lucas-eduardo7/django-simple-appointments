from django.db import models


class Appointment(models.Model):
    provider = None
    recipient = None
