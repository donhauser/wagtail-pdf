
from wagtail.contrib.routable_page.models import RoutablePageMixin, route

from django.conf import settings
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.utils.cache import add_never_cache_headers
from django.utils.cache import patch_cache_control
from django.utils.text import slugify
from django.urls.exceptions import NoReverseMatch

import logging

from wagtail.models import Page, PreviewableMixin

from .utils import route_function, get_pdf_viewer_url

from .views import WagtailWeasyView

logger = logging.getLogger(__name__)


def redirect_request_to_pdf_viewer(original_request):
    """
    Redirect the original request to a custom pdf viewer frontend
    
    This is used to hook in pdf.js from server-side in the preview to enable propper iframe interaction.
    Using the browsers pdf viewer within iframes instead may break the preview (e.g. firefox wagtail >4.0),
    as the pdf viewer is hosted locally and thus prevents accessing scroll properites (CORS prohibited).
    """
    
    query = original_request.GET.copy()
    # this prevents a preview redirection loop
    query['enforce_preview'] = "true"
    
    path = f"{original_request.path_info}?{query.urlencode()}"
    url = get_pdf_viewer_url(path)

    return redirect(url)


class MultiplePreviewMixin:
    """
    Forward mode specific preview handling by serve_preview_<mode>() methods
    """

    def get_preview_modes(self):
        """
        List of modes in which this page can be displayed for preview/moderation purposes.

        The modes are a list of (internal_name, display_name) tuples.
        """

        raise NotImplementedError("The model must override either get_preview_modes() or preview_modes")

    @property
    def preview_modes(self):
        """
        List of modes in which this page can be displayed for preview/moderation purposes.

        The modes are a list of (internal_name, display_name) tuples.
        By default this is set to a list of all available views (given by ROUTE_CONFIG),
        e.g. [("html", "HTML"), ("pdf", "PDF")].
        """
        return self.get_preview_modes()


    # kwargs not supported (by wagtail) yet
    def serve_preview(self, request, mode_name):
        """
        Handle serve_preview like wagtail (version 2.12)
        but hook in mode specific serve_*()/serve_preview_*() methods.
        e.g. call serve_preview_pdf() or serve_pdf() for mode="pdf"
        """

        mode_names = [mode[0] for mode in self.preview_modes]

        request.is_preview = True

        # try to serve preview or serve regular if the given mode is available as preview
        if mode_name in mode_names:
            try:
                serve = getattr(self, "serve_preview_" + mode_name)
            except AttributeError:
                serve = getattr(self, "serve_" + mode_name)

            response = serve(request)

            patch_cache_control(response, private=True)

            return response

        return super().serve_preview(request, mode_name)


class MultipleViewPageMixin(RoutablePageMixin):
    """
    This mixin enables multiple different views on a wagtail page.
    
    The goals of this extension are similar to the @route decorator from wagtails RoutablePage.
    In contrast to the native RoutablePageMixin this mixin is build with the goal to provided
    a more flexible/extensible inheritance structure for views on wagtail pages.
    
    With this mixin, a page model (e.g. class PdfPage(Page)) can define an class attribute
    
    ROUTE_CONFIG = [
        ("html", r'^$'),     # default route
        ("pdf", r'^pdf/$'),  # /pdf/ route
    ]
    
    which adds the methods
    >   @route(r'^$')
    >   def serve_html(..)
    and 
    >   @route(r'^pdf/$')
    >   def serve_pdf(..)
    to the class.
    
    To make the difference to a naive implementation with @route is that an inheriting class
    is still able to change/extend the path configuration to its needs by reimplementing
    ROUTE_CONFIG.
    
    E.g. Another page model (e.g. class CustomPdfPage(PdfPage)) can default the "pdf" view,
    which would not be easily possible by using @route("^pdf/") in PdfPage
    
    ROUTE_CONFIG = [
        ("pdf", r'^$'),    # new default route
        ("html", None),    # ignored route
    ]
    """
    
    def __init_subclass__(cls):
        """
            Process cls.ROUTE_CONFIG on class creation
            
            The route configuration is used to implement @routed serve_*() methods.
        """
        
        # Check if the inheriting class really is a true page.
        # This prevents adding unwanted routes to mixins inheriting from this class
        if issubclass(cls, Page):
            
            for key, value, *args in cls.ROUTE_CONFIG:
                
                if value:
                    serve_method = "serve_{}".format(key)
                    
                    # Use a propper name for @route, otherwise the name will be 'inner' due to function wrapping
                    if not args:
                        args = [key]
                    
                    # add the @route decorator to the serve methods
                    fn = getattr(cls, serve_method)
                    setattr(cls, serve_method, route_function(fn, value, *args))
    
    
    def __init__(self, *args, **kwargs):
        """
        Assign a custom url attribute for each view during initialization
        
        For example the url for the 'pdf'-view of the Page will be `Page.url_pdf`
        """
        
        super().__init__(*args, **kwargs)
        
        for key, value, *route_args in self.ROUTE_CONFIG:
            
            if not route_args:
                route_args = [key]
            
            # Assign the url attribute to the matching reverse if the attribute is not set already
            if value and not hasattr(self, "url_"+key):
                
                name = route_args[0]
                
                url = self.url
                
                if url is not None:
                    if not url.endswith('/'):
                        url += '/'
                    
                    setattr(self, "url_"+key, url+self.reverse_subpage(name))


