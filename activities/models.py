from django.db import models
from datetime import timedelta


class Activity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    duration_time = models.DurationField(default=timedelta(hours=1))

    def __str__(self):
        return self.name
