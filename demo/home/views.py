
from wagtail.admin.viewsets.model import ModelViewSet

from wagtail_pdf_view.views import PdfAdminViewSetMixin
#from wagtail_pdf_view_tex.views import WagtailTexAdminView

from .models import DemoModel


from wagtail_pdf_view.views import WagtailWeasyView, PdfViewSetMixin
from wagtail_pdf_view.hooks import register_pdf_view


# register a pdf view for the model Invoice
# i.e. urlpatterns += [path('pdf/invoice/<str:pk>/', WagtailWeasyView.as_view(model=Invoice), name='invoice-detail')]

@register_pdf_view('demo/<str:pk>/')
class DemoModelView(WagtailWeasyView):
    model = DemoModel

class DemoModelViewSet(PdfAdminViewSetMixin, ModelViewSet):
    add_to_admin_menu = True
    model = DemoModel
    menu_label = 'Demo Model'
    icon = 'cog'

    name = 'demo'

    # Change the view class to render the view using latex
    #pdf_view_class = WagtailTexAdminView

    # Admin settings for 'view pdf' only
    # (not considered in the preview, which just uses model.serve_preview_pdf())
    #pdf_options = {...}
    #pdf_attachment = True
    #pdf_template_name = "path/to/your/template.html"
