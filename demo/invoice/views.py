
from wagtail.admin.viewsets.model import ModelViewSet

from wagtail_pdf_view.views import WagtailWeasyView, PdfViewSetMixin
from wagtail_pdf_view.hooks import register_pdf_view

from .models import Invoice


# register a pdf view for the model Invoice
# i.e. urlpatterns += [path('pdf/invoice/<str:pk>/', WagtailWeasyView.as_view(model=Invoice), name='invoice-detail')]

@register_pdf_view('invoice/<str:pk>/')
class InvoiceView(WagtailWeasyView):
    model = Invoice

class InvoiceModelViewSet(PdfViewSetMixin, ModelViewSet):
    add_to_admin_menu = True
    model = Invoice
    menu_label = 'Invoices'
    icon = 'cog'

    name = 'invoice'