class BasePdfMixin:
    """
    A mixin for serving a wagtail objects as '.pdf'
    """

    # you can implement Page.attachment to control the Content-Disposition attachment
    ATTACHMENT_VARIABLE = "attachment"
    
    pdf_view_class = WagtailWeasyView
    
    # Slugifies the document title if enabled
    pdf_slugify_document_name = True

    def get_pdf_view_kwargs(self):
        """
        Specifies the keyword arguments for the pdf view class construction
        """

        kwargs = {}

        if hasattr(self, 'pdf_options'):
            kwargs['pdf_options'] = self.pdf_options

        return kwargs

    @property
    def pdf_view(self):
        """
        Serve a pdf view for a given instance
        """

        return self.pdf_view_class.as_view(**self.get_pdf_view_kwargs())

    def serve_pdf(self, request, **kwargs):
        """
            Serve the page as pdf using the classes pdf view
        """

        response = self.pdf_view(request, object=self, mode="pdf", **kwargs)

        # TODO remove
        add_never_cache_headers(response)

        return response


class BasePreviewablePdfMixin(BasePdfMixin, MultiplePreviewMixin):
    """
    A mixin for serving the preview of a wagtail objects as '.pdf'
    """

    preview_pdf_view_class = None

    def get_preview_modes(self):
        """
        List of modes in which this page can be displayed for preview/moderation purposes.

        The modes are a list of (internal_name, display_name) tuples.
        """

        return [("pdf", "PDF")]

    def get_preview_pdf_view_kwargs(self, in_preview_panel=False):
        """
        Specifies the keyword arguments for the pdf view class construction in preview mode
        """

        kwargs = self.get_pdf_view_kwargs()

        kwargs['preview'] = True
        kwargs['in_preview_panel'] = in_preview_panel

        if in_preview_panel and hasattr(self, 'preview_panel_pdf_options'):
            kwargs['preview_panel_pdf_options'] = self.preview_panel_pdf_options
        elif hasattr(self, 'preview_pdf_options'):
            kwargs['preview_pdf_options'] = self.preview_pdf_options
    
        return kwargs

    @property
    def preview_pdf_view(self):
        view_class = self.preview_pdf_view_class or self.pdf_view_class
        return view_class.as_view(**self.get_preview_pdf_view_kwargs(False))

    @property
    def preview_panel_pdf_view(self):
        view_class = self.preview_pdf_view_class or self.pdf_view_class
        return view_class.as_view(**self.get_preview_pdf_view_kwargs(True))
    
    def make_in_preview_panel_request(self, original_request):
        """
        Handle in preview panel requests by redirecting to a pdf viewer like "pdf.js"
        """
        
        return redirect_request_to_pdf_viewer(original_request)
    
    def make_preview_request(self, original_request=None, preview_mode=None, extra_request_attrs=None):
        """
        Make a preview request with the orignial request (admin view) still being available
        
        This is essentially a fix for weasyprint in the wagtail admin preview.
        The original request is still accessible as request.orginal_request e.g. to figure out
        the server port (which is not possible otherwise, as wagtail is creating a new 'fake'
        request with port 80) or to check whether "in_preview_panel" is set
        """
        
        if not extra_request_attrs:
            extra_request_attrs = {}
            
        extra_request_attrs["original_request"] = original_request
        
        # Hook in the specified WAGTAIL_PDF_VIEWER in 'pdf' mode, setting WAGTAIL_PDF_VIEWER = {} will disable the viewer
        if preview_mode=='pdf' and getattr(settings, 'WAGTAIL_PDF_VIEWER', None) != {}:
            # check whether the request is inside the preview panel and ensure that redirection is not prohibited (i.e. avoid recursion)
            if original_request and original_request.GET.get('in_preview_panel') and not original_request.GET.get('enforce_preview'):
                
                try:
                    # Wagtail >4.0 fix for e.g. firefox (internal pdf viewer prohibits CORS)
                    return self.make_in_preview_panel_request(original_request)
                except NoReverseMatch as e:
                    logger.warn(f"Could not create an 'in preview panel' request. Falling back to regular PDF serving.")
        
        return super().make_preview_request(original_request=original_request, preview_mode=preview_mode, extra_request_attrs=extra_request_attrs)

    
    def serve_preview_pdf(self, request, **kwargs):
        """
        Serve the page preview as pdf using the classes pdf view

        If the preview is opened outside of the preview panel, the usual pdf view is used instead.
        """

        if request.original_request and not request.original_request.GET.get('in_preview_panel'):
            view = self.preview_pdf_view
        else:
            view = self.preview_panel_pdf_view
        
        response = view(request, object=self, mode="pdf", **kwargs)
        
        # TODO remove
        add_never_cache_headers(response)
            
        return response


