from django.conf import settings
from datetime import date, timedelta, time
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from model_bakery import baker
from .models import Appointment
from .forms import AppointmentAdminForm


USER = get_user_model()


class AppointmentTestMixin(TestCase):
    def setUp(self):
        """Prepare test data: one activity, one provider user, and one recipient user."""
        self.activity = baker.make(
            "activities.Activity",
            name="test",
            price="100",
            duration_time=timedelta(minutes=90),
        )
        self.provider = baker.make(USER, username="provider")
        self.recipient = baker.make(USER, username="recipient")

    def _add_m2m(
        self,
        appointment,
        add_activity=True,
        multiple_providers=False,
    ):
        """
        Add Many-to-Many relationships to the given appointment.

        Args:
            appointment (Appointment): The appointment instance to link relations.
            add_activity (bool): Whether to add the activity relation.

        Returns:
            Appointment: The appointment reloaded from the database after saving through tables.
        """
        if add_activity:
            appointment.activities.add(self.activity)

        if multiple_providers:
            self.provider_x = baker.make(USER)
            self.provider_y = baker.make(USER)
            appointment.providers.add(
                self.provider.id, self.provider_x.id, self.provider_y.id
            )
        else:
            appointment.providers.add(self.provider)

        appointment.recipients.add(self.recipient)

        # Save all through table objects to trigger their save() logic
        for through_model in [
            Appointment.activities.through,
            Appointment.providers.through,
            Appointment.recipients.through,
        ]:
            for through_obj in through_model.objects.all():
                through_obj.save()

        appointment.refresh_from_db()
        return appointment

    def _assert_base_fields(
        self,
        appointment,
        price,
        start_time,
        end_time,
        auto_price,
        auto_end_time,
        is_blocked=False,
    ):
        """
        Assert that the appointment base fields match the expected values.

        Args:
            appointment (Appointment): The appointment instance to verify.
            price (int): Expected price.
            start_time (str): Expected start time in "%H:%M" format.
            end_time (str): Expected end time in "%H:%M" format.
            auto_price (bool): Expected auto_price flag.
            auto_end_time (bool): Expected auto_end_time flag.
            is_blocked (bool): Expected blocked state.
        """
        self.assertEqual(appointment.price, price)
        self.assertEqual(appointment.start_time.strftime("%H:%M"), start_time)
        self.assertEqual(appointment.end_time.strftime("%H:%M"), end_time)
        self.assertEqual(appointment.auto_price, auto_price)
        self.assertEqual(appointment.auto_end_time, auto_end_time)
        if is_blocked is not None:
            self.assertEqual(appointment.is_blocked, is_blocked)

    def _assert_m2m_counts(self, appointment, activities_count=1):
        """
        Assert that the appointment has the expected Many-to-Many counts.

        Args:
            appointment (Appointment): The appointment instance to verify.
            activities_count (int): Expected number of activities linked.
        """
        self.assertEqual(appointment.activities.count(), activities_count)
        self.assertEqual(appointment.providers.count(), 1)
        self.assertEqual(appointment.recipients.count(), 1)
        if activities_count:
            self.assertIn(self.activity, appointment.activities.all())
        self.assertIn(self.provider, appointment.providers.all())
        self.assertIn(self.recipient, appointment.recipients.all())


