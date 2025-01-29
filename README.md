# wagtail-pdf-view
Render Wagtail pages and models as PDF document using [weasyprint](https://github.com/Kozea/WeasyPrint).

The goal of this extension is to provide a flexible but easy to use way to render Wagtail pages and Django models as PDF.
With this extension you can utilize all the benefits from the wagtail page system (previews, drafts, history) as well as the power of
*StreamField* and *RichText* for your generated PDF document.
Models may be easily rendered as PDF and will be accessible either through the admin interface or through a public URL.

![For PDF generation, this module provides many functions from the wagtail page system and offers simplified model rendering.](clip_wagtail_pdf_view_low.gif)

## Installing

Install the latest version from pypi:

```sh
# This package allows to convert HTML -> PDF using weasyprint
pip install -U wagtail-pdf-view
```

and add the following to your installed apps:

```py
# settings.py

INSTALLED_APPS = [
    ...
    'wagtail_pdf_view',
    'wagtail.contrib.routable_page',
    ...
]

# Specify the root url for weasyprint (fix static files not loading, e.g. when using docker)
# WEASYPRINT_BASEURL = '/'
```

Furthermore, you need to hook in `wagtail_pdf_view.urls` into your projects `urls.py`:


```py
# urls.py

urlpatterns = urlpatterns + [
    # hook in the 'live'-view PDFs under "pdf/"
    path("pdf/", include('wagtail_pdf_view.urls')),
    ...
    # IMPORTANT: This must be below the "pdf/" include
    path("", include(wagtail_urls)),
    ...
]
```

This is required for a working in panel preview (using [pdf.js](https://mozilla.github.io/pdf.js/)) and to access (model admin) PDFs from outside of the admin area.

On your production environment you need to refresh the static files:

```sh
python manage.py collectstatic
```


### LaTeX

While [weasyprint](https://github.com/Kozea/WeasyPrint) is installed as dependency of [django-weasyprint](https://github.com/fdemmer/django-weasyprint) and works out of the box,
a working latex interpreter (lualatex) must be installed on your system if you want to use [django-tex](https://github.com/weinbusch/django-tex).

Please follow the "Using LaTeX" instructions below.


## Usage for Pages

All you need to do to render your Wagtail `Page` as PDF, is to inherit from `PdfViewPageMixin`.
If you want to render a model instead, read the section **ModelAdmin** below.

**If you want to use latex, read the latex section below.**

A page inheriting from `PdfViewPageMixin` can be further configured with the options:
- `ROUTE_CONFIG` to enable rendering of the default HTML view and the PDF view at the same time
- `stylesheets` resp. `get_stylesheets` to include CSS stylesheets for [weasyprint](https://github.com/Kozea/WeasyPrint)
- `pdf_options`, `preview_pdf_options`, and `preview_panel_pdf_options` to change the compilation options of weasyprint for the page, the preview and the in panel preview respectively
- `attachment` to control the file attachment (i.e. whether to download the PDF or open it in the browser)

## Examples

A very simple example page using Wagtails `StreamField`.
Like for a regular Wagtail `Page`, the template should be located under: `<app_dir>/templates/<app>/simple_pdf_page.html`

**If you're using django-tex the template extention .tex is expected**.

```py
# models.py

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail import blocks
from wagtail.admin.edit_handlers import FieldPanel, StreamField

from wagtail_pdf_view.mixins import PdfViewPageMixin

# Inherit from PdfViewPageMixin
class SimplePdfPage(PdfViewPageMixin, Page):
    
    # you can create fields as you're used to, e.g. StreamField
    content = StreamField([
        ("heading", blocks.CharBlock(form_classname="full title")),
        ("text", blocks.RichTextBlock()),
    ], blank=True)
    
    # content panel for the CMS (same as always)
    content_panels = Page.content_panels + [
        StreamField("content"),
    ]
    
    # OPTIONAL: If you want to include a stylesheet
    #stylesheets = ["css/your_stylesheet.css"]
```

### Usage of `ROUTE_CONFIG`:

By default, i.e. without setting `ROUTE_CONFIG`, only the pdf-view is available, i.e. you may only view this page as pdf.
This is useful when you just want to display a generated pdf document easily.

```py
# models.py

class PdfOnlyPage(PdfViewPageMixin, Page):

    # PDF only (default case)
    ROUTE_CONFIG = [
        ("pdf", r'^$'),
        ("html", None),
    ]
    
```



A HTML first page: You can access the wagtail page as you're used e.g. *127.0.0.1/mypage*.
The PDF version will be available under *pdf/* e.g. *127.0.0.1/mypage/pdf*

```py
# models.py

class HtmlAndPdfPage(PdfViewPageMixin, Page):

    # HTML first
    ROUTE_CONFIG = [
        ("html", r'^$'),
        ("pdf", r'^pdf/$'),
    ]
    
```

Note that the order of *html* and *pdf* is not arbitrary:
The entry you set first, will be displayed by default when using wagtails preview function. Depending on your case, you may want to put *pdf* in the first place, so your editors get the pdf-view by default, while html-page url stays the same for the users.
In both cases your editors may access both views through the drop-down menu integrated in the preview button.

A PDF first page: The PDF version is displayed with the regular url and
you can access the wagtail page under */html*, e.g. *127.0.0.1/mypage/html*

```py
# models.py

class HtmlAndPdfPage(PdfViewPageMixin, Page):
    
    # PDF first
    ROUTE_CONFIG = [
        ("pdf", r'^$'),
        ("html", r'^html/$'),
    ]
    
```

`ROUTE_CONFIG` is build on wagtails [routable_page](https://docs.wagtail.io/en/stable/reference/contrib/routablepage.html), you can specify routes as desired (e.g. `("html", r'^web/$')`)

#### Reversing and using URLs in templates

Reversing url patterns is supported, which is useful in cases when you are serving multiple views (i.e. html and pdf).

Within templates, you can access the URLs for the different views by using `routablepageurl` from the [routable_page](https://docs.wagtail.io/en/stable/reference/contrib/routablepage.html) module:

```html
{% load wagtailroutablepage_tags %}

<!-- HTML Page URL-->
{% routablepageurl page "html" %}

<!-- PDF Page URL-->
{% routablepageurl page "pdf" %}


<!-- When looping over Page.get_children, you need to use the specific Page object -->
{% for subpage in page.get_children %}
    <li>{% routablepageurl subpage.specific "pdf" %}</li>
{% endfor %}
```

In most cases you don't need the full functionality of `routablepageurl`. To make things easy you can simply access the different views by the custom URL attributes `url_pdf` and `url_html`:

```html
<!-- HTML view url -->
{{page.url_html}}

<!-- PDF view url -->
{{page.url_pdf}}


<!-- When looping over Page.get_children, you need to use the specific Page object -->
{% for subpage in page.get_children %}
    <li>{{subpage.specific.url_pdf}}</li>
{% endfor %}
```

In python code `Page.reverse_subpage()` can be used to reverse a HTML-first page to obtain it's pdf-url:

```py
# this will be 'pdf/' in HTML-first mode
page.reverse_subpage('pdf')
```

## Usage with Models and ModelViewSet

Besides pages, it is also possible to render models as PDF.

### Migrating Legacy ModelAdmin Code

Wagtail 6 dropped support for ModelAdmin, thus the following adaptions need to be made:

- Substitude `modeladmin.mixins.ModelAdminPdfViewMixin` by `view.PdfViewSetMixin`. Add view with the `@register_pdf_view` decorator if you desire to make the PDF public.
- Replace `modeladmin.mixins.ModelAdminPdfAdminViewMixin` with `views.PdfAdminViewSetMixin`
- The attribute `YourModel.admin_template_name` was removed, declare `YourViewSet.template_name` instead

### PDF rendering for models

To enable model rendering, your model must inherit from `PdfModelMixin`:

```py
# models.py

from wagtail_pdf_view.mixins import PdfViewPageMixin, PdfModelMixin

class YourPdfModel(PdfModelMixin, models.Model):

    # the admin view uses a different template attribute to
    # prevent you from publishing sensitive content by accident
    
    template_name = "path/to/your_model.html"
```

This will add rendering methods like `serve()` to your model and will make the model furthermore previewable by adding `serve_preview()`.

### Serving a model as live view

If you want `YourPdfModel` to be accessible on the (live) website, a view must be specified to expose PDF-renderable models, as this is not done automatically.

```py
#views.py

from wagtail_pdf_view.views import WagtailWeasyView
from wagtail_pdf_view.hooks import register_pdf_view

from .models import YourPdfModel


# by default the view is registered under 'pdf' i.e. 'pdf/some/path/<..>'
# with the name 'wagtail_pdf_view:<app_label>.<object_name>'
@register_pdf_view('some/path/<str:pk>/')
class YourPdfModelView(WagtailWeasyView):
    model = YourPdfModel
```

Sub-classing `WagtailWeasyView` provides required functionality for PDF-rendering capable models.
By using the optional decorator `register_pdf_view(url)`, the specified model url is registered under `wagtail_pdf_view.urls`.


### ViewSet configuration

As described above, models that inherit from `PdfModelMixin` are renderable and previewable. To adapt to those additional functionalities, simply adjust your `ModelViewSet` to inherit from `PdfViewSetMixin`.

```py
#views.py

from wagtail.admin.viewsets.model import ModelViewSet

from wagtail_pdf_view.views import PdfViewSetMixin

from .models import Invoice


class YourPdfModelViewSet(PdfViewSetMixin, ModelViewSet):
    add_to_admin_menu = True
    model = YourPdfModel
    menu_label = 'Your Model'
    icon = 'cog'

    name = 'yourmodel'
```

In some scenarios, it is not desired to expose a PDF to the public.
To ease such cases, `PdfAdminViewSetMixin` exists as variant of `PdfViewSetMixin`.
Besides the preview functionallity, `PdfAdminViewSetMixin` also adds a `pdf_view_class` to the `ViewSet`, which is accessible through a _view pdf_ button.


```py
#views.py

from wagtail.admin.viewsets.model import ModelViewSet

from wagtail_pdf_view.views import PdfAdminViewSetMixin

from .models import Invoice


class YourPdfModelViewSet(PdfAdminViewSetMixin, ModelViewSet):
    add_to_admin_menu = True
    model = YourPdfModel
    menu_label = 'Your Model'
    icon = 'cog'

    name = 'yourmodel'
    
    ## PDF settings for the admin view, i.e. 'view pdf'
    
    ## Change the view class to render the view using latex
    #pdf_view_class = WagtailTexAdminView
    ## Set the pdf options for weasyprint e.g. to disable forms
    #pdf_options = {...}
    ## Set the attachment to download the PDF instead of opening
    #pdf_attachment = True
    ## Custom template
    #pdf_template_name = "path/to/your/template.html"
```

Changing or adding new buttons is possible by specifying a custom `index_view_class`.

### Custom model url registration

It is also possible to directly specify a model's url pattern instead of using `register_pdf_view()`.
Using `wagtail_pdf_view:<app_label>.<object_name>` as name is recommended to preserve url-revering dependent functionalities like _"view live"_.

```py
#urls.py

from wagtail_pdf_view.views import WagtailWeasyView

from .models import YourPdfModel

# register a pdf view for YourPdfModel
urlpatterns = [
    path('custom/url/path/<str:pk>/', WagtailWeasyView.as_view(model=YourPdfModel), name='your-model-name')
]
``` 


### Settings

The following settings are supported:
- `WAGTAIL_DEFAULT_PDF_OPTIONS`, `WAGTAIL_PREVIEW_PDF_OPTIONS`, and `WAGTAIL_PREVIEW_PANEL_PDF_OPTIONS` to set global options for weasyprint
- `WAGTAIL_PDF_VIEWER` to configure a different pdf viewer (instead of _pdf.js_) in the panel preview
- `WEASYPRINT_BASEURL` to fix static files loading problems, e.g. when using docker (from [django-weasyprint](https://github.com/fdemmer/django-weasyprint))

```py
# settings.py

# set default compiler options for weasyprint (e.g. to disable `pdf_forms` or to set the embedded image `dpi`)
WAGTAIL_DEFAULT_PDF_OPTIONS = {'pdf_forms': False}
WAGTAIL_DEFAULT_PDF_OPTIONS = {'dpi': 50}

# set default compiler options for weasyprint during preview (e.g. to disable `pdf_forms` in every preview) 
WAGTAIL_PREVIEW_PDF_OPTIONS = {'pdf_forms': False}

# set the compiler options for weasyprint when rendering inside the preview panel
WAGTAIL_PREVIEW_PANEL_PDF_OPTIONS = {'pdf_forms': True}
WAGTAIL_PREVIEW_PANEL_PDF_OPTIONS = {}

# disable pdf.js as in panel pdf preview
WAGTAIL_PDF_VIEWER = {}

# Specify the root url for weasyprint (fix static files not loading)
WEASYPRINT_BASEURL = '/'
```

## Using LaTeX


When you want to use LaTeX instead of HTML, you should be do the following:


```sh
# if you instead want to compile Latex -> PDF you need to install this package with optional dependency django-tex
pip install -U wagtail-pdf-view[django-tex]
```

You need to add django_tex to `INSTALLED_APPS`, add the jinja tex engine to `TEMPLATES` and set `WAGTAIL_PDF_VIEW` in your settings.py:

```py
# settings.py

INSTALLED_APPS = [
    ...
    'wagtail_pdf_view',
    'wagtail_pdf_view_tex',
    'wagtail.contrib.routable_page',
    'django_tex',
    ...
]

TEMPLATES += [
    {
        'NAME': 'tex',
        'BACKEND': 'django_tex.engine.TeXEngine', 
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'wagtail_pdf_view_tex.environment.latex_environment',
        },
    },
]

```


The `pdf_view_class` of each `Model`, `Page`, and `ModelViewSet` need to be changed to `WagtailTexView`:

```py
# models.py

from wagtail_pdf_view.views import WagtailTexView

class SimplePdfPage(PdfViewPageMixin, Page):

    # render with LaTeX instead
    pdf_view_class = WagtailTexView
```

In general you should include *wagtail_preamble.tex*, which provides required packages and commands for proper richtext handling.

```
{% include 'wagtail_preamble.tex' %}
```

You can set custom width for the richtext image insertion
 
```
{% raw %}
\renewcommand{\fullwidth} {0.8\textwidth}
\renewcommand{\partialwidth} {0.5\textwidth}
{% endraw  %} 
```

A very useful block is *raw*, this prevents the jinja rendering engine from interpreting everything inside.
This is nice if you want to create a latex command

```
{% raw  %}
{% endraw  %}
```

For further information read [the django-tex github page](https://github.com/weinbusch/django-tex)
