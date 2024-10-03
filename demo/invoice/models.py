from datetime import datetime

from django.db import models

from wagtail.core.models import Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core import blocks
from wagtail.contrib.table_block.blocks import TableBlock

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

from wagtail.admin.edit_handlers import FieldPanel, InlinePanel#, MultiFieldPanel, FieldRowPanel

from wagtail_pdf_view.mixins import PdfViewPageMixin, PdfModelMixin


import uuid

class Invoice(PdfModelMixin, ClusterableModel):
    #attachment = True
    
    #pdf_options = {'dpi': 200}
    
    # uuid is used for URL anonymization 
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    number = models.PositiveIntegerField(default=0, unique=True, editable=False)
    
    creation_date = models.DateField(default=datetime.now)
    
    address = models.TextField(max_length=500)
    
    due_by_date = models.DateField()
    account_number = models.CharField(max_length=24)
    
    panels = [
        FieldPanel("creation_date"),
        FieldPanel("address"),
        FieldPanel("due_by_date"),
        FieldPanel("account_number"),
        InlinePanel("items", heading="Items"),
    ]
    
    template_name = "invoice/invoice.html"
    
    stylesheets = ["invoice.css"]
    
    @property
    def total_price(self):
        
        return sum(x.total_price for x in self.items.all())
    
    
    def save(self, *args, **kwargs):
        # Auto-Incrementing number field
        # Source: https://stackoverflow.com/questions/41228034/django-non-primary-key-autofield
        
        # This means that the model isn't saved to the database yet
        if self._state.adding:
            # Get the maximum value from the database
            last_id = type(self).objects.all().aggregate(largest=models.Max('number'))['largest']

            # aggregate can return None! Check it first.
            # If it isn't none, just use the last ID specified (which should be the greatest) and add one to it
            if last_id is not None:
                self.number = last_id + 1

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Invoice #{self.number}"

class InvoiceItem(models.Model):
    
    name = models.TextField(max_length=500)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    quantity = models.IntegerField()
    
    invoice = ParentalKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
    )
    
    @property
    def total_price(self):
        
        return self.price*self.quantity
    
    
