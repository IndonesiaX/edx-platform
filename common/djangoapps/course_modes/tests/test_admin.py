"""
Tests for the course modes Django admin interface.
"""
import unittest
from datetime import datetime, timedelta

import ddt
from pytz import timezone, UTC

from django.conf import settings
from django.core.urlresolvers import reverse

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from util.date_utils import get_time_display
from xmodule.modulestore.tests.factories import CourseFactory
from student.tests.factories import UserFactory
from course_modes.models import CourseMode
from course_modes.admin import CourseModeForm

# TODO -- explain
from verify_student.models import VerificationDeadline


# We can only test this in the LMS because the course modes admin relies
# on verify student, which is not an installed app in Studio, so the verification
# deadline table will not be created.
@unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
class AdminCourseModePageTest(ModuleStoreTestCase):
    """
    Test the course modes Django admin interface.
    """

    def test_expiration_timezone(self):
        # Test that expiration datetimes are saved and retrieved with the timezone set to UTC.
        # This verifies the fix for a bug in which the date displayed to users was different
        # than the date in Django admin.
        user = UserFactory.create(is_staff=True, is_superuser=True)
        user.save()
        course = CourseFactory.create()
        expiration = datetime(2015, 10, 20, 1, 10, 23, tzinfo=timezone(settings.TIME_ZONE))

        data = {
            'course_id': unicode(course.id),
            'mode_slug': 'verified',
            'mode_display_name': 'verified',
            'min_price': 10,
            'currency': 'usd',
            'expiration_datetime_0': expiration.date(),  # due to django admin datetime widget passing as seperate vals
            'expiration_datetime_1': expiration.time(),

        }

        self.client.login(username=user.username, password='test')

        # Create a new course mode from django admin page
        response = self.client.post(reverse('admin:course_modes_coursemode_add'), data=data)
        self.assertRedirects(response, reverse('admin:course_modes_coursemode_changelist'))

        # Verify that datetime is appears on list page
        response = self.client.get(reverse('admin:course_modes_coursemode_changelist'))
        self.assertContains(response, get_time_display(expiration, '%B %d, %Y, %H:%M  %p'))

        # Verify that on the edit page the datetime value appears as UTC.
        resp = self.client.get(reverse('admin:course_modes_coursemode_change', args=(1,)))
        self.assertContains(resp, expiration.date())
        self.assertContains(resp, expiration.time())

        # Verify that the expiration datetime is the same as what we set
        # (hasn't changed because of a timezone translation).
        course_mode = CourseMode.objects.get(pk=1)
        self.assertEqual(course_mode.expiration_datetime.replace(tzinfo=None), expiration.replace(tzinfo=None))


@unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
@ddt.ddt
class AdminCourseModeFormTest(ModuleStoreTestCase):
    """
    Test the course modes Django admin form validation and saving.
    """

    UPGRADE_DEADLINE = datetime.now(UTC)
    VERIFICATION_DEADLINE = UPGRADE_DEADLINE + timedelta(days=5)

    def setUp(self):
        """
        Create a test course.
        """
        super(AdminCourseModeFormTest, self).setUp()
        self.course = CourseFactory.create()

    @ddt.data(
        ("honor", False),
        ("verified", True),
        ("professional", False),
        ("no-id-professional", False),
        ("credit", False),
    )
    @ddt.unpack
    def test_load_verification_deadline(self, mode, expect_deadline):
        # Configure a verification deadline for the course
        VerificationDeadline.set_deadline(self.course.id, self.VERIFICATION_DEADLINE)

        # Configure a course mode with both an upgrade and verification deadline
        # and load the form to edit it.
        form = CourseModeForm({
            "course_id": unicode(self.course.id),
            "mode_slug": mode,
            "mode_display_name": mode,
            "expiration_datetime": self.UPGRADE_DEADLINE if mode == "verified" else None,
            "currency": "usd",
            "min_price": 10,
        })

        # Clean form data and check that the form validated
        self._assert_form_valid(form)

        # Check that the verification deadline is loaded,
        # but ONLY for verified modes.
        if mode in CourseMode.VERIFIED_MODES:
            self.assertEqual(form.cleaned_data["verification_deadline"], self.VERIFICATION_DEADLINE)
        else:
            self.assertIs(form.cleaned_data["verification_deadline"], None)

    def test_set_verification_deadline(self):
        # Configure a verification deadline for the course
        VerificationDeadline.set_deadline(self.course.id, self.VERIFICATION_DEADLINE)

        # Create the course mode Django admin form
        new_deadline = self.VERIFICATION_DEADLINE + timedelta(days=1)
        course_mode = CourseMode.objects.create(
            course_id=self.course.id,
            mode_slug="verified"
        )
        form = CourseModeForm({
            "course_id": unicode(self.course.id),
            "mode_slug": "verified",
            "mode_display_name": "Verified Certificate",
            "expiration_datetime": self.UPGRADE_DEADLINE,
            "verification_deadline": new_deadline,
            "currency": "usd",
            "min_price": 10,
        }, instance=course_mode)

        # Save the form
        self._assert_form_valid(form)
        form.save()

        # Check that the deadline was updated
        updated_deadline = VerificationDeadline.deadline_for_course(self.course.id)
        self.assertEqual(updated_deadline, new_deadline)

    def test_disable_verification_deadline(self):
        self.fail("TODO")

    @ddt.data("honor", "professional", "no-id-professional", "credit")
    def test_validate_upgrade_deadline_only_for_verified(self, course_mode):
        self.fail("TODO")

    @ddt.data("honor", "professional", "no-id-professional", "credit")
    def test_validate_verification_deadline_only_for_verified(self, course_mode):
        self.fail("TODO")

    def test_verification_deadline_after_upgrade_deadline(self):
        self.fail("TODO")

    def _configure(self, mode, upgrade_deadline=None, verification_deadline=None):
        """TODO """
        course_mode = CourseMode.objects.create(
            mode_slug=mode,
            mode_display_name=mode,
        )

        if upgrade_deadline is not None:
            course_mode.upgrade_deadline = upgrade_deadline
            course_mode.save()

        VerificationDeadline.set_deadline(self.course.id, verification_deadline)

        return CourseModeForm(instance=course_mode)

    def _assert_form_valid(self, form):
        """TODO """
        self.assertTrue(form.is_valid(), msg="Validation errors: {errors}".format(errors=form.errors))
