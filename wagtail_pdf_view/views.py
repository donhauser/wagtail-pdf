

from django.template.response import TemplateResponse
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View
from django.views.generic.detail import SingleObjectMixin, BaseDetailView

from django.contrib.staticfiles.finders import find

from django.conf import settings

from django.core.exceptions import SuspiciousFileOperation

from django.contrib.auth.mixins import PermissionRequiredMixin

from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.core.permission_policies import ModelPermissionPolicy



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
        
        
        def get_template_names(self):
            
            # possibility to override template
            if self.template_name:
                return self.template_name
            
            if hasattr(self.object, "get_template"):
                return self.object.get_template(self.request, view_provider=self, extension="tex")
            
            # fallback
            return super().get_template_names()


    class WagtailTexView(WagtailTexTemplateMixin, PDFDetailView):
        pass

    class WagtailTexAdminView(AdminViewMixin, WagtailTexView):
        pass


try:
    import django_weasyprint
except ImportError:
    django_weasyprint = None


if django_weasyprint:

    import weasyprint
    from django_weasyprint.views import WeasyTemplateResponseMixin, WeasyTemplateResponse

    class CustomWeasyTemplateResponse(WeasyTemplateResponse):
        
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


        def get_css(self, base_url, url_fetcher):
            """
            Get the css for weasyprint
            
            All paths are collected from _stylesheets and are tried to be located
            with djangos static loaders.
            """
            
            tmp = []
            for value in self._stylesheets:
                try:
                    # Try to import relative to BASE_DIR
                    css = weasyprint.CSS(
                        value,
                        base_url=base_url,
                        url_fetcher=url_fetcher,
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
                        )
                    else:
                        raise e
                    
                if css:
                    tmp.append(css)
                
            return tmp


    class WagtailWeasyTemplateMixin(WagtailAdapterMixin, ConcreteSingleObjectMixin, WeasyTemplateResponseMixin):
        response_class = CustomWeasyTemplateResponse
        
        def get_pdf_stylesheets(self):
            # try to call get_stylesheets, otherwise get stylesheet attribute
            try:
                stylesheets = self.object.get_stylesheets(self.request)
            except AttributeError:
                stylesheets = getattr(self.object, "stylesheets", [])
            
            return stylesheets


    class WagtailWeasyView(WagtailWeasyTemplateMixin, PDFDetailView):
        pass
        
 
    class WagtailWeasyAdminView(AdminViewMixin, WagtailWeasyView):
        pass