class PdfModelMixin(BasePreviewablePdfMixin, PreviewableMixin):

    def get_context(self, request, **kwargs):
        return {}

    def get_template(self, request, extension=None):
        return self.template_name


    # you can implement Page.attachment to control the Content-Disposition attachment
    ATTACHMENT_VARIABLE = "attachment"


    def get_pdf_filename(self, request, **kwargs):
        """
        Get the filename for the pdf file

        This simply extends the model name with '.pdf'
        """

        return self._meta.model_name + '.pdf'


class PdfViewPageMixin(BasePreviewablePdfMixin, MultipleViewPageMixin):
    """
    A mixin for serving a wagtailpage as '.pdf'

    This works by rerouting the pages sub-url (example.com/path/to/page/<sub-url>) with
    wagtails routable pages and rendering it with a custom pdf view.

    By default only the pdf view is available, i.e. you may only view this page as pdf.
    This may be changed by reimplementing ROUTE_CONFIG, e.g.

    ROUTE_CONFIG = [
        ("pdf", r'^pdf/$'), # pdf view
        ("html", r'^$'),    # default view
    ]

    will serve the page as usual and /pdf/ will serve the rendered '.pdf' document.

    You should avoid to override the serve() method, as this likely will break the routing.
    """

    # by default only the pdf view is available, i.e. you may only view this page as pdf
    ROUTE_CONFIG = [
        ("pdf", r'^$'),
        ("html", None),
    ]


    def get_pdf_filename(self, request, **kwargs):
        """
        Get the filename for the pdf file

        This simply extends the page title with '.pdf'
        """

        if self.pdf_slugify_document_name:
            title = slugify(self.title)
        else:
            title = self.title

        return title + '.pdf'


    def get_template(self, request, extension=None, **kwargs):
        """
        Get the template name for this page

        extension can be used to replace the file extension '.html' with e.g. '.tex'
        """

        template_name = super().get_template(request)

        if extension:
            template_name = template_name.replace(".html", "."+extension)

        return template_name

    def get_preview_mode_name(self, key):
        """
        Suggested name for the preview key

        e.g. "pdf" will become "pdf preview"
        """

        return _(str(key).upper())

    def get_preview_modes(self):
        """
        List of modes in which this page can be displayed for preview/moderation purposes.

        The modes are a list of (internal_name, display_name) tuples.
        By default this is set to a list of all available views (given by ROUTE_CONFIG),
        e.g. [("html", "HTML"), ("pdf", "PDF")].
        The mode names are assigned by get_preview_mode_name
        """

        return [(mode, self.get_preview_mode_name(mode)) for mode, value, *_ in type(self).ROUTE_CONFIG if value]

    def serve_html(self, request, **kwargs):
        return super().serve(request)
