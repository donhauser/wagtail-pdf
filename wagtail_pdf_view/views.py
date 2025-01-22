
from django.template.response import TemplateResponse
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View
from django.views.generic.detail import SingleObjectMixin, BaseDetailView
from django.urls import path
from django.contrib.staticfiles.finders import find
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.contrib.auth.mixins import PermissionRequiredMixin

from wagtail.admin.views import generic
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.admin.views.generic.preview import PreviewOnCreate, PreviewOnEdit
from wagtail.admin.ui.components import Component, MediaContainer
from wagtail.admin.ui.side_panels import PreviewSidePanel
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.models import PreviewableMixin

import weasyprint

from django_weasyprint.views import WeasyTemplateResponseMixin, WeasyTemplateResponse


class ConcreteSingleObjectMixin(SingleObjectMixin):
    """
    This mixin simply enables you to pass a concrete instance of a object to a DetailView
    instead of fetching it with a Queryset.
    
    In the regular django dataflow this a DetailView needs to match the correct object
    e.g. given its primary key. When the concrete object is already given (e.g. during the
    serve process of a wagtail page) fetching the same object from the database again is
    non-optimal. With this mixin the object may simply passed to the view call with
    'object=..'
    """
    
    def setup(self, request, *args, object=None, **kwargs):
        self.object = object
        
        return super().setup(request, *args, **kwargs)

    def get_object(self):
        return self.object or super().get_object()
    

class WagtailAdapterMixin(ContextMixin):
    """
    Make a wagtail page accessible as template view.
    
    A wagtail page already provides a template name and context for rendering.
    This mixin makes the page rendering information available for the use with a plain
    django view (TemplateResponse).
    """
    
    def get_template_names(self):
        
        # possibility to override template
        if self.template_name:
            return self.template_name
        
        if hasattr(self.object, "get_template"):
            return self.object.get_template(self.request, view_provider=self)
        
        # fallback
        return super().get_template_names()
    
    def get_context_data(self, **kwargs):
        context = self.object.get_context(self.request, view_provider=self, **kwargs)
        context.update(super().get_context_data(**kwargs))
        return context
    
    
class PDFDetailView(BaseDetailView):
    
    def post_process_responce(self, request, response, **kwargs):
        
        response['Content-Disposition'] = '{}filename="{}"'.format(
            "attachment;" if getattr(self.object, self.object.ATTACHMENT_VARIABLE, False) else '',
            self.object.get_pdf_filename(request, **kwargs)
        )
        
        return response
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        kwargs["object"] = self.object
        
        # Difference to BaseDetailView: Also pass kwargs
        context = self.get_context_data(**kwargs)
        
        response = self.render_to_response(context)
        
        return self.post_process_responce(request, response, **kwargs)
    
    # support for post (e.g. for filling forms)
    def post(self, request, *args, **kwargs):
        return self.get(self, request, *args, **kwargs)


class AdminViewMixin(PermissionCheckedMixin):
    """
    An adminpanel only view
    """
    
    @property
    def permission_policy(self):
        return ModelPermissionPolicy(self.model)
    
    permission_required = 'view'


PDF_VIEWS = {}
PDF_ADMIN_VIEWS = {}


def register_pdf_view(name):
    """
    Register the decorated class as pdf view under the given name
    """
    
    def decorator(cls):
        
        if name in PDF_VIEWS:
            raise ValueError(f"A pdf view with the name '{name}' is already registered")
        
        if not issubclass(cls, PDFDetailView):
            raise ValueError(f"The registered pdf view class '{cls.__name__}' must inherit from PDFDetailView")
        
        PDF_VIEWS[name] = cls
        
        return cls
    return decorator


def register_pdf_admin_view(name):
    """
    Register the decorated class as pdf admin view under the given name
    """
    
    def decorator(cls):
        
        if name in PDF_ADMIN_VIEWS:
            raise ValueError(f"A pdf admin view with the name '{name}' is already registered")
        
        if not issubclass(cls, PDFDetailView):
            raise ValueError(f"The registered pdf admin view class '{cls.__name__}' must inherit from PDFDetailView")
        
        PDF_ADMIN_VIEWS[name] = cls
        
        return cls
    return decorator


