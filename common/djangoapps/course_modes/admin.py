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

    # TODO -- explain this
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

        if self.instance.course_id:
            from verify_student.models import VerificationDeadline
            deadline = VerificationDeadline.deadline_for_course(self.instance.course_id)
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
        """TODO """
        if self.cleaned_data.get("verification_deadline"):
            return self.cleaned_data.get("verification_deadline").replace(tzinfo=UTC)

    def clean(self):
        """TODO """
        cleaned_data = super(CourseModeForm, self).clean()
        verification_deadline = cleaned_data["verification_deadline"]
        upgrade_deadline = cleaned_data["expiration_datetime"]
        mode_slug = cleaned_data["mode_slug"]

        # Verification deadlines are allowed only for verified modes
        if verification_deadline is not None and mode_slug not in CourseMode.VERIFIED_MODES:
            raise forms.ValidationError("Verification deadline can be set only for verified modes.")

        # Verification deadline must be after the upgrade deadline
        if verification_deadline is not None and upgrade_deadline is not None:
            if verification_deadline < upgrade_deadline:
                raise forms.ValidationError("Verification deadline must be after the upgrade deadline.")

        return cleaned_data

    def save(self, commit=True):
        course_key = self.cleaned_data.get("course_id")
        verification_deadline = self.cleaned_data.get("verification_deadline")

        if course_key is not None:
            from verify_student.models import VerificationDeadline
            VerificationDeadline.set_deadline(course_key, verification_deadline)

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

    expiration_datetime_custom.short_description = "Upgrade Deadline"

admin.site.register(CourseMode, CourseModeAdmin)
