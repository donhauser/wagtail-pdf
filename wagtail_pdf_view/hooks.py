from django.urls import path
from wagtail import hooks


def register_pdf_view(pattern, name=None):
    """
    Add an automatically generated url path to the decorated pdf view

    e.g. "/pdf/<pattern>"
    """
    def inner(view):

        @hooks.register('register_pdf_site_urls')
        def register_pdf_site_urls():
            if name is None:
                url_name = f"{view.model._meta.app_label}.{view.model._meta.object_name}"
            else:
                url_name = name

            return [
                path(pattern, view.as_view(), name=url_name),
            ]

    return inner