def get_pdf_view(name=None):
    """
    Get the pdf view class (e.g. WagtailWeasyView) which is associated with the given name
    
    If no name is given, this method default to either settings.WAGTAIL_PDF_VIEW or 'weasyprint' as fallback.
    """
    
    if name is None:
        name = getattr(settings, 'WAGTAIL_PDF_VIEW', 'weasyprint')
    
    try: 
        return PDF_VIEWS[name]
    except KeyError:
        raise ValueError(f"No such pdf view '{name}', did you forget to use @register_pdf_view('{name}') ?")
    
    
def get_pdf_admin_view(name=None):
    """
    Get the pdf admin view class (e.g. WagtailWeasyAdminView) which is associated with the given name
    
    If no name is given, this method default to either settings.WAGTAIL_PDF_ADMIN_VIEW or 'weasyprint' as fallback.
    """
    
    if name is None:
        name = getattr(settings, 'WAGTAIL_PDF_ADMIN_VIEW', 'weasyprint')
        
    try: 
        return PDF_ADMIN_VIEWS[name]
    except KeyError:
        raise ValueError(f"No such pdf view '{name}', did you forget to use @register_pdf_admin_view('{name}') ?")


try:
    import django_tex
except ImportError:
    django_tex = None


if django_tex:
    
    from django_tex.core import compile_template_to_pdf

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
                return self.object.get_template(self.request, view_provider=self, extension="tex")
            
            # fallback
            return super().get_template_names()


    @register_pdf_view('django-tex')
    class WagtailTexView(WagtailTexTemplateMixin, PDFDetailView):
        pass

    @register_pdf_admin_view('django-tex')
    class WagtailTexAdminView(AdminViewMixin, WagtailTexView):
        pass


"""
The default compiler options for weasyprint can be changed in the settings    
"""
WAGTAIL_DEFAULT_PDF_OPTIONS = getattr(settings, 'WAGTAIL_DEFAULT_PDF_OPTIONS', {
    'pdf_forms': True
})

WAGTAIL_PREVIEW_PDF_OPTIONS = getattr(settings, 'WAGTAIL_PREVIEW_PDF_OPTIONS', None)

WAGTAIL_PREVIEW_PANEL_PDF_OPTIONS = getattr(settings, 'WAGTAIL_PREVIEW_PANEL_PDF_OPTIONS', {
    'pdf_forms': False,
    'dpi': 50,
    'jpeg_quality': 30
})


class WagtailWeasyTemplateResponse(WeasyTemplateResponse):    
    
    def get_base_url(self):
        """
        Determine base URL to fetch CSS files from `WEASYPRINT_BASEURL` or
        fall back to using the root path of the URL used in the request.
        
        In contrast to the implementation in django_weasyprint this method contains a
        working fallback for the dummy requests used by wagtails page preview mode.
        """
        
        if hasattr(settings, 'WEASYPRINT_BASEURL'):
            return settings.WEASYPRINT_BASEURL
        
        # Check if this is a wagtail dummy request and use the uri of the original request instead
        if getattr(self._request, "is_dummy", False) and hasattr(self._request, "original_request"):
            return self._request.original_request.build_absolute_uri('/')
            
        return self._request.build_absolute_uri('/')


    def get_css(self, base_url, url_fetcher, font_config, *args, **kwargs):
        """
        Get the css for weasyprint
        
        All paths are collected from _stylesheets and are tried to be located
        with djangos static loaders.
        
        This method is an override of django_weasyprint.views.WeasyTemplateResponse.get_css(),
        which also supports static file paths. If the relative import fails, django automatically tries searches
        for the correct static file by using django.contrib.staticfiles.finders.find(value) as fallback.
        """
        
        tmp = []
        for value in self._stylesheets:
            try:
                # Try to import relative to BASE_DIR
                css = weasyprint.CSS(
                    value,
                    base_url=base_url,
                    url_fetcher=url_fetcher,
                    font_config=font_config,
                )
            except FileNotFoundError as e:
                try:
                    # Try to locate the static file
                    path = find(value)
                except SuspiciousFileOperation:
                    # raise original FileNotFound, raising SuspiciousFileOperation would be misleading
                    raise e
                
                if path:
                    css = weasyprint.CSS(
                        path,
                        base_url=base_url,
                        url_fetcher=url_fetcher,
                        font_config=font_config,
                    )
                else:
                    raise e
                
            if css:
                tmp.append(css)
            
        return tmp


