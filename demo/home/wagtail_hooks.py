from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import DemoModel


from wagtail_pdf_view.modeladmin.mixins import PdfViewButtonHelper

class MyCustomButtonHelper(PdfViewButtonHelper):
    
    custom_object_buttons = [
        ("custom", {"label": 'Custom Label'}),
        ("some_action", {"label": 'Another Action'}),
    ]


from wagtail_pdf_view.modeladmin.mixins import ModelAdminPdfViewMixin, ModelAdminPdfAdminViewMixin


@modeladmin_register
class DemoModelWagtailAdmin(ModelAdminPdfViewMixin, ModelAdminPdfAdminViewMixin, ModelAdmin):
    model = DemoModel
    menu_label = 'Demo Model'
    menu_icon = 'cog'
    menu_order = 800
    
    button_helper_class = MyCustomButtonHelper

    def custom_view(self, request, instance_pk):
        # Change the needed permission
        return self.pdf_admin_view(request, instance_pk, permission_required="can_view_pdf")
    
    def another_custom_view(self, request, instance_pk):
        return self.pdf_admin_view(request, instance_pk, template_name="path/to/template")
    
    
    def get_custom_object_views(self):
        return [
            ("custom", self.custom_view),
            ("some_action", self.another_custom_view),
        ]
    
    
    
    
