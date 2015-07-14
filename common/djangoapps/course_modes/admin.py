"""
Django admin page for course modes
"""
from django.conf import settings
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import widgets

from pytz import timezone, UTC

from ratelimitbackend import admin
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from opaque_keys import InvalidKeyError

from util.date_utils import get_time_display
from xmodule.modulestore.django import modulestore
from course_modes.models import CourseMode

# Technically, we shouldn't be doing this, since verify_student is defined
# in LMS, and course_modes is defined in common.
#
# Once we move the responsibility for administering course modes into
# the Course Admin tool, we can remove this dependency and expose
# verification deadlines as a separate Django model admin.
#
# The admin page will work in both LMS and Studio,
# but the test suite for Studio will fail because
# the verification deadline table won't exist.
from verify_student import models as verification_models


class CourseModeForm(forms.ModelForm):

    class Meta(object):  # pylint: disable=missing-docstring
        model = CourseMode

    COURSE_MODE_SLUG_CHOICES = (
        [(CourseMode.DEFAULT_MODE_SLUG, CourseMode.DEFAULT_MODE_SLUG)] +
        [(mode_slug, mode_slug) for mode_slug in CourseMode.VERIFIED_MODES] +
        [(CourseMode.NO_ID_PROFESSIONAL_MODE, CourseMode.NO_ID_PROFESSIONAL_MODE)] +
        [(mode_slug, mode_slug) for mode_slug in CourseMode.CREDIT_MODES]
    )

    mode_slug = forms.ChoiceField(choices=COURSE_MODE_SLUG_CHOICES, label=_("Mode"))

    # The verification deadline is stored outside the course mode in the verify_student app.
    # (we used to use the course mode expiration_datetime as both an upgrade and verification deadline).
    # In order to make this transition easier, we include the verification deadline as a custom field
    # in the course mode admin form.  Longer term, we will deprecate the course mode Django admin
    # form in favor of an external Course Administration Tool.
    verification_deadline = forms.SplitDateTimeField(
        label=_("Verification Deadline"),
        required=False,
        help_text=_(
            "OPTIONAL: After this date/time, users will no longer be able to submit photos for verification.  "
            "This appies ONLY to modes that require verification."
        ),
        widget=widgets.AdminSplitDateTime,
    )

    def __init__(self, *args, **kwargs):
        super(CourseModeForm, self).__init__(*args, **kwargs)

        if self.instance.expiration_datetime:
            default_tz = timezone(settings.TIME_ZONE)
            # django admin is using default timezone. To avoid time conversion from db to form
            # convert the UTC object to naive and then localize with default timezone.
            expiration_datetime = self.instance.expiration_datetime.replace(tzinfo=None)
            self.initial["expiration_datetime"] = default_tz.localize(expiration_datetime)

        # Load the verification deadline
        # Since this is stored on a model in verify student, we need to load it from there.
        if self.instance.course_id and self.instance.mode_slug in CourseMode.VERIFIED_MODES:
            deadline = verification_models.VerificationDeadline.deadline_for_course(self.instance.course_id)
            self.initial["verification_deadline"] = deadline

    def clean_course_id(self):
        course_id = self.cleaned_data['course_id']
        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            try:
                course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
            except InvalidKeyError:
                raise forms.ValidationError("Cannot make a valid CourseKey from id {}!".format(course_id))

        if not modulestore().has_course(course_key):
            raise forms.ValidationError("Cannot find course with id {} in the modulestore".format(course_id))

        return course_key

    def clean_expiration_datetime(self):
        """changing the tzinfo for a given datetime object"""
        # django admin saving the date with default timezone to avoid time conversion from form to db
        # changes its tzinfo to UTC
        if self.cleaned_data.get("expiration_datetime"):
            return self.cleaned_data.get("expiration_datetime").replace(tzinfo=UTC)

    def clean_verification_deadline(self):
        """
        Ensure that the verification deadline we save uses the UTC timezone.
        """
        if self.cleaned_data.get("verification_deadline"):
            return self.cleaned_data.get("verification_deadline").replace(tzinfo=UTC)

    def clean(self):
        """
        Clean the form fields.
        This is the place to perform checks that involve multiple form fields.
        """
        cleaned_data = super(CourseModeForm, self).clean()
        mode_slug = cleaned_data["mode_slug"]
        upgrade_deadline = cleaned_data["expiration_datetime"]
        verification_deadline = cleaned_data["verification_deadline"]

        # Allow upgrade deadlines ONLY for the "verified" mode
        # This avoids a nasty error condition in which the upgrade deadline is set
        # for a professional education course before the enrollment end date.
        # When this happens, the course mode expires and students are able to enroll
        # in the course for free.  To avoid this, we explicitly prevent admins from
        # setting an upgrade deadline for any mode except "verified" (which has an upgrade path).
        if upgrade_deadline is not None and mode_slug != CourseMode.VERIFIED:
            raise forms.ValidationError(
                'Only the "verified" mode can have an upgrade deadline.  '
                'For other modes, please set the enrollment end date in Studio.'
            )

        # Verification deadlines are allowed only for verified modes
        if verification_deadline is not None and mode_slug not in CourseMode.VERIFIED_MODES:
            raise forms.ValidationError("Verification deadline can be set only for verified modes.")

        # Verification deadline must be after the upgrade deadline
        if verification_deadline is not None:
            if upgrade_deadline is None or verification_deadline < upgrade_deadline:
                raise forms.ValidationError("Verification deadline must be after the upgrade deadline.")

        return cleaned_data

    def save(self, commit=True):
        """
        Save the form data.
        """
        course_key = self.cleaned_data.get("course_id")
        verification_deadline = self.cleaned_data.get("verification_deadline")

        # Since the verification deadline is stored in a separate model,
        # we need to handle saving this ourselves.
        # Note that verification deadline can be `None` here if
        # the deadline is being disabled.
        if course_key is not None:
            verification_models.VerificationDeadline.set_deadline(course_key, verification_deadline)

        return super(CourseModeForm, self).save(commit=commit)


class CourseModeAdmin(admin.ModelAdmin):
    """Admin for course modes"""
    form = CourseModeForm

    fields = (
        'course_id',
        'mode_slug',
        'mode_display_name',
        'min_price',
        'currency',
        'expiration_datetime',
        'verification_deadline',
        'sku'
    )

    search_fields = ('course_id',)

    list_display = (
        'id',
        'course_id',
        'mode_slug',
        'min_price',
        'expiration_datetime_custom',
        'sku'
    )

    def expiration_datetime_custom(self, obj):
        """adding custom column to show the expiry_datetime"""
        if obj.expiration_datetime:
            return get_time_display(obj.expiration_datetime, '%B %d, %Y, %H:%M  %p')

    # Display a more user-friendly name for the custom expiration datetime field
    # in the Django admin list view.
    expiration_datetime_custom.short_description = "Upgrade Deadline"

admin.site.register(CourseMode, CourseModeAdmin)
