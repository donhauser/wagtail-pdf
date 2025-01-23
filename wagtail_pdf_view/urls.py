
from django.conf import settings
from django.urls import include, path, re_path
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.static import serve

from wagtail import hooks
from wagtail.utils.urlpatterns import decorate_urlpatterns

from .utils import PDF_VIEWER


@xframe_options_sameorigin
def serve_sameorigin(*args, **kwargs):
    return serve(*args, **kwargs)

app_name = 'wagtail_pdf_view'

urlpatterns = []

if PDF_VIEWER.get('route'):
    urlpatterns += [
        re_path(PDF_VIEWER['route'], serve_sameorigin, {'document_root': PDF_VIEWER['document_root']}, name=PDF_VIEWER['name']),
    ]



# Import additional urlpatterns from any apps that define a register_site_urls hook
# The urls are NOT put behind 'admin/'
for fn in hooks.get_hooks('register_pdf_site_urls'):
    urls = fn()
    if urls:
        urlpatterns += urls 
