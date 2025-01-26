
from wagtail import hooks

from .views import DemoModelViewSet


@hooks.register("register_admin_viewset")
def register_viewset():
    return DemoModelViewSet()
