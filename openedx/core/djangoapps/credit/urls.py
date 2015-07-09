"""
URLs for the credit app.
"""
from django.conf.urls import patterns, url

from .views import create_credit_request, credit_provider_callback
from .api.provider import get_credit_provider_info

urlpatterns = patterns(
    '',

    url(
        r"^v1/provider/(?P<provider_id>[^/]+)/$",
        get_credit_provider_info,
        name="get_provider_info"
    ),
    url(
        r"^v1/provider/(?P<provider_id>[^/]+)/request/$",
        create_credit_request,
        name="create_request"
    ),

    url(
        r"^v1/provider/(?P<provider_id>[^/]+)/callback/?$",
        credit_provider_callback,
        name="provider_callback"
    ),
)
