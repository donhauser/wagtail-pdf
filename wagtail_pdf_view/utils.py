
from django.conf import settings
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from functools import wraps

import logging

import os

import urllib.parse

from wagtail.contrib.routable_page.models import route

logger = logging.getLogger(__name__)


def route_function(func, pattern, *args, **kwargs):
    """
    Adds the @route decorator to func
    """
    
    @wraps(func) 
    @route(pattern, *args, **kwargs)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    
    return inner
    

PDF_VIEWER = getattr(settings, 'WAGTAIL_PDF_VIEWER', {
    'name': 'pdf.js',
    'app_name': 'wagtail_pdf_view',
    'args': ['web/viewer.html'],
    'query': 'file',
    'route': r'^static/pdf.js/(?P<path>.*)$',
    'document_root': os.path.dirname(__file__) + "/static/pdf.js"
})

if 'document_root' in PDF_VIEWER and not os.path.exists(PDF_VIEWER['document_root']):
    logger.warn(f"The document_root '{PDF_VIEWER['document_root']}' on pdf viewer {PDF_VIEWER['name']} does not exist")

def get_pdf_viewer_url(path, viewer=None):
    if viewer is None:
        viewer = PDF_VIEWER
    
    url_name = viewer['app_name']+':'+viewer['name']

    try:
        url = reverse(url_name, args=viewer['args'])
    except NoReverseMatch as e:
        logger.error(f"Failed to reverse the url of the pdf viewer '{url_name}'. Make sure that you've added `include('wagtail_pdf_view.urls')` to the project `urlpatterns` or reconfigure `settings.WAGTAIL_PDF_VIEWER`")
        raise e
    
    quoted_path = urllib.parse.quote(path)

    return f"{url}?{viewer['query']}={quoted_path}"
