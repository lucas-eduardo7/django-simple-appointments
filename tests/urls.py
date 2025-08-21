from django.urls import path
from tests.views import TestFormWizardView, TestSucessWizardView

urlpatterns = [
    path("wizard/<int:step>/", TestFormWizardView.as_view(), name="wizard"),
    path("success/", TestSucessWizardView.as_view(), name="wizard_success"),
]
