
from django.urls import include, path, re_path
from wagtail import hooks
from wagtail.utils.urlpatterns import decorate_urlpatterns

urlpatterns = [
]


# Import additional urlpatterns from any apps that define a register_site_urls hook
# The urls are NOT put behind 'admin/'
for fn in hooks.get_hooks('register_pdf_site_urls'):
    urls = fn()
    if urls:
        urlpatterns += urls 
