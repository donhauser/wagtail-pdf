
from django.template.response import TemplateResponse
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View
from django.views.generic.detail import SingleObjectMixin, BaseDetailView
from django.urls import path,reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext as _
from django.contrib.staticfiles.finders import find
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.contrib.admin.utils import quote
from django.contrib.auth.mixins import PermissionRequiredMixin

from wagtail.admin.views import generic
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.admin.views.generic.preview import PreviewOnCreate, PreviewOnEdit
from wagtail.admin.widgets.button import ListingButton
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
    Make a wagtail page or model accessible as template view.
    
    A wagtail page already provides a template name and context for rendering.
    This mixin makes the page rendering information available for the use with a plain
    django view (TemplateResponse).
    """
    
    def get_template_names(self):
        
        # possibility to override template
        if self.template_name:
            return self.template_name
        
        if hasattr(self.object, "get_template"):
            return self.object.get_template(self.request)
        
        # fallback
        return super().get_template_names()
    
    def get_context_data(self, **kwargs):
        context = self.object.get_context(self.request, **kwargs)
        context.update(super().get_context_data(**kwargs))
        return context
    
    
class PDFDetailView(BaseDetailView):

    #: pdf content-disposition attachment state
    attachment = None

    def get_attachment(self):
        """
        Spefifies the content-disposition attachment state for the pdf response
        """

        if self.attachment is None:
            return getattr(self.object, self.object.ATTACHMENT_VARIABLE, False)

        return self.attachment
    
    def post_process_responce(self, request, response, **kwargs):
        """
        Perform additional operations on the pdf response
        """

        response['Content-Disposition'] = '{}filename="{}"'.format(
            "attachment;" if self.get_attachment() else '',
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


class WagtailWeasyView(WagtailWeasyTemplateMixin, PDFDetailView):
    pass
    

class WagtailWeasyAdminView(WagtailWeasyView):
    permission_required = 'view'


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


class LiveIndexViewMixin:
    live_app_name = 'wagtail_pdf_view'

    def get_live_url(self, instance):
        try:
            name = f"{self.model._meta.app_label}.{self.model._meta.object_name}"

            if self.live_app_name:
                name = self.live_app_name+":"+name

            return reverse(name, args=(quote(instance.pk),))
        except NoReverseMatch:
            return ''

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)

        if live_url := self.get_live_url(instance):
            b = ListingButton(
                _("View live"),
                url=live_url,
                icon_name="doc-empty",
                attrs={
                    "aria-label": _("Open PDF '%(title)s'") % {"title": str(instance)}
                },
                priority=15,
            )
            buttons.append(b)

        return buttons


class LiveIndexView(LiveIndexViewMixin, generic.IndexView):
    pass


class PdfViewSetMixin(PreviewableViewSetMixin):
    index_view_class = LiveIndexView


class PdfAdminIndexView(LiveIndexViewMixin, generic.IndexView):
    """
    IndexView for ViewSets with an 'Open PDF' button
    """

    pdf_url_name = None

    def get_pdf_url(self, instance):
        if not self.pdf_url_name:
            raise ImproperlyConfigured( # TODO proper warning
                "Subclasses of PdfAdminIndexView must provide an "
                "pdf_url_name attribute or a get_pdf_url method"
            )
        return reverse(self.pdf_url_name, args=(quote(instance.pk),))

    def get_list_buttons(self, instance):
        buttons = super().get_list_buttons(instance)

        if pdf_url := self.get_pdf_url(instance):
            b = ListingButton(
                _("View pdf"),
                url=pdf_url,
                icon_name="doc-full",
                attrs={
                    "aria-label": _("Open PDF '%(title)s'") % {"title": str(instance)}
                },
                priority=10,
            )

            buttons.append(b)

        return buttons


class PdfAdminViewSetMixin(PdfViewSetMixin):
    """
    Makes a model accessible as PDF for admin panel users
    """

    index_view_class = PdfAdminIndexView

    pdf_view_class = WagtailWeasyView

    pdf_options = None
    pdf_attachment = None
    pdf_template_name = None

    def get_urlpatterns(self):
        urlpatterns = [
            path("pdf/<str:pk>/", self.pdf_view, name="pdf"),
        ]

        return super().get_urlpatterns() + urlpatterns

    def get_index_view_kwargs(self, **kwargs):
        url_map = {
            "pdf_url_name": self.get_url_name("pdf"),
        }

        return super().get_index_view_kwargs(**url_map, **kwargs)

    def get_pdf_view_kwargs(self, **kwargs):

        options = {}

        if self.pdf_options is not None:
            options['pdf_options'] = self.pdf_options

        if self.pdf_attachment is not None:
            options['attachment'] = self.pdf_attachment

        if self.pdf_template_name is not None:
            options['template_name'] = self.pdf_template_name

        return {
            **options,
            **kwargs
        }

    @property
    def pdf_view(self):
        """
        Serve an admin pdf view for a given instance

        The kwargs may be used to pass template_name="path/to/custom/template" or
        to change the view permissions with permission_required="some permission".
        Passing permission_required=None disables the permission system.
        (Access to /admin is still needed)
        """

        return self.construct_view(self.pdf_view_class, **self.get_pdf_view_kwargs())
