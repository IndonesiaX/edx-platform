"""
This file contains utility functions which will responsible for sending emails.
"""

import os

import logging
import pynliner
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.contrib.staticfiles import finders
from django.utils.translation import ugettext as _

from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from eventtracking import tracker

from edxmako.shortcuts import render_to_string
from microsite_configuration import microsite
from openedx.core.djangoapps.user_api.accounts.api import get_account_settings
from xmodule.modulestore.django import modulestore


log = logging.getLogger(__name__)


def send_credit_notifications(username, course_key, email_type="credit_eligibility"):
    """Sends email notification to user on different phases during credit
    course e.g., credit eligibility, credit payment etc.
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        log.error('No user with %s exist', username)
        return

    account_settings = get_account_settings(user)
    course = modulestore().get_course(course_key, depth=0)
    course_display_name = course.display_name
    branded_logo = dict(title='Logo', path=settings.NOTIFICATION_EMAIL_EDX_LOGO, cid=str(uuid.uuid4()))
    tracking_context = tracker.get_tracker().resolve_context()
    tracking_id = str(tracking_context.get('user_id'))
    client_id = str(tracking_context.get('client_id'))
    events = '&t=event&ec=email&ea=open'
    tracking_pixel = 'https://www.google-analytics.com/collect?v=1&tid' + tracking_id + '&cid' + client_id + events
    context = {
        'full_name': account_settings['name'],
        'platform_name': settings.PLATFORM_NAME,
        'course_name': course_display_name,
        'branded_logo': branded_logo['cid'],
        'tracking_pixel': tracking_pixel,
    }

    # TODO: Update the dummy notification messages with real content
    # create the root email message
    notification_msg = MIMEMultipart('related')
    # add 'alternative' part to root email message to encapsulate the plain and
    # HTML versions, so message agents can decide which they want to display.
    msg_alternative = MIMEMultipart('alternative')
    notification_msg.attach(msg_alternative)
    # render the credit notification templates
    subject = None
    if email_type == "credit_eligibility":
        subject = _("Course Credit Eligibility")

        # add alternative plain text message
        email_body_plain = render_to_string('credit_notifications/credit_eligibility_email.txt', context)
        msg_alternative.attach(MIMEText(email_body_plain, _subtype='plain'))

        # add alternative html message
        email_body = with_inline_css(
            render_to_string("credit_notifications/credit_eligibility_email.html", context)
        )
        msg_alternative.attach(MIMEText(email_body, _subtype='html'))

        # add images
        logo_image = attach_image(branded_logo, 'Header Logo')
        if logo_image:
            notification_msg.attach(logo_image)

    from_address = microsite.get_value('default_from_email', settings.DEFAULT_FROM_EMAIL)
    to_address = account_settings['email']

    # send the root email message
    msg = EmailMessage(subject, None, from_address, [to_address])
    msg.attach(notification_msg)
    msg.send()


def with_inline_css(html_without_css):
    """Returns html with inline css if the css file path exists
    else returns html with out the inline css.
    """
    css_filepath = settings.NOTIFICATION_EMAIL_CSS
    if not css_filepath.startswith('/'):
        css_filepath = finders.FileSystemFinder().find(settings.NOTIFICATION_EMAIL_CSS)

    if css_filepath:
        with open(css_filepath, "r") as _file:
            css_content = _file.read()

        # insert style tag in the html and run pyliner.
        html_with_inline_css = pynliner.fromString('<style>' + css_content + '</style>' + html_without_css)
        return html_with_inline_css

    return html_without_css


def attach_image(img_dict, filename):
    """
    Attach images in the email headers.
    """
    img_path = img_dict['path']
    if not img_path.startswith('/'):
        img_path = finders.FileSystemFinder().find(img_path)

    if img_path:
        with open(img_path, 'rb') as img:
            msg_image = MIMEImage(img.read(), name=os.path.basename(img_path))
            msg_image.add_header('Content-ID', '<{}>'.format(img_dict['cid']))
            msg_image.add_header("Content-Disposition", "inline", filename=filename)
        return msg_image
