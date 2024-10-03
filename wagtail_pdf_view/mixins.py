
from wagtail.contrib.routable_page.models import RoutablePageMixin, route


from django.conf import settings

from django.shortcuts import redirect

from django.utils.translation import gettext as _

from django.utils.cache import add_never_cache_headers

from .utils import route_function

from django.utils.cache import patch_cache_control
from django.utils.text import slugify

import urllib.parse

from wagtail.core.models import Page

from .views import get_pdf_view, get_pdf_admin_view, WagtailWeasyView, WagtailWeasyAdminView, AdminViewMixin



DEFAULT_PDF_VIEW = get_pdf_view(getattr(settings, 'WAGTAIL_PDF_VIEW', 'weasyprint'))
DEFAULT_PDF_ADMIN_VIEW = get_pdf_admin_view(getattr(settings, 'WAGTAIL_PDF_ADMIN_VIEW', 'weasyprint'))


WAGTAIL_IN_PREVIEW_PANEL_PDF_DEFAULT_URL = settings.STATIC_URL + "pdf.js/web/viewer.html?file="
WAGTAIL_IN_PREVIEW_PANEL_PDF_URL = getattr(settings, 'WAGTAIL_IN_PREVIEW_PANEL_PDF_URL', WAGTAIL_IN_PREVIEW_PANEL_PDF_DEFAULT_URL)


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
    
    file = f"{original_request.path_info}?{query.urlencode()}"
    url = WAGTAIL_IN_PREVIEW_PANEL_PDF_URL + urllib.parse.quote(file)

    return redirect(url)


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
    to the class and default the classes preview modes with
    >   DEFAULT_PREVIEW_MODES = [("html", "html preview"), ("pdf", "pdf preview")]
    
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
            Process cls.ROUTE_CONFIG on class creation.
            
            Renew cls.DEFAULT_PREVIEW_MODES to match the configuration and
            implement @routed serve_*() methods
        """
        
        # Check if the inheriting class really is a true page.
        # This prevents adding unwanted routes to mixins inheriting from this class
        if issubclass(cls, Page):
            
            cls.DEFAULT_PREVIEW_MODES = []
            
            for key, value, *args in cls.ROUTE_CONFIG:
                
                if value:
                    cls.DEFAULT_PREVIEW_MODES.append((key, cls.get_preview_name(key)))
                    
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
    
    @classmethod
    def get_preview_name(cls, key):
        """
        Suggested name for the preview key
        
        e.g. "pdf" will become "pdf preview"
        """
        
        return _(str(key).upper())
    
    @property
    def preview_modes(self):
        """
        A list of (internal_name, display_name) tuples for the modes in which
        this page can be displayed for preview/moderation purposes.
        By default this is set to a list of all available views (given by ROUTE_CONFIG),
        e.g. [("html", "html preview"), ("pdf", "pdf preview")].
        The defaults are provided by DEFAULT_PREVIEW_MODES of the class
        """
        return type(self).DEFAULT_PREVIEW_MODES

    
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


class PdfModelMixin:
    TEMPLATE_ATTRIBUTE = 'template_name'
    ADMIN_TEMPLATE_ATTRIBUTE = 'admin_template_name'
    
    def get_context(self, *args, **kwargs):
        return {}
    
    # TODO context=... for block
    def get_template(self, request, *args, extension=None, view_provider=None, **kwargs):
        
        if isinstance(view_provider, AdminViewMixin):
            template_attr = self.ADMIN_TEMPLATE_ATTRIBUTE
        else:
            template_attr = self.TEMPLATE_ATTRIBUTE
        
        try:
            return getattr(self, template_attr)
        except AttributeError:
            raise AttributeError("Template attribute not found for model {}. "
                                 "Try to add {}='path/to/your/template_file' to {}".format(self._meta.model_name, template_attr, self._meta.model_name)
                                 )
    
    
    # you can implement Page.attachment to control the Content-Disposition attachment
    ATTACHMENT_VARIABLE = "attachment"
    
    
    def get_pdf_filename(self, request, **kwargs):
        """
        Get the filename for the pdf file
        
        This simply extends the model name with '.pdf'
        """
        
        return self._meta.model_name + '.pdf'


class PdfViewPageMixin(MultipleViewPageMixin):
    """
    A mixin for serving a wagtailpage as '.pdf'
    
    This works by rerouting the pages sub-url (example.com/path/to/page/<sub-url>) with
    wagtails routable pages and rendering it with a custom pdf view.
    
    For this to work you have to ensure that you've installed 'WeasyPrint'.
    Alternatively you can also use 'django-tex' (make sure that you have 'luatex' installed)
    and either implement
    >    pdf_view_class = DjangoTexProvider
    in your page model, or add
    >    WAGTAIL_PDF_VIEW = 'django-tex'
    >    # WAGTAIL_PDF_ADMIN_VIEW = 'django-tex' # if you want to use model admin as well
    to your projects settings.
    
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
    
    # you can implement Page.attachment to control the Content-Disposition attachment
    ATTACHMENT_VARIABLE = "attachment"
    
    pdf_view_class = DEFAULT_PDF_VIEW
    
    # Slugifies the document title if enabled
    pdf_slugify_document_name = True
    
    @property
    def pdf_options(self):
        """
        Possibility to add custom compiler options for weasyprint
        """
        
        return {}
    
    
    @property
    def preview_panel_pdf_options(self):
        """
        Possibility to add custom compiler options for weasyprint
        """
        
        return self.pdf_options
    
    
    def get_pdf_view(self, in_preview_panel=False, pdf_options={}, **kwargs):
        """
        Get the serve method for the classes pdf provider
        """
        
        if in_preview_panel:
            pdf_options = {**self.pdf_view_class.preview_panel_pdf_options, **pdf_options}
        else:
            pdf_options = {**self.pdf_view_class.pdf_options, **pdf_options}
            
        return self.pdf_view_class.as_view(pdf_options=pdf_options, **kwargs)
    
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
        
        if WAGTAIL_IN_PREVIEW_PANEL_PDF_URL and preview_mode=='pdf':
            # check whether the request is inside the preview panel and ensure that redirection is not prohibited (i.e. avoid recursion)
            if original_request and original_request.GET.get('in_preview_panel') and not original_request.GET.get('enforce_preview'):
                # Wagtail >4.0 fix for e.g. firefox (internal pdf viewer prohibits CORS)
                return self.make_in_preview_panel_request(original_request)
        
        return super().make_preview_request(original_request=original_request, preview_mode=preview_mode, extra_request_attrs=extra_request_attrs)
    
    def serve_html(self, request, **kwargs):
        return super().serve(request)
    
    def serve_pdf(self, request, **kwargs):
        """
            Serve the page as pdf using the classes pdf view
        """
        
        view = self.get_pdf_view(pdf_options=self.pdf_options)
        
        response = view(request, object=self, mode="pdf", **kwargs)
        
        # TODO remove
        add_never_cache_headers(response)
            
        return response
    
    def serve_preview_pdf(self, request, **kwargs):
        """
            Serve the page as pdf using the classes pdf view
        """
        
        if request.original_request and not request.original_request.GET.get('in_preview_panel'):
            view = self.get_pdf_view(pdf_options=self.pdf_options)
        else:
            view = self.get_pdf_view(pdf_options=self.preview_panel_pdf_options, in_preview_panel=True)
        
        response = view(request, object=self, mode="pdf", **kwargs)
        
        # TODO remove
        add_never_cache_headers(response)
            
        return response
