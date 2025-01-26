
from django.template.response import TemplateResponse
from django.views.generic.base import TemplateResponseMixin

from django_tex.core import compile_template_to_pdf

from wagtail_pdf_view.views import WagtailAdapterMixin, ConcreteSingleObjectMixin, PDFDetailView


class TexTemplateResponse(TemplateResponse):

    @property
    def rendered_content(self):
        """
        Returns rendered PDF pages.
        """

        context = self.resolve_context(self.context_data)

        return compile_template_to_pdf(self.template_name, context)


class WagtailTexTemplateMixin(WagtailAdapterMixin, ConcreteSingleObjectMixin, TemplateResponseMixin):
    """
    Provide the latex compiler (from django-tex) as view
    """
    content_type='application/pdf'
    response_class = TexTemplateResponse

    # currently unsupported, as django-tex uses settings.LATEX_INTERPRETER_OPTIONS
    pdf_options = None
    preview_pdf_options = None
    preview_panel_pdf_options = None

    preview = False
    in_preview_panel = False

    def get_template_names(self):

        # possibility to override template
        if self.template_name:
            return self.template_name

        if hasattr(self.object, "get_template"):
            return self.object.get_template(self.request, extension="tex")

        # fallback
        return super().get_template_names()


class WagtailTexView(WagtailTexTemplateMixin, PDFDetailView):
    pass


class WagtailTexAdminView(WagtailTexView):
    permission_required = 'view'