class CreateAppointmentTests(AppointmentTestMixin):
    def test_create_complete_appointment_auto_fields_off(self):
        """Test creating a complete appointment with auto fields disabled."""
        appointment = Appointment.objects.create(
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_complete_appointment_auto_fields_on(self):
        """Test creating a complete appointment with auto fields enabled."""
        appointment = Appointment.objects.create(
            price=0,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    def test_create_incomplete_appointment_auto_fields_on(self):
        """Test creating an incomplete appointment with auto fields enabled."""
        appointment = Appointment.objects.create(
            start_time="14:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    def test_create_complete_blocked_appointment_auto_fields_off(self):
        """Test creating a blocked appointment with auto fields disabled."""
        appointment = Appointment.objects.create(
            is_blocked=True,
            price=0,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )
        appointment.save()
        appointment = self._add_m2m(appointment, add_activity=False)

        self._assert_base_fields(appointment, 0, "14:00", "15:00", False, False, True)
        self._assert_m2m_counts(appointment, activities_count=0)

    def test_create_incomplete_blocked_appointment_auto_fields_on(self):
        """Test creating an incomplete blocked appointment with auto fields enabled."""
        appointment = Appointment.objects.create(
            is_blocked=True,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True, True)
        self._assert_m2m_counts(appointment)

    def test_create_complete_appointment_auto_fields_off_overlap_off(self):
        """Test creating a complete appointment with auto fields disabled and overlap prevention enabled."""
        appointment = Appointment.objects.create(
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
            prevents_overlap=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_complete_appointment_auto_fields_on_overlap_off(self):
        """Test creating a complete appointment with auto fields enabled and overlap prevention enabled."""
        appointment = Appointment.objects.create(
            price=0,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
            prevents_overlap=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    def test_create_incomplete_appointment_auto_fields_on_overlap_off(self):
        """Test creating an incomplete appointment with auto fields enabled and overlap prevention enabled."""
        appointment = Appointment.objects.create(
            start_time="14:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
            prevents_overlap=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    def test_create_appointment_without_activities_auto_fields_on(self):
        """Test creating an appointment without activities and auto fields enabled."""
        appointment = Appointment.objects.create(
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment, add_activity=False)

        self._assert_base_fields(appointment, 70, "14:00", "15:00", True, True)
        self._assert_m2m_counts(appointment, activities_count=0)


class AppointmentTimeVerificationTest(AppointmentTestMixin):
    """Test suite to verify the correctness of appointment start and end times."""

    def test_create_appointment_with_coherent_time(self):
        """
        Test creating an appointment where the start time is earlier than the end time.

        This should succeed without raising any validation errors.
        """
        appointment = Appointment.objects.create(
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_appointment_with_inconsistent_time(self):
        """
        Test creating an appointment where the start time is later than the end time.

        Expected Behavior:
            - The model's validation should raise a ValidationError.
            - The error message must match the expected string.
        """
        with self.assertRaisesMessage(
            ValidationError,
            "The start time (15:00:00) must be earlier than the end time (14:00:00).",
        ):
            appointment = Appointment.objects.create(
                price=70,
                start_time="15:00",
                end_time="14:00",
                date=date.today(),
                auto_price=False,
                auto_end_time=False,
            )
            appointment.save()
            appointment = self._add_m2m(appointment)


class AppointmentBlockVerificationTest(AppointmentTestMixin):
    """Test suite to verify blocked appointment behavior and overlap rules."""

    def test_create_blocked_appointment_overlap_on(self):
        """
        Test creating a blocked appointment where overlaps are prevented.

        This scenario is valid and should not raise any errors.
        """
        appointment = Appointment.objects.create(
            is_blocked=True,
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False, True)
        self._assert_m2m_counts(appointment)

    def test_create_blocked_appointment_overlap_off(self):
        """
        Test creating a blocked appointment where overlaps are allowed (prevents_overlap=False).

        Expected Behavior:
            - This configuration is invalid because a blocked appointment must prevent overlaps.
            - A ValidationError is raised with the expected message.
        """
        with self.assertRaisesMessage(
            ValidationError,
            "An appointment cannot be marked as blocked while allowing overlaps. "
            "Set 'prevents_overlap=True' when 'is_blocked=True",
        ):
            appointment = Appointment.objects.create(
                is_blocked=True,
                price=70,
                start_time="14:00",
                end_time="15:00",
                date=date.today(),
                auto_price=False,
                auto_end_time=False,
                prevents_overlap=False,
            )
            appointment.save()
            appointment = self._add_m2m(appointment)


class AppointmentOverlapVerificationTest(AppointmentTestMixin):
    """
    Test suite to validate appointment creation and modification in scenarios involving
    overlapping schedules, boundary times, and provider availability.
    """

    def setUp(self):
        """Prepare a base appointment from 14:00 to 15:00 to use in overlap tests."""
        super().setUp()
        self.appointment = Appointment.objects.create(
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )

    def test_create_appointment_overlapping_another(self):
        """
        Ensure that creating an appointment with the exact same start and end time
        as an existing one raises a ValidationError due to schedule conflict.
        """
        today = date.today()
        with self.assertRaisesMessage(
            ValidationError,
            f"Schedule conflict for provider provider on {today} between 14:00:00 and 15:00:00. Conflicts with existing appointment from 14:00:00 to 15:00:00.",
        ):
            appointment = Appointment.objects.create(
                price=70,
                start_time="14:00",
                end_time="15:00",
                date=today,
                auto_price=False,
                auto_end_time=False,
            )

            self.appointment.save()
            self.appointment = self._add_m2m(self.appointment)

            appointment.save()
            appointment = self._add_m2m(appointment)

    def test_create_appointment_fully_inside_another(self):
        """
        Ensure that creating an appointment fully inside the time range of
        another appointment (e.g., 14:30–14:50 inside 14:00–15:00) raises a ValidationError.
        """
        today = date.today()
        with self.assertRaisesMessage(
            ValidationError,
            f"Schedule conflict for provider provider on {today} between 14:00:00 and 15:00:00. Conflicts with existing appointment from 14:30:00 to 14:50:00.",
        ):
            appointment = Appointment.objects.create(
                price=70,
                start_time="14:30",
                end_time="14:50",
                date=today,
                auto_price=False,
                auto_end_time=False,
            )

            self.appointment.save()
            self.appointment = self._add_m2m(self.appointment)

            appointment.save()
            appointment = self._add_m2m(appointment)

    def test_create_appointment_starts_at_previous_end_time(self):
        """
        Verify that creating an appointment that ends exactly at the start time
        of another (13:00–14:00 before 14:00–15:00) does not raise an error.
        """
        appointment = Appointment.objects.create(
            price=70,
            start_time="13:00",
            end_time="14:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )
        self.appointment.save()
        self.appointment = self._add_m2m(self.appointment)

        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "13:00", "14:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_appointment_ends_at_next_start_time(self):
        """
        Verify that creating an appointment that starts exactly when another ends
        (15:00–16:00 after 14:00–15:00) does not raise an error.
        """
        appointment = Appointment.objects.create(
            price=70,
            start_time="15:00",
            end_time="16:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )
        self.appointment.save()
        self.appointment = self._add_m2m(self.appointment)

        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "15:00", "16:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_appointment_date_change_causes_overlap(self):
        """
        Validate that changing an appointment's date to a day where it overlaps
        with an existing appointment raises a ValidationError.
        """
        today = date.today()
        tomorrow = today + timedelta(days=1)
        appointment = Appointment.objects.create(
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=tomorrow,
            auto_price=False,
            auto_end_time=False,
        )
        self.appointment.save()
        self.appointment = self._add_m2m(self.appointment)

        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

        with self.assertRaisesMessage(
            ValidationError,
            f"Schedule conflict for provider provider on {today} between 14:00:00 and 15:00:00. Conflicts with existing appointment from 14:00:00 to 15:00:00.",
        ):
            appointment.date = date.today()
            appointment.save()

    def test_appointment_date_change_starts_at_previous_end_time(self):
        """
        Ensure that moving an appointment to a date where it ends exactly when
        another appointment starts is still valid.
        """
        tomorrow = date.today() + timedelta(days=1)
        appointment = Appointment.objects.create(
            price=70,
            start_time="13:00",
            end_time="14:00",
            date=tomorrow,
            auto_price=False,
            auto_end_time=False,
        )
        self.appointment.save()
        self.appointment = self._add_m2m(self.appointment)

        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "13:00", "14:00", False, False)
        self._assert_m2m_counts(appointment)

        appointment.date = date.today()
        appointment.save()

        self._assert_base_fields(appointment, 70, "13:00", "14:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_appointment_date_change_ends_at_next_start_time(self):
        """
        Ensure that moving an appointment to a date where it starts exactly
        when another appointment ends is still valid.
        """
        tomorrow = date.today() + timedelta(days=1)
        appointment = Appointment.objects.create(
            price=70,
            start_time="15:00",
            end_time="16:00",
            date=tomorrow,
            auto_price=False,
            auto_end_time=False,
        )
        self.appointment.save()
        self.appointment = self._add_m2m(self.appointment)

        appointment.save()
        appointment = self._add_m2m(appointment)

        self._assert_base_fields(appointment, 70, "15:00", "16:00", False, False)
        self._assert_m2m_counts(appointment)

        appointment.date = date.today()
        appointment.save()

        self._assert_base_fields(appointment, 70, "15:00", "16:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_appointment_with_one_provider_unavailable(self):
        """
        Validate that when one provider is already booked during a time slot,
        creating a new appointment with the same provider raises a ValidationError.
        """
        today = date.today()
        with self.assertRaisesMessage(
            ValidationError,
            f"Schedule conflict for provider provider on {today} between 14:00:00 and 15:00:00. Conflicts with existing appointment from 14:00:00 to 15:00:00.",
        ):
            appointment = Appointment.objects.create(
                price=70,
                start_time="14:00",
                end_time="15:00",
                date=today,
                auto_price=False,
                auto_end_time=False,
            )

            self.appointment.save()
            self.appointment = self._add_m2m(self.appointment)

            appointment.save()
            appointment = self._add_m2m(appointment, multiple_providers=True)


class AppointmentDuplicateProvidersRecipientsTest(AppointmentTestMixin):
    """
    Test cases to validate that an Appointment cannot have duplicate
    providers or recipients in its many-to-many relationships.
    """

    def test_cannot_add_duplicate_providers(self):
        """
        Ensure that attempting to add a duplicate provider to an appointment
        raises a ValidationError.

        Steps:
        1. Create a new appointment and add the initial provider via _add_m2m.
        2. Attempt to create a duplicate entry in the AppointmentProvider through table.
        3. Expect a ValidationError indicating the provider already exists for this appointment.
        """
        with self.assertRaisesMessage(
            ValidationError,
            "Appointment provider with this Appointment and Provider already exists.",
        ):
            appointment = Appointment.objects.create(
                price=70,
                start_time="14:00",
                end_time="15:00",
                date=date.today(),
                auto_price=False,
                auto_end_time=False,
            )
            appointment.save()
            appointment = self._add_m2m(appointment)

            # Attempt to insert a duplicate provider manually in the through table
            baker.make(
                "appointments.AppointmentProvider",
                appointment=appointment,
                provider=self.provider,
            )

    def test_cannot_add_duplicate_recipients(self):
        """
        Ensure that attempting to add a duplicate recipient to an appointment
        raises a ValidationError.

        Steps:
        1. Create a new appointment and add the initial recipient via _add_m2m.
        2. Attempt to create a duplicate entry in the AppointmentRecipient through table.
        3. Expect a ValidationError indicating the recipient already exists for this appointment.
        """
        with self.assertRaisesMessage(
            ValidationError,
            "Appointment recipient with this Appointment and Recipient already exists.",
        ):
            appointment = Appointment.objects.create(
                price=70,
                start_time="14:00",
                end_time="15:00",
                date=date.today(),
                auto_price=False,
                auto_end_time=False,
            )
            appointment.save()
            appointment = self._add_m2m(appointment)

            # Attempt to insert a duplicate recipient manually in the through table
            baker.make(
                "appointments.AppointmentRecipient",
                appointment=appointment,
                recipient=self.recipient,
            )


class AppointmentAutoFieldsOnActivityUpdateTest(AppointmentTestMixin):
    """
    Test suite to verify that automatic fields (`auto_price` and `auto_end_time`)
    in Appointment objects remain unchanged when the attributes of linked
    Activity instances are updated after the appointment is created.
    """

    def test_auto_fields_remain_when_activity_price_changes(self):
        """
        Verify that updating the price of an associated Activity
        does not automatically recalculate `price` or `end_time`
        in an Appointment with `auto_price` and `auto_end_time` enabled.
        """
        # Create an appointment with auto fields enabled
        appointment = Appointment.objects.create(
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        # Initial automatic values should reflect the activity's original data
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

        # Change the price of the linked Activity
        self.activity.price = 70
        self.activity.save()

        # Reload the appointment from the database and check that fields did not change
        appointment.refresh_from_db()
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)

    def test_auto_fields_remain_when_activity_duration_changes(self):
        """
        Verify that updating the duration_time of an associated Activity
        does not automatically recalculate `price` or `end_time`
        in an Appointment with `auto_price` and `auto_end_time` enabled.
        """
        # Create an appointment with auto fields enabled
        appointment = Appointment.objects.create(
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=True,
            auto_end_time=True,
        )
        appointment.save()
        appointment = self._add_m2m(appointment)

        # Initial automatic values should reflect the activity's original data
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

        # Change the duration of the linked Activity
        self.activity.duration_time = timedelta(minutes=60)
        self.activity.save()

        # Reload the appointment from the database and check that fields did not change
        appointment.refresh_from_db()
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)


class FormHelperMixin:
    def _build_form_data(
        self,
        *,
        date_value=None,
        start_time=None,
        end_time=None,
        price=None,
        auto_price=None,
        auto_end_time=None,
        is_blocked=None,
        prevents_overlap=None,
        providers=None,
        recipients=None,
        activities=None,
    ):
        data = {}
        if date_value is not None:
            data["date"] = date_value.isoformat()
        if start_time is not None:
            data["start_time"] = str(start_time)
        if end_time is not None:
            data["end_time"] = str(end_time)
        if price is not None:
            data["price"] = str(price)
        if auto_price is not None:
            data["auto_price"] = auto_price
        if auto_end_time is not None:
            data["auto_end_time"] = auto_end_time
        if is_blocked is not None:
            data["is_blocked"] = is_blocked
        if prevents_overlap is not None:
            data["prevents_overlap"] = prevents_overlap

        data["providers"] = [p.pk for p in (providers or [])]
        data["recipients"] = [r.pk for r in (recipients or [])]
        data["activities"] = [a.pk for a in (activities or [])]

        return data

    def _submit_and_save_form(self, data):
        form = AppointmentAdminForm(data=data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors.as_json()}")
        return form.save()


class CreateAppointmentFormTests(AppointmentTestMixin, FormHelperMixin):
    def test_create_complete_appointment_auto_fields_off(self):
        """Test creating a complete appointment with automatic fields disabled, using form."""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_complete_appointment_auto_fields_on(self):
        """Test creating a complete appointment with auto fields enabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=0,
            auto_price=True,
            auto_end_time=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    def test_create_incomplete_appointment_auto_fields_on(self):
        """Test creating an incomplete appointment with auto fields enabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            # no end_time provided
            price=0,
            auto_price=True,
            auto_end_time=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    def test_create_complete_blocked_appointment_auto_fields_off(self):
        """Test creating a blocked appointment with auto fields disabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=0,
            auto_price=False,
            auto_end_time=False,
            is_blocked=True,
            prevents_overlap=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 0, "14:00", "15:00", False, False, True)
        self._assert_m2m_counts(appointment)

    def test_create_incomplete_blocked_appointment_auto_fields_on(self):
        """Test creating an incomplete blocked appointment with auto fields enabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=0,
            auto_price=True,
            auto_end_time=True,
            is_blocked=True,
            prevents_overlap=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True, True)
        self._assert_m2m_counts(appointment)

    def test_create_complete_appointment_auto_fields_off_overlap_off(self):
        """Test creating a complete appointment with auto fields disabled and overlap prevention enabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=70,
            auto_price=False,
            auto_end_time=False,
            prevents_overlap=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_complete_appointment_auto_fields_on_overlap_off(self):
        """Test creating a complete appointment with auto fields enabled and overlap prevention enabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=0,
            auto_price=True,
            auto_end_time=True,
            prevents_overlap=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    def test_create_incomplete_appointment_auto_fields_on_overlap_off(self):
        """Test creating an incomplete appointment with auto fields enabled and overlap prevention enabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            # end_time omitted so auto_end_time will compute it
            price=0,
            auto_price=True,
            auto_end_time=True,
            prevents_overlap=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

    # def test_create_appointment_without_activities_auto_fields_on(self):
    # """Test creating an appointment without activities and auto fields enabled, using form"""

    #    data = self._build_form_data(
    #        date_value=date.today(),
    #        start_time="14:00",
    #        end_time="15:00",
    #        price=70,
    #        auto_price=True,
    #        auto_end_time=True,
    #        providers=[self.provider],
    #        recipients=[self.recipient],
    #        activities=[],  # no activities
    #    )
    #    appointment = self._submit_and_save_form(data)
    #    self._assert_base_fields(appointment, 70, "14:00", "15:00", True, True)
    #    self._assert_m2m_counts(appointment, activities_count=0)


class AppointmentTimeVerificationFormTest(AppointmentTestMixin, FormHelperMixin):
    def test_create_appointment_with_coherent_time(self):
        """Test suite to verify the correctness of appointment start and end times, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_appointment_with_inconsistent_time(self):
        """Test creating a complete appointment with auto fields enabled, using form"""
        data = self._build_form_data(
            date_value=date.today(),
            start_time="15:00",
            end_time="14:00",
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        form = AppointmentAdminForm(data=data)
        # Expect invalid and specific message on start_time
        self.assertFalse(form.is_valid())
        err_list = form.errors.get("start_time", [])
        self.assertTrue(any("The start time" in str(m) for m in err_list))


class AppointmentBlockVerificationFormTest(AppointmentTestMixin, FormHelperMixin):
    """Test suite to verify blocked appointment behavior and overlap rules."""

    def test_create_blocked_appointment_overlap_on(self):
        """
        Test creating a blocked appointment where overlaps are prevented.

        This scenario is valid and should not raise any errors.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            is_blocked=True,
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False, True)
        self._assert_m2m_counts(appointment)

    def test_create_blocked_appointment_overlap_off(self):
        """
        Test creating a blocked appointment where overlaps are allowed (prevents_overlap=False).

        Expected Behavior:
            - This configuration is invalid because a blocked appointment must prevent overlaps.
            - A error is returned with the expected message.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            is_blocked=True,
            prevents_overlap=False,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        form = AppointmentAdminForm(data=data)
        self.assertFalse(form.is_valid())
        err_list = form.errors.get("is_blocked", [])
        self.assertTrue(any("cannot be marked as blocked" in str(m) for m in err_list))


class AppointmentOverlapVerificationFormTest(AppointmentTestMixin, FormHelperMixin):
    """
    Test suite to validate appointment creation and modification in scenarios involving
    overlapping schedules, boundary times, and provider availability.
    """

    def setUp(self):
        """Prepare a base appointment from 14:00 to 15:00 to use in overlap tests."""
        super().setUp()
        self.base_appointment = Appointment.objects.create(
            price=70,
            start_time="14:00",
            end_time="15:00",
            date=date.today(),
            auto_price=False,
            auto_end_time=False,
        )
        self.base_appointment.save()
        self.base_appointment = self._add_m2m(self.base_appointment)

    def test_create_appointment_overlapping_another(self):
        """
        Ensure that creating an appointment with the exact same start and end time
        as an existing one return a error due to schedule conflict.
        """
        today = date.today()
        data = self._build_form_data(
            date_value=today,
            start_time="14:00",
            end_time="15:00",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],  # provider same as base appointment
            recipients=[self.recipient],
            activities=[self.activity],
        )
        form = AppointmentAdminForm(data=data)
        self.assertFalse(form.is_valid())
        msgs = form.errors.get("start_time", [])
        self.assertTrue(any(str(today) in str(m) for m in msgs))
        self.assertTrue(any("Schedule conflict" in str(m) for m in msgs))

    def test_create_appointment_fully_inside_another(self):
        """
        Ensure that creating an appointment fully inside the time range of
        another appointment (e.g., 14:30–14:50 inside 14:00–15:00) return an error.
        """
        today = date.today()
        data = self._build_form_data(
            date_value=today,
            start_time="14:30",
            end_time="14:50",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        form = AppointmentAdminForm(data=data)
        self.assertFalse(form.is_valid())
        msgs = form.errors.get("start_time", [])
        self.assertTrue(any("Schedule conflict" in str(m) for m in msgs))

    def test_create_appointment_starts_at_previous_end_time(self):
        """
        Verify that creating an appointment that ends exactly at the start time
        of another (13:00–14:00 before 14:00–15:00) does not return an error.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="13:00",
            end_time="14:00",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 70, "13:00", "14:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_appointment_ends_at_next_start_time(self):
        """
        Verify that creating an appointment that starts exactly when another ends
        (15:00–16:00 after 14:00–15:00) does not return an error.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="15:00",
            end_time="16:00",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)
        self._assert_base_fields(appointment, 70, "15:00", "16:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_appointment_date_change_causes_overlap(self):
        """
        Validate that changing an appointment's date to a day where it overlaps
        with an existing appointment raises a ValidationError.
        """
        tomorrow = date.today() + timedelta(days=1)
        data = self._build_form_data(
            date_value=tomorrow,
            start_time="14:00",
            end_time="15:00",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)

        # sanity checks
        self._assert_base_fields(appointment, 70, "14:00", "15:00", False, False)
        self._assert_m2m_counts(appointment)

        # moving it to today should conflict with base_appointment
        appointment.date = date.today()
        with self.assertRaisesMessage(
            ValidationError,
            "Schedule conflict",
        ):
            appointment.save()

    def test_appointment_date_change_starts_at_previous_end_time(self):
        """
        Ensure that moving an appointment to a date where it ends exactly when
        another appointment starts is still valid.
        """
        tomorrow = date.today() + timedelta(days=1)
        data = self._build_form_data(
            date_value=tomorrow,
            start_time="13:00",
            end_time="14:00",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)

        # move to today (ends at 14:00 which is start of base appointment) — should be OK
        appointment.date = date.today()
        appointment.save()
        self._assert_base_fields(appointment, 70, "13:00", "14:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_appointment_date_change_ends_at_next_start_time(self):
        """
        Ensure that moving an appointment to a date where it starts exactly
        when another appointment ends is still valid.
        """
        tomorrow = date.today() + timedelta(days=1)
        data = self._build_form_data(
            date_value=tomorrow,
            start_time="15:00",
            end_time="16:00",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)

        # move to today (starts at 15:00 which is end of base appointment) — should be OK
        appointment.date = date.today()
        appointment.save()
        self._assert_base_fields(appointment, 70, "15:00", "16:00", False, False)
        self._assert_m2m_counts(appointment)

    def test_create_appointment_with_one_provider_unavailable(self):
        """
        Validate that when one provider is already booked during a time slot,
        creating a new appointment with the same provider return an error.
        """
        today = date.today()
        # base_appointment already exists in setUp with provider self.provider

        data = self._build_form_data(
            date_value=today,
            start_time="14:00",
            end_time="15:00",
            prevents_overlap=True,
            price=70,
            auto_price=False,
            auto_end_time=False,
            # try to create another appointment with multiple providers (one of them unavailable)
            providers=[self.provider, self.provider2]
            if hasattr(self, "provider2")
            else [self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        # If you really want to test multiple providers and one unavailable,
        # ensure self.provider2 exists in AppointmentTestMixin. Otherwise this reduces to single provider conflict.
        form = AppointmentAdminForm(data=data)
        self.assertFalse(form.is_valid())
        msgs = form.errors.get("start_time", [])
        self.assertTrue(any("Schedule conflict" in str(m) for m in msgs))


class AppointmentDuplicateProvidersRecipientsFormTest(
    AppointmentTestMixin, FormHelperMixin
):
    """
    Test cases to validate that an Appointment cannot have duplicate
    providers or recipients in its many-to-many relationships.
    """

    def test_cannot_add_duplicate_providers(self):
        """
        Ensure that attempting to add a duplicate provider to an appointment
        raises a ValidationError.

        Steps:
        1. Create a new appointment and add the initial provider via _add_m2m.
        2. Attempt to create a duplicate entry in the AppointmentProvider through table.
        3. Expect a error indicating the provider already exists for this appointment.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)

        # Attempt to create a duplicate in the through table directly; should raise ValidationError
        with self.assertRaisesMessage(
            ValidationError,
            "Appointment provider with this Appointment and Provider already exists.",
        ):
            baker.make(
                "appointments.AppointmentProvider",
                appointment=appointment,
                provider=self.provider,
            )

    def test_cannot_add_duplicate_recipients(self):
        """
        Ensure that attempting to add a duplicate recipient to an appointment
        raises a ValidationError.

        Steps:
        1. Create a new appointment and add the initial recipient via _add_m2m.
        2. Attempt to create a duplicate entry in the AppointmentRecipient through table.
        3. Expect a ValidationError indicating the recipient already exists for this appointment.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=70,
            auto_price=False,
            auto_end_time=False,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)

        with self.assertRaisesMessage(
            ValidationError,
            "Appointment recipient with this Appointment and Recipient already exists.",
        ):
            baker.make(
                "appointments.AppointmentRecipient",
                appointment=appointment,
                recipient=self.recipient,
            )


class AppointmentAutoFieldsOnActivityUpdateFormTest(
    AppointmentTestMixin, FormHelperMixin
):
    """
    Test suite to verify that automatic fields (`auto_price` and `auto_end_time`)
    in Appointment objects remain unchanged when the attributes of linked
    Activity instances are updated after the appointment is created.
    """

    def test_auto_fields_remain_when_activity_price_changes(self):
        """
        Verify that updating the price of an associated Activity
        does not automatically recalculate `price` or `end_time`
        in an Appointment with `auto_price` and `auto_end_time` enabled.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=0,
            auto_price=True,
            auto_end_time=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)

        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

        # change activity price
        self.activity.price = 70
        self.activity.save()

        appointment.refresh_from_db()
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)

    def test_auto_fields_remain_when_activity_duration_changes(self):
        """
        Verify that updating the duration_time of an associated Activity
        does not automatically recalculate `price` or `end_time`
        in an Appointment with `auto_price` and `auto_end_time` enabled.
        """
        data = self._build_form_data(
            date_value=date.today(),
            start_time="14:00",
            end_time="15:00",
            price=0,
            auto_price=True,
            auto_end_time=True,
            providers=[self.provider],
            recipients=[self.recipient],
            activities=[self.activity],
        )
        appointment = self._submit_and_save_form(data)

        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)
        self._assert_m2m_counts(appointment)

        # change activity duration
        self.activity.duration_time = timedelta(minutes=60)
        self.activity.save()

        appointment.refresh_from_db()
        self._assert_base_fields(appointment, 100, "14:00", "15:30", True, True)


class FormWizardTestMixin(TestCase):
    def setUp(self):
        """
        Store the URL of the first valid step to reuse in tests.
        This represents the initial step of the form wizard.
        """
        self.initial_step = reverse("wizard", kwargs={"step": 1})
        self.provider = baker.make(USER, username="provider")
        self.recipient = baker.make(USER, username="recipient")
        self.activity = baker.make(
            "activities.Activity", name="activity", duration_time=timedelta(minutes=60)
        )

        self.provider2 = baker.make(USER, username="provider2")
        self.recipient2 = baker.make(USER, username="recipient2")
        self.activity2 = baker.make(
            "activities.Activity", name="activity2", duration_time=timedelta(minutes=60)
        )


@override_settings(ROOT_URLCONF="tests.urls")
class FormWizardViewStructuralTests(FormWizardTestMixin):
    def test_load_initial_step(self):
        """
        Test that the first step of the wizard loads successfully.
        Ensures the view returns HTTP 200 for the initial step.
        """
        url = self.initial_step
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_redirect_if_step_does_not_exist(self):
        """
        Test the behavior when a non-existent step is requested.
        The wizard should redirect to the initial step.
        """
        url = reverse("wizard", kwargs={"step": 100})
        response = self.client.get(url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], self.initial_step)

    def test_redirect_if_previous_step_not_completed(self):
        """
        Test the behavior when requesting a step whose previous step
        has not been completed. The wizard should redirect to the first step.
        """
        url = reverse("wizard", kwargs={"step": 2})
        response = self.client.get(url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], self.initial_step)


@override_settings(ROOT_URLCONF="tests.urls")
@override_settings(
    ROOT_URLCONF="tests.urls",
    TEMPLATES=[
        {
            **settings.TEMPLATES[0],
            "DIRS": ["tests/templates"],
        }
    ],
)
class FormWizardFlowTests(FormWizardTestMixin):
    def setUp(self):
        super().setUp()
        # Create sample appointments with different times and constraints
        self.ap1 = baker.make(
            Appointment,
            start_time=time(8, 0),
            end_time=time(8, 0),
            auto_end_time=False,
            is_blocked=False,
            prevents_overlap=False,
        )
        self.ap2 = baker.make(
            Appointment,
            start_time=time(10, 0),
            end_time=time(11, 30),
            auto_end_time=False,
            is_blocked=False,
        )
        self.ap3 = baker.make(
            Appointment,
            start_time=time(11, 30),
            end_time=time(12, 0),
            auto_end_time=False,
            is_blocked=True,
        )

        # Link recipients, providers and activities to the created appointments
        for appointment in [self.ap1, self.ap2, self.ap3]:
            appointment.recipients.add(self.recipient)
            appointment.providers.add(self.provider)
            appointment.activities.add(self.activity)

    def _advance_to_step(self, step, follow=False):
        """
        Helper method that simulates going through the wizard step by step.
        Automatically fills in each step with valid data until reaching the given step.
        """
        url = reverse("wizard", kwargs={"step": 1})

        if step >= 1:
            data = {"recipients": [self.recipient.pk, self.recipient2.pk]}
            response = self.client.post(url, data=data, follow=follow)
            url = response.request["PATH_INFO"]

        if step >= 2:
            data = {"providers": [self.provider.pk, self.provider2.pk]}
            response = self.client.post(url, data=data, follow=follow)
            url = response.request["PATH_INFO"]

        if step >= 3:
            data = {"activities": [self.activity.pk, self.activity2.pk]}
            response = self.client.post(url, data=data, follow=follow)
            url = response.request["PATH_INFO"]

        if step >= 4:
            data = {"date": date.today()}
            response = self.client.post(url, data=data, follow=follow)
            url = response.request["PATH_INFO"]

        if step >= 5:
            data = {"start_time": time(8, 0)}
            response = self.client.post(url, data=data, follow=follow)
            url = response.request["PATH_INFO"]

        return response

    def test_step1_loads_with_correct_choices(self):
        """Step 1 should load with the available recipients as choices."""
        url = self.initial_step
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 1)
        self.assertContains(response, self.recipient.username)
        self.assertContains(response, self.recipient2.username)

    def test_step1_invalid_null_data(self):
        """Submitting step 1 without recipients should return validation errors."""
        url = self.initial_step
        response = self.client.post(url, data={}, follow=True)

        form = response.context["form"]

        self.assertIn("recipients", form.errors)
        self.assertEqual(form.errors["recipients"], ["This field is required."])
        self.assertEqual(response.request["PATH_INFO"], self.initial_step)

    def test_step1_valid_data_advances_to_next_step(self):
        """Valid recipients selection should redirect to step 2."""
        response = self._advance_to_step(1)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("wizard", kwargs={"step": 2}))

    def test_step2_loads_with_correct_choices(self):
        """Step 2 should load with the available providers as choices."""
        response = self._advance_to_step(1, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 2)
        self.assertContains(response, self.provider.username)
        self.assertContains(response, self.provider2.username)

    def test_step2_invalid_null_data(self):
        """Submitting step 2 without providers should return validation errors."""
        response = self._advance_to_step(1, follow=True)
        url = response.request["PATH_INFO"]

        response = self.client.post(url, data={})
        form = response.context["form"]

        self.assertIn("providers", form.errors)
        self.assertEqual(response.context["step"], 2)
        self.assertEqual(form.errors["providers"], ["This field is required."])
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 2})
        )

    def test_step2_valid_data_advances_to_next_step(self):
        """Valid providers selection should redirect to step 3."""
        response = self._advance_to_step(2, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 3)
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 3})
        )

    def test_step3_loads_with_correct_choices(self):
        """Step 3 should load with the available activities as choices."""
        response = self._advance_to_step(2, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 3)
        self.assertContains(response, self.activity.name)
        self.assertContains(response, self.activity2.name)

    def test_step3_invalid_null_data(self):
        """Submitting step 3 without activities should return validation errors."""
        response = self._advance_to_step(2, follow=True)
        url = response.request["PATH_INFO"]

        response = self.client.post(url, data={})
        form = response.context["form"]

        self.assertIn("activities", form.errors)
        self.assertEqual(response.context["step"], 3)
        self.assertEqual(form.errors["activities"], ["This field is required."])
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 3})
        )

    def test_step3_valid_data_advances_to_next_step(self):
        """Valid activities selection should redirect to step 4."""
        response = self._advance_to_step(3, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 4)
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 4})
        )

    def test_step4_loads_with_correct_choices(self):
        """Step 4 should load with a date picker field."""
        response = self._advance_to_step(3, follow=True)

        response = self.client.get(reverse("wizard", kwargs={"step": 4}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 4)
        self.assertContains(response, 'name="date"')

    def test_step4_invalid_null_data(self):
        """Submitting step 4 without a date should return validation errors."""
        response = self._advance_to_step(3, follow=True)
        url = response.request["PATH_INFO"]

        response = self.client.post(url, data={})
        form = response.context["form"]

        self.assertIn("date", form.errors)
        self.assertEqual(response.context["step"], 4)
        self.assertEqual(form.errors["date"], ["This field is required."])
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 4})
        )

    def test_step4_valid_data_advances_to_next_step(self):
        """Valid date selection should redirect to step 5."""
        response = self._advance_to_step(3, follow=True)
        url = response.request["PATH_INFO"]

        data = {"date": date.today().isoformat()}
        response = self.client.post(url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 5)
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 5})
        )

    def test_step5_loads_with_correct_choices(self):
        """Step 5 should load available start times, excluding unavailable slots."""
        response = self._advance_to_step(4, follow=True)

        response = self.client.get(reverse("wizard", kwargs={"step": 5}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 5)
        self.assertContains(response, 'name="start_time"')

        form = response.context["form"]
        choices = form.fields["start_time"].choices

        # Validate availability due to already scheduled appointments
        self.assertIn(("08:00:00", "08:00"), choices)
        self.assertNotIn(("10:00:00", "10:00"), choices)
        self.assertNotIn(("11:30:00", "11:30"), choices)
        self.assertNotIn(("11:40:00", "11:40"), choices)
        self.assertNotIn(("11:50:00", "11:50"), choices)
        self.assertNotIn(("12:00:00", "12:00"), choices)

        # Validate availability according to default generation boundaries
        self.assertNotIn(("07:50:00", "07:50"), choices)
        self.assertNotIn(("18:10:00", "18:10"), choices)
        self.assertIn(("16:00:00", "16:00"), choices)

    def test_step5_invalid_null_data(self):
        """Submitting step 5 without selecting a start time should return validation errors."""
        response = self._advance_to_step(4, follow=True)
        url = response.request["PATH_INFO"]

        response = self.client.post(url, data={})
        form = response.context["form"]

        self.assertIn("start_time", form.errors)
        self.assertEqual(response.context["step"], 5)
        self.assertEqual(form.errors["start_time"], ["This field is required."])
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 5})
        )

    def test_step5_valid_data_advances_to_next_step(self):
        """Valid start time selection should redirect to step 6 (confirmation)."""
        response = self._advance_to_step(4, follow=True)
        url = response.request["PATH_INFO"]

        data = {"start_time": time(8, 0).isoformat()}
        response = self.client.post(url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 6)
        self.assertEqual(
            response.request["PATH_INFO"], reverse("wizard", kwargs={"step": 6})
        )

    def test_step6_loads_confirmation(self):
        """Step 6 should display the confirmation button."""
        response = self._advance_to_step(5, follow=True)
        url = response.request["PATH_INFO"]

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["step"], 6)
        self.assertContains(response, "submit")

    def test_step6_post_without_data(self):
        """Posting step 6 without additional data should finalize and create the appointment."""
        response = self._advance_to_step(5, follow=True)
        url = response.request["PATH_INFO"]

        response = self.client.post(url, data={}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Appointment created successfully!")

    def test_step6_post_creates_appointment(self):
        """Final step should create a new appointment with all selected recipients, providers, and activities."""
        self.assertEqual(
            Appointment.objects.exclude(
                pk__in=[self.ap1.pk, self.ap2.pk, self.ap3.pk]
            ).count(),
            0,
        )

        response = self._advance_to_step(5, follow=True)
        url = response.request["PATH_INFO"]

        response = self.client.post(url, data={}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("wizard_success"))

        self.assertEqual(
            Appointment.objects.exclude(
                pk__in=[self.ap1.pk, self.ap2.pk, self.ap3.pk]
            ).count(),
            1,
        )
        appointment = Appointment.objects.last()

        self.assertEqual(
            [r.pk for r in appointment.recipients.all()],
            [self.recipient.pk, self.recipient2.pk],
        )
        self.assertEqual(
            [p.pk for p in appointment.providers.all()],
            [self.provider.pk, self.provider2.pk],
        )
        self.assertEqual(
            [a.pk for a in appointment.activities.all()],
            [self.activity.pk, self.activity2.pk],
        )
