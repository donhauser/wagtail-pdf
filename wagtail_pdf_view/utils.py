
from django.conf import settings
from django.urls import reverse

from functools import wraps

import urllib.parse

from wagtail.contrib.routable_page.models import route


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
    'args': ['web/viewer.html'],
    'query': 'file',
    'route': r'^static/pdf.js/(?P<path>.*)$',
    'document_root': settings.STATIC_ROOT + "/" + "pdf.js"
})


def get_pdf_viewer_url(path, viewer=None):
    if viewer is None:
        viewer = PDF_VIEWER
    
    quoted_path = urllib.parse.quote(path)
    
    url = reverse(viewer['name'], args=viewer['args'])

    return f"{url}?{viewer['query']}={quoted_path}"
