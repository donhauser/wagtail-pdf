
from wagtail import hooks

from .views import InvoiceModelViewSet


@hooks.register("register_admin_viewset")
def register_viewset():
    return InvoiceModelViewSet()
