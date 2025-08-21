from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super().clean()
        if hasattr(self, "run_validations"):
            self.run_validations()

    def save(self, clean=True, *args, **kwargs):
        if clean:
            self.full_clean()
        super().save(*args, **kwargs)


class AppointmentAcitivityBaseModel(BaseModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_fields()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.update_fields()
