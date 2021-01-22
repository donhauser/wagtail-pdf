from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import DemoModel

@modeladmin_register
class DemoModelWagtailAdmin(ModelAdmin):
    model = DemoModel
    menu_label = 'Demo Model'
    menu_icon = 'cog'
    menu_order = 800
    add_to_settings_menu = False
    exclude_from_explorer = False
     
