from datetime import date, time, timedelta
from django.apps import apps
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View
from .conf import get_setting
from .forms import AppointmentAdminForm
from .wizard_forms import (
    RecipientsStepForm,
    ProviderStepForm,
    ActivitiesStepForm,
    DateStepForm,
    TimeStepForm,
    ConfirmStepForm,
)


class BaseFormWizardView(View):
    template_name = None
    next_url = None
    success_url = None
    forms_map = {}

    def get(self, request, step):
        if step not in self.forms_map:
            return redirect(self.next_url, step=1)

        valid, step_redirect = self._validate_step_sequence(request, step)
        if not valid:
            return redirect(self.next_url, step=step_redirect)

        form = self._build_form(step, request)
        return render(request, self.template_name, {"form": form, "step": step})

    def post(self, request, step):
        if step not in self.forms_map:
            return redirect(self.next_url, step=1)

        valid, step_redirect = self._validate_step_sequence(request, step)
        if not valid:
            return redirect(self.next_url, step=step_redirect)

        form = self._build_form(step, request)
        next_step = self.forms_map[step][1]

        if form.is_valid():
            self._save_step_data(request, form.cleaned_data)
            self._set_completed_steps(request, step)

            if next_step:
                return redirect(self.next_url, step=next_step)
            else:
                return self._finalize_wizard(request)
        return render(request, self.template_name, {"form": form, "step": step})

    def _load_step_data(self, request):
        return request.session.setdefault("form_data", {})

    def _save_step_data(self, request, cleaned_data):
        form_data = self._load_step_data(request)

        for key, value in cleaned_data.items():
            if hasattr(value, "pk"):
                form_data[key] = value.pk
            elif hasattr(value, "__iter__") and not isinstance(value, str):
                form_data[key] = [obj.pk for obj in value]
            elif isinstance(value, (date, time)):
                form_data[key] = value.isoformat()
            else:
                form_data[key] = value

        request.session.modified = True

    def _set_completed_steps(self, request, step):
        completed_steps = request.session.get("completed_steps", [])
        if step not in completed_steps:
            completed_steps.append(step)
        request.session["completed_steps"] = completed_steps

    def _validate_step_sequence(self, request, step):
        completed_steps = request.session.get("completed_steps", [])
        if step > len(completed_steps) + 1:
            return (False, len(completed_steps) + 1)
        return (True, None)

    def _finalize_wizard(self, request):
        raise NotImplementedError

    def _build_form(self, step, request, post_data=None):
        raise NotImplementedError


class AppointmentBuilderMixin:
    prevents_overlap = True
    is_blocked = False
    start_time = time(8, 0)
    end_time = time(18, 0)
    interval = timedelta(minutes=10)

    def _build_appointment_form(self, form_data):
        data = {
            "providers": [
                p.pk
                for p in self._get_objects(
                    "APPOINTMENTS_PROVIDERS_MODEL", form_data["providers"]
                )
            ],
            "recipients": [
                r.pk
                for r in self._get_objects(
                    "APPOINTMENTS_RECIPIENTS_MODEL", form_data["recipients"]
                )
            ],
            "activities": [
                a.pk
                for a in self._get_objects(
                    "APPOINTMENTS_ACTIVITIES_MODEL", form_data["activities"]
                )
            ],
            "price": 0,
            "auto_price": True,
            "is_blocked": self.is_blocked,
            "date": date.fromisoformat(form_data["date"]),
            "start_time": time.fromisoformat(form_data["start_time"]),
            "end_time": None,
            "auto_end_time": True,
            "prevents_overlap": self.prevents_overlap,
        }
        return AppointmentAdminForm(data=data)

    def _get_objects(self, setting_key, pks):
        app, model = get_setting(setting_key).split(".")
        Model = apps.get_model(app, model)
        return Model.objects.filter(pk__in=pks)


class FormWizardView(AppointmentBuilderMixin, BaseFormWizardView):
    forms_map = {
        1: (RecipientsStepForm, 2),
        2: (ProviderStepForm, 3),
        3: (ActivitiesStepForm, 4),
        4: (DateStepForm, 5),
        5: (TimeStepForm, 6),
        6: (ConfirmStepForm, None),
    }

    def _finalize_wizard(self, request):
        form_data = request.session["form_data"]

        appointment_form = self._build_appointment_form(form_data)

        if appointment_form.is_valid():
            appointment_form.save()
            messages.success(request, "Appointment created successfully!")
        else:
            for field, errors in appointment_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect(self.next_url, step=1)

        del request.session["form_data"]
        return redirect(self.success_url)

    def _build_form(self, step, request, post_data=None):
        form_class, _ = self.forms_map[step]
        form_data = self._load_step_data(request)

        if form_class == self.get_time_step_form():
            selected_date = date.fromisoformat(form_data.get("date"))
            providers = self._get_objects(
                "APPOINTMENTS_PROVIDERS_MODEL", form_data.get("providers")
            )
            activities = self._get_objects(
                "APPOINTMENTS_ACTIVITIES_MODEL", form_data.get("activities")
            )

            kwargs = {
                "date": selected_date,
                "providers": providers,
                "activities": activities,
                "start": self.start_time,
                "end": self.end_time,
                "interval": self.interval,
            }

            if request.method == "POST":
                return form_class(post_data or request.POST, **kwargs)
            return form_class(**kwargs)

        if request.method == "POST":
            return form_class(post_data or request.POST)
        return form_class()

    def get_time_step_form(self):
        return TimeStepForm
