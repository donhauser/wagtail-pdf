
from django import forms


class CheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """
    Widget for rendering multiple options with checkboxes in a PDF document
    
    The django implementation of CheckboxSelectMultiple is broken for PDF rendering, as all inputs get the same name attribute.
    Weasyprint assumes that checkboxes with the same name attribute share the same state (i.e. are checked simultaneously)
    """
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        # copied and modified from django
        
        index = str(index) if subindex is None else "%s_%s" % (index, subindex)
        
        option_attrs = (
            self.build_attrs(self.attrs, attrs) if self.option_inherits_attrs else {}
        )
        
        if selected:
            option_attrs.update(self.checked_attribute)
            
        if "id" in option_attrs:
            option_attrs["id"] = self.id_for_label(option_attrs["id"], index)
            
        return {
            "name": f"{name}-{index}", # append the index to uniquify the name
            "value": value,
            "label": label,
            "selected": selected,
            "index": index,
            "attrs": option_attrs,
            "type": self.input_type,
            "template_name": self.option_template_name,
            "wrap_label": True,
        }
