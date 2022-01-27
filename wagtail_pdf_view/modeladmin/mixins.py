
from django.conf import settings
from django.urls import re_path

from wagtail.core import hooks

from wagtail.contrib.modeladmin.helpers import ButtonHelper, PermissionHelper, AdminURLHelper
from django.urls.exceptions import NoReverseMatch


from ..mixins import DEFAULT_PDF_VIEW_PROVIDER, DEFAULT_PDF_ADMIN_VIEW_PROVIDER


class ExtendableButtonHelperMixin:
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        if self.custom_object_buttons is None:
            self.custom_object_buttons = self.get_custom_object_buttons()
    
    def extra_button(self, url=None, label='', title=None, classnames_add=None, classnames_exclude=None):
        if classnames_add is None:
            classnames_add = []
        if classnames_exclude is None:
            classnames_exclude = []
        classnames = classnames_add
        cn = self.finalise_classname(classnames, classnames_exclude)
        
        if not title:
            title = label
        
        return {
            'url': url,
            'label': label,
            'classname': cn,
            'title': title,
        }

    def get_buttons_for_obj(self, obj, exclude=None, classnames_add=None,
                            classnames_exclude=None):
        
        btns = super().get_buttons_for_obj(obj, exclude=exclude, classnames_add=classnames_add,
                            classnames_exclude=classnames_exclude)
        
        if exclude is None:
            exclude = []
        if classnames_add is None:
            classnames_add = []
        if classnames_exclude is None:
            classnames_exclude = []
        
        ph = self.permission_helper
        usr = self.request.user
        pk = getattr(obj, self.opts.pk.attname)
        
        for action, kw in self.custom_object_buttons:
            
            if action in exclude or not ph.user_can_perform_action(usr, obj, action):
                continue
            
            # If the reverse URL is missing simply skip the button
            try:
                # unite if necessary
                if 'classnames_add' in kw:
                    kw['classnames_add'] += classnames_add
                else:
                    kw['classnames_add'] = classnames_add
                    
                if 'classnames_exclude' in kw:
                    kw['classnames_exclude'] += classnames_exclude
                else:
                    kw['classnames_exclude'] = classnames_exclude
                
                btns.append(self.extra_button(self.url_helper.get_action_url(action, pk), **kw))
            except NoReverseMatch as e:
                if not self.is_optional(action):
                    raise e
            
        return btns

    
    # custom button definitions
    # [
    #   (action, attributes),
    # ]
    custom_object_buttons = None
    
    def get_custom_object_buttons(self):
        return []
    
    def is_optional(self, action):
        return False
    


from django.utils.translation import gettext as _
    
class PdfViewButtonHelper(ExtendableButtonHelperMixin, ButtonHelper):
    
    # custom definitions
    # (action, attributes)
    
    custom_object_buttons = [
        ("pdf", {"label":_("View pdf")}),
        ("live", {"label":_("View live")}),
    ]
    
    def is_optional(self, action):
        # This class is shared between ModelAdminPdfViewMixin and ModelAdminPdfAdminViewMixin.
        # Both classes have different actions and do not define a reversible URL on the action of each other.
        # Buttons with actions listed below will simply be skipped, if the URL-reversing failed
        
        return action in ["pdf", "live"]


class CustomActionPermissionHelperMixin:
    def user_can_perform_action(self, user, obj, action):
        """
        Return a boolean to indicate whether `user` is permitted to perform a <action> on
        a specific `self.model` instance.
        """
        perm_codename = self.get_perm_codename(action)
        return self.user_has_specific_permission(user, perm_codename)
    
    
class CustomActionPermissionHelper(CustomActionPermissionHelperMixin, PermissionHelper):
    pass


class ModelAdminPdfViewMixin:
    
    button_helper_class = PdfViewButtonHelper
    permission_helper_class = CustomActionPermissionHelper
    
    pdf_view_class = getattr(settings, "DEFAULT_PDF_VIEW_PROVIDER", DEFAULT_PDF_VIEW_PROVIDER)


    def register_with_wagtail(self):
        """
        Hook the models live site pdf-views into wagtail
        """
        
        super().register_with_wagtail()
        
        @hooks.register('register_pdf_site_urls')
        def register_site_urls():
            return self.get_site_urls_for_registration()
    
    # ability to register multiple templates for live
    custom_site_pdf_views = [
        ("live", {}),
        #("live", {'template_name':'path/to/template.html'}),
    ]
    
    
    def pdf_view(self, request, instance_pk, **kwargs):
        """
        Serve an admin pdf view for a given instance
        
        The kwargs may be used to pass template_name="path/to/custom/template" or
        to change the view permissions with permission_required="some permission".
        Passing permission_required=None disables the permission system.
        (Access to /admin is still needed)
        """
        
        kwargs['model'] = self.model
        
        view_class = self.pdf_view_class
        
        return view_class.as_view(**kwargs)(request, pk=instance_pk)
    
    
    def get_site_urls_for_registration(self):
        
        urls = tuple(
            re_path(
                self.url_helper.get_action_url_pattern(action),
                self.pdf_view,
                name=self.url_helper.get_action_url_name(action),
            ) for action, kw in self.custom_site_pdf_views
        )
        
        return urls
    
class ModelAdminPdfAdminViewMixin:
    
    button_helper_class = PdfViewButtonHelper
    permission_helper_class = CustomActionPermissionHelper
    
    pdf_admin_view_class = getattr(settings, "DEFAULT_PDF_ADMIN_VIEW_PROVIDER", DEFAULT_PDF_ADMIN_VIEW_PROVIDER)


    def pdf_admin_view(self, request, instance_pk, **kwargs):
        """
        Serve an admin pdf view for a given instance
        
        The kwargs may be used to pass template_name="path/to/custom/template" or
        to change the view permissions with permission_required="some permission".
        Passing permission_required=None disables the permission system.
        (Access to /admin is still needed)
        """
        
        kwargs['model'] = self.model
        
        view_class = self.pdf_admin_view_class
        
        return view_class.as_view(**kwargs)(request, pk=instance_pk, model_admin=self)
    
    def get_admin_urls_for_registration(self):
        """
        Utilised by Wagtail's 'register_admin_urls' hook to register urls for
        our the views that class offers.
        """
        urls = super().get_admin_urls_for_registration()
        
        # check if there are custom views
        if hasattr(self, "get_custom_object_views"):
            
            urls = urls + tuple(
                re_path(
                    self.url_helper.get_action_url_pattern(action),
                    view,
                    name=self.url_helper.get_action_url_name(action))
                for action, view in self.get_custom_object_views()
            )
        
        return urls
    
    def get_custom_object_views(self):
        return [
            ("pdf", self.pdf_admin_view),
        ]

