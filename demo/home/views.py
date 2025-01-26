
from wagtail.admin.viewsets.model import ModelViewSet

from wagtail_pdf_view.views import PdfAdminViewSetMixin, PreviewableViewSetMixin

from .models import DemoModel


class DemoModelViewSet(PdfAdminViewSetMixin, PreviewableViewSetMixin, ModelViewSet):
    add_to_admin_menu = True
    model = DemoModel
    menu_label = 'Demo Model'
    icon = 'cog'

    name = 'demo'

    # Admin settings for 'view pdf' only
    # (not considered in the preview, which just uses model.serve_preview_pdf())
    #pdf_options = {...}
    #pdf_attachment = True
    #pdf_template_name = "path/to/your/template.html"
