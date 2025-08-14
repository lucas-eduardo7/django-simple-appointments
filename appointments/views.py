from django.views import View
from django.views.generic import CreateView
from .models import Appointment
from .forms import AppointmentAdminForm
from django.urls import reverse_lazy
from datetime import date, time


class AppointmentCreateView(CreateView):
    model = Appointment
    template_name = "home.html"
    form_class = AppointmentAdminForm
    success_url = reverse_lazy("home")


from .forms import (
    RecipientsStepForm,
    ProviderStepForm,
    ActivitiesStepForm,
    DateStepForm,
    TimeStepForm,
    ConfirmStepForm,
)
from django.shortcuts import render, redirect
from .conf import get_setting
from django.apps import apps


class FormWizardView(View):
    forms_map = {
        1: (RecipientsStepForm, "home.html", 2),
        2: (ProviderStepForm, "home.html", 3),
        3: (ActivitiesStepForm, "home.html", 4),
        4: (DateStepForm, "home.html", 5),
        5: (TimeStepForm, "home.html", 6),
        6: (ConfirmStepForm, "home.html", None),
    }

    def get(self, request, step):
        if step not in self.forms_map:
            return redirect("wizard", step=1)

        form_class, template, _ = self.forms_map[step]
        form = form_class(initial=self._load_step_data(request))
        return render(request, template, {"form": form, "step": step})

    def post(self, request, step):
        if step not in self.forms_map:
            return redirect("wizard", step=1)

        form_class, template, next_step = self.forms_map[step]
        form = form_class(request.POST)

        if form.is_valid():
            self._save_step_data(request, form.cleaned_data)

            if next_step:
                return redirect("wizard", step=next_step)
            else:
                self._finalize_wizard(request)
                return redirect("wizard_sucesso")
        return render(request, template, {"form": form, "step": step})

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

    def _finalize_wizard(self, request):
        form_data = request.session["form_data"]

        appointment_form = self._build_appointment_form(form_data)

        if appointment_form.is_valid():
            appointment_form.save()
        else:
            print("erros", appointment_form.errors())

        del request.session["form_data"]

    def _build_appointment_form(self, form_data):
        data = {
            "providers": [
                p.pk
                for p in self._get_objects(
                    "APPOINTMENTS_PROVIDER_MODEL", form_data["providers"]
                )
            ],
            "recipients": [
                r.pk
                for r in self._get_objects(
                    "APPOINTMENTS_RECIPIENT_MODEL", form_data["recipients"]
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
            "is_blocked": False,
            "date": date.fromisoformat(form_data["date"]),
            "start_time": time.fromisoformat(form_data["start_time"]),
            "end_time": None,
            "auto_end_time": True,
            "prevents_overlap": True,
        }
        return AppointmentAdminForm(data=data)

    def _get_objects(self, setting_key, pks):
        app, model = get_setting(setting_key).split(".")
        Model = apps.get_model(app, model)
        return Model.objects.filter(pk__in=pks)
