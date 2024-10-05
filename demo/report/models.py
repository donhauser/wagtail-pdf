from datetime import datetime

from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock

from wagtail.admin.panels import FieldPanel, FieldRowPanel

from wagtail_pdf_view.mixins import PdfViewPageMixin, PdfModelMixin

from wagtail.images.blocks import ImageChooserBlock

class ColumnBlock(blocks.StructBlock):
    
    heading = blocks.CharBlock(form_classname="full title")
    sub_heading = blocks.CharBlock(required=False)
    text = blocks.RichTextBlock()
    
    class Meta:
        template = 'report/blocks/columns.html'

class CompetencesBlockEntry(blocks.StructBlock):
    heading = blocks.CharBlock()
    text = blocks.CharBlock()
    kind = blocks.ChoiceBlock(
            choices=[
                ('table-content', 'Table content'),
                ('heading', 'Heading titles'),
                ('multi-columns', 'Multi-column text'),
                ('internal-links', 'Internal links'),
                ('style', 'Page style'),
            ])

class CompetencesBlock(blocks.StructBlock):
    
    heading = blocks.CharBlock(form_classname="full title")
    sub_heading = blocks.CharBlock(required=False)
    entries = blocks.ListBlock(CompetencesBlockEntry(label="Entry"))
    
    class Meta:
        template = 'report/blocks/competences.html'
        

class OffersBlockEntry(blocks.StructBlock):
    heading = blocks.CharBlock()
    text = blocks.CharBlock()
    price = blocks.IntegerBlock()
    items = blocks.ListBlock(blocks.CharBlock())

        
class OffersBlock(blocks.StructBlock):
    
    heading = blocks.CharBlock(form_classname="full title")
    sub_heading = blocks.CharBlock(required=False)
    entries = blocks.ListBlock(OffersBlockEntry(label="Entry"))
    
    class Meta:
        template = 'report/blocks/offers.html'


class ReportPage(PdfViewPageMixin, Page):
    ## Set the browsers attachment handling
    # attachment = True
    
    ## render with LaTeX instead
    # pdf_view_class = WagtailTexView
    
    ## Add a custom view provider or method
    #def get_pdf_view(self):
    #    return WagtailTexView(self).serve
    
    #creation_date = models.DateField(default=datetime.now)
    
    #author = models.CharField(max_length=200)
    
    
    #stylesheets = ["report.css"]
    
    address_left = models.TextField(max_length=200)
    address_right = models.TextField(max_length=200)
    
    content = StreamField([
        ("chapter", blocks.CharBlock(form_classname="full title")),
        ("columns", ColumnBlock()),
        ("competences", CompetencesBlock()),
        ("offers", OffersBlock()),
    ], blank=True, use_json_field=True)
    
    
    #body = RichTextField(blank=True)
    
    content_panels = Page.content_panels + [
        FieldRowPanel([
            FieldPanel("address_left"),
            FieldPanel("address_right"),
        ]),
        FieldPanel("content"),
    ]
    
    