class WagtailWeasyTemplateMixin(WagtailAdapterMixin, ConcreteSingleObjectMixin, WeasyTemplateResponseMixin):
    response_class = WagtailWeasyTemplateResponse
    
    pdf_options = None
    preview_pdf_options = None
    preview_panel_pdf_options = None

    preview = False
    in_preview_panel = False


    def get_pdf_options(self):
        """
        Specifies pdf options for weasyprint

        The options are choosen based on whether the view is a (in panel) preview.
        In-panel options are preferred to general preview options, normal options are the least preferred.
        """

        if self.in_preview_panel:
            if self.preview_panel_pdf_options is not None:
                return self.preview_panel_pdf_options

            if WAGTAIL_PREVIEW_PANEL_PDF_OPTIONS is not None:
                return WAGTAIL_PREVIEW_PANEL_PDF_OPTIONS

        if self.preview:
            if self.preview_pdf_options is not None:
                return self.preview_pdf_options

            if WAGTAIL_PREVIEW_PDF_OPTIONS is not None:
                return WAGTAIL_PREVIEW_PDF_OPTIONS

        if self.pdf_options is not None:
            return self.pdf_options

        return WAGTAIL_DEFAULT_PDF_OPTIONS or {}

    
    def get_pdf_stylesheets(self):
        # try to call get_stylesheets, otherwise get stylesheet attribute
        try:
            stylesheets = self.object.get_stylesheets(self.request)
        except AttributeError:
            stylesheets = getattr(self.object, "stylesheets", [])
        
        return stylesheets


@register_pdf_view('weasyprint')
class WagtailWeasyView(WagtailWeasyTemplateMixin, PDFDetailView):
    pass
    

@register_pdf_admin_view('weasyprint')
class WagtailWeasyAdminView(AdminViewMixin, WagtailWeasyView):
    pass


class CreateView(generic.CreateEditViewOptionalFeaturesMixin, generic.CreateView):
    """
    Create view for previewable models
    """
    view_name = "create"

    def get_side_panels(self):
        side_panels = []

        if self.preview_enabled and self.form.instance.is_previewable():
            side_panels.append(
                PreviewSidePanel(
                    self.form.instance, self.request, preview_url=self.get_preview_url()
                )
            )
        return MediaContainer(side_panels)


class EditView(generic.CreateEditViewOptionalFeaturesMixin, generic.EditView):
    """
    Edit view for previewable models
    """
    view_name = "edit"

    def get_side_panels(self):
        side_panels = []

        if self.preview_enabled and self.object.is_previewable():
            side_panels.append(
                PreviewSidePanel(
                    self.object, self.request, preview_url=self.get_preview_url()
                )
            )
        return MediaContainer(side_panels)


class CopyView(generic.CopyViewMixin, CreateView):
    pass


class PreviewOnCreateView(PreviewOnCreate):
    pass


class PreviewOnEditView(PreviewOnEdit):
    pass


class PreviewableViewSetMixin:
    """
    Mixin for adding the preview functionality to viewsets
    """

    add_view_class = CreateView
    edit_view_class = EditView
    copy_view_class = CopyView

    #: The view class to use for previewing on the create view
    preview_on_add_view_class = PreviewOnCreateView

    #: The view class to use for previewing on the edit view
    preview_on_edit_view_class = PreviewOnEditView

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.preview_enabled = issubclass(self.model, PreviewableMixin)

    def get_urlpatterns(self):
        urlpatterns = []

        if self.preview_enabled:
            urlpatterns += [
                path("preview/", self.preview_on_add_view, name="preview_on_add"),
                path(
                    "preview/<str:pk>/",
                    self.preview_on_edit_view,
                    name="preview_on_edit",
                ),
            ]

        return super().get_urlpatterns() + urlpatterns

    @property
    def preview_on_add_view(self):
        return self.construct_view(
            self.preview_on_add_view_class,
            form_class=self.get_form_class(),
        )

    @property
    def preview_on_edit_view(self):
        return self.construct_view(
            self.preview_on_edit_view_class,
            form_class=self.get_form_class(for_update=True),
        )

    def get_add_view_kwargs(self, **kwargs):
        return super().get_add_view_kwargs(
            preview_url_name=self.get_url_name("preview_on_add"),
            **kwargs,
        )

    def get_edit_view_kwargs(self, **kwargs):
        return super().get_edit_view_kwargs(
            preview_url_name=self.get_url_name("preview_on_edit"),
            **kwargs,
        )
