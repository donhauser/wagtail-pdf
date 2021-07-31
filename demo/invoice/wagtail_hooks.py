from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import Invoice


from wagtail_pdf_view.modeladmin.mixins import ModelAdminPdfViewMixin, ModelAdminPdfAdminViewMixin

@modeladmin_register
class InvoiceWagtailAdmin(ModelAdminPdfViewMixin, ModelAdmin):
    model = Invoice
    menu_label = 'Invoices'
    menu_icon = 'cog'
    menu_order = 800
    
    
