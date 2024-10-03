from datetime import datetime

from django.db import models

from wagtail.core.models import Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core import blocks
from wagtail.contrib.table_block.blocks import TableBlock

from wagtail.admin.edit_handlers import FieldPanel

from wagtail_pdf_view.mixins import PdfViewPageMixin, PdfModelMixin


from django.conf import settings


class DemoModel(PdfModelMixin, models.Model):
    #attachment = True
    
    # use weasyprint compiler options to enable forms for the live/user view
    pdf_options = {
        'pdf_forms': True
    }
    
    #  use weasyprint compiler options to disable forms in the admin panel
    admin_pdf_options = {
        'pdf_forms': False
    }
    
    creation_date = models.DateField(default=datetime.now)
    
    author = models.CharField(max_length=200)
    
    content = StreamField([
        ("heading", blocks.CharBlock(form_classname="full title")),
        ("text", blocks.RichTextBlock()),
    ], blank=True, use_json_field=True)
    
    panels = [
        FieldPanel("creation_date"),
        FieldPanel("author"),
        FieldPanel("content"),
    ]
    
    template_name = "home/demo_model.html"
    admin_template_name = "home/demo_model_admin.html"
    
    # Alternative: Override the get_template() method
    # def get_template(self, request, *args, extension=None, **kwargs):
    #     return "home/demo_model.html"
    
    class Meta:
        permissions = (
            # IT IS IMPORTANT TO APPEND '_modelname'
            ('can_view_pdf'+'_demomodel', 'can view the demo model pdf'),
        )


class SimplePdfPage(PdfViewPageMixin, Page):
    ## Set the browsers attachment handling
    #attachment = True
    
    #pdf_options = {'dpi': 20}
    
    ## render with LaTeX instead
    # PDF_VIEW_PROVIDER = WagtailTexView
    
    ## Add a custom view provider or method
    #def get_pdf_view(self):
    #    return WagtailTexView(self).serve
    
    creation_date = models.DateField(default=datetime.now)
    
    author = models.CharField(max_length=200)
    
    content = StreamField([
        ("heading", blocks.CharBlock(form_classname="full title")),
        ("text", blocks.RichTextBlock()),
    ], blank=True, use_json_field=True)
    
    content_panels = Page.content_panels + [
        FieldPanel("creation_date"),
        FieldPanel("author"),
        FieldPanel("content"),
    ]
    
    
    # stylesheets = [settings.STATIC_ROOT + "/css/demo_page.css"]
    stylesheets = ["css/demo_page.css"]

    #def get_stylesheets(self, request):
    #    return ["css/demo_page.css"]

from wagtail.core.fields import RichTextField

from wagtail.images.blocks import ImageChooserBlock

    
class HtmlAndPdfPage(PdfViewPageMixin, Page):
    
    
    # Set the browsers attachment handling
    attachment = models.BooleanField(help_text="Download the .pdf file instead of displaying it in the browser", default=False)
    
    ## PDF first
    # ROUTE_CONFIG = [
    #     ("pdf", r'^$'),
    #     ("html", r'^html/$'),
    # ]
    
    # HTML first
    ROUTE_CONFIG = [
        ("html", r'^$'),
        ("pdf", r'^pdf/$'),
    ]
    
    ## You can rename the default preview modes
    # preview_modes = [
    #    ("pdf", "My Pdf Preview"),
    #    ("html", "My HTML Preview"),
    # ]
    
    creation_date = models.DateField(default=datetime.now)
    
    author = models.CharField(max_length=200)
    
    address = models.TextField(blank=True)
    
    content = StreamField([
        ("heading", blocks.CharBlock(form_classname="full title")),
        ("text", blocks.RichTextBlock()),
        ("image", ImageChooserBlock()),
        ("table", TableBlock()),
        
    ], blank=True, use_json_field=True)
    
    
    body = RichTextField(blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel("creation_date"),
        FieldPanel("author"),
        FieldPanel("address"),
        FieldPanel("body"),
        FieldPanel("content"),
    ]
    
    
    pdf_base_template = "pdf_document_base.html"
    
    def get_stylesheets(self, request, mode=None, **kwargs):
        
        # TODO default stylesheets
        # SCSS --> CSS (and remove leading '/')
        return []# return [sass_processor('scss/style_document.pdf.scss')[1:] ]
    
    def get_context(self, request, mode=None, **kwargs):
        context = super().get_context(request, **kwargs)
        
        if mode == 'pdf':
            context["override_base"] = self.pdf_base_template
        
        return context
    

class Homepage(Page):
    pass
