from django import forms
from django.apps import apps
from datetime import time
from .conf import get_setting
from .mixin_forms import TimeStepFormMixin


class RecipientsStepForm(forms.Form):
    def get_model():
        app, model = get_setting("APPOINTMENTS_RECIPIENTS_MODEL").split(".")
        return apps.get_model(app, model)

    recipients = forms.ModelMultipleChoiceField(
        queryset=get_model().objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )


class ProviderStepForm(forms.Form):
    def get_model():
        app, model = get_setting("APPOINTMENTS_PROVIDERS_MODEL").split(".")
        return apps.get_model(app, model)

    providers = forms.ModelMultipleChoiceField(
        queryset=get_model().objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )


class ActivitiesStepForm(forms.Form):
    def get_model():
        app, model = get_setting("APPOINTMENTS_ACTIVITIES_MODEL").split(".")
        return apps.get_model(app, model)

    activities = forms.ModelMultipleChoiceField(
        queryset=get_model().objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )


class DateStepForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))


class TimeStepForm(TimeStepFormMixin, forms.Form):
    start_time = forms.ChoiceField(choices=None)

    def __init__(self, *args, **kwargs):
        date = kwargs.pop("date", None)
        providers = kwargs.pop("providers", None)
        start = kwargs.pop("start", time(0, 0))
        end = kwargs.pop("end", time(0, 0))
        activities = kwargs.pop("activities", [])
        interval = kwargs.pop("interval", 10)

        super().__init__(*args, **kwargs)

        if date and providers:
            self.fields["start_time"].choices = self.get_slot_choices(
                date, providers, start, end, activities, interval
            )
        else:
            self.fields["start_time"].choices = []


class ConfirmStepForm(forms.Form):
    pass
