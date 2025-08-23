# Django Simple Appointments

A lightweight framework for managing appointments generically in Django applications. It provides models, utilities, and a `FormWizard` view to handle providers, recipients, activities, time slots, pricing, and overlap validation.

## Installation

1. Install the package via pip:
   ```bash
   pip install django-simple-appointments
   ```

2. Add `simple_appointments` to `INSTALLED_APPS` in `settings.py`:
   ```python
   INSTALLED_APPS = [
       ...,
       'simple_appointments',
   ]
   ```

3. Apply migrations:
   ```bash
   python manage.py migrate
   ```

## `Appointment` Model

The `Appointment` model has the following fields:

- **providers**: Users who perform the appointment (e.g., a barber in a barbershop).
- **recipients**: Users who receive the appointment (e.g., a client in a barbershop).
- **activities**: Activities to be performed in the appointment.
  - These fields are many-to-many (M2M) relationships, allowing multiple objects.
  - Can be overridden in `settings.py`:
    ```python
    APPOINTMENTS_PROVIDERS_MODEL = "your_app.YourModel"
    APPOINTMENTS_RECIPIENTS_MODEL = "your_app.YourModel"
    APPOINTMENTS_ACTIVITIES_MODEL = "your_app.YourModel"
    ```

- **status**: Indicates the appointment's current status. Default options:
  ```python
  APPOINTMENTS_STATUS_CHOICES = [
      ("", "Not specified"),
      ("pending", "Pending"),
      ("confirmed_by_recipients", "Confirmed by Recipients"),
      ("canceled_by_recipients", "Canceled by Recipients"),
      ("canceled_by_providers", "Canceled by Providers"),
      ("completed", "Completed"),
      ("no_show", "No-show"),
  ]
  ```
  - Can be customized in `settings.py`.

- **price**: The appointment's price.
- **auto_price**: If `True`, the price is calculated by summing the `price` attribute of the activities. If a price is set manually, it will be overridden by the automatic calculation.
- **is_blocked**: If `True`, blocks the time slot, preventing new appointments (e.g., reserving a slot for an unavailable barber).
- **date**: Appointment date.
- **start_time**: Start time of the appointment.
- **end_time**: End time of the appointment.
- **auto_end_time**: If `True`, `end_time` is calculated automatically based on the `duration_time` attribute of activities. If `False` and `end_time` is empty, `end_time` will match `start_time`.
- **prevents_overlap**: If `True` (default), prevents conflicting appointments for the same provider at the same time. If `False`, allows overlaps.

## FormWizard

The package includes a `FormWizard`-based view that automatically calculates available time slots, considering existing appointments and the duration of selected activities.

### How to Use the `FormWizard`

1. Import and configure the view:
   ```python
   from simple_appointments.views import FormWizardView

   class ExampleFormWizardView(FormWizardView):
       template_name = "your_template.html"
       next_url = "your_url"
       success_url = "your_success_url"
       prevents_overlap = True
       is_blocked = False
       start_time = time(8, 0)  # Starts at 8 AM
       end_time = time(18, 0)   # Ends at 6 PM
       interval = timedelta(minutes=10)  # 10-minute intervals
   ```

2. Default `FormWizard` structure:
   ```python
   forms_map = {
       1: (RecipientsStepForm, 2),
       2: (ProviderStepForm, 3),
       3: (ActivitiesStepForm, 4),
       4: (DateStepForm, 5),
       5: (TimeStepForm, 6),
       6: (ConfirmStepForm, None),
   }
   ```
   - To customize, override `forms_map` in your class.
   - To modify the `TimeStepForm`, override the method:
     ```python
     def get_time_step_form(self):
         return YourCustomTimeStepForm
     ```

## Development

To contribute or test locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/django-simple-appointments.git
   cd django-simple-appointments
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
