from simple_appointments.views import FormWizardView
from django.shortcuts import render
from django.views import View


class TestFormWizardView(FormWizardView):
    template_name = "home.html"
    next_url = "wizard"
    success_url = "wizard_success"


class TestSucessWizardView(View):
    def get(self, request):
        return render(request, "home.html")
