# wagtail-pdf-view
Create PDF response views for Wagtail pages.

The goal of this extension is to provide a flexible but easy to use way to render Wagtail pages as PDF.
With this extension you can utilize all the benefits from the wagtail page system (previews, drafts, history) as well as the power of
*StreamField* and *RichText* for your generated PDF document.

Currently [weasyprint](https://github.com/Kozea/WeasyPrint) (for HTML to PDF conversion) and latex is supported.
If you are undecided which one to use, [weasyprint](https://github.com/Kozea/WeasyPrint) is recommended.

## Installing

Install the latest version from pypi:

```sh
pip install -U wagtail-pdf-view
# and either this for HTML -> PDF
pip install -U django-weasyprint
# and/or this for Latex -> PDF
pip install -U django-tex
```

and add the following to your installed apps:

```py
INSTALLED_APPS = [
    ...
    'wagtail_pdf_view',
    'wagtail.contrib.routable_page',
    ...
]
```

While [weasyprint](https://github.com/Kozea/WeasyPrint) is installed as dependency of [django-weasyprint](https://github.com/fdemmer/django-weasyprint) and works out of the box,
a working latex interpreter (lualatex) must be installed on your system if you want to use [django-tex](https://github.com/weinbusch/django-tex).

If [django-weasyprint](https://github.com/fdemmer/django-weasyprint) and [django-tex](https://github.com/weinbusch/django-tex) is installed, weasyprint is selected by default.
For [django-tex](https://github.com/weinbusch/django-tex) you should set `DEFAULT_PDF_VIEW_PROVIDER = WagtailTexView` in your settings.


## Usage

All you need to do to render your Wagtail page as PDF, is to inherit from `PdfModelMixin`.

**If you want to use latex, read the latex section below.**

Further configuration options include:
- `ROUTE_CONFIG` to enable rendering of the default HTML view and the PDF view at the same time
- `stylesheets` resp. `get_stylesheets` to include CSS stylesheets for [weasyprint](https://github.com/Kozea/WeasyPrint)
- `attachment` to control the file attachment (i.e. whether to download the PDF or open it in the browser)

## Examples

A very simple example page using Wagtails StreamField.
Like for a regular Wagtail page, the template should be located under: `<app_dir>/templates/<app>/simple_pdf_page.html`
**If you're using django-tex the template extention .tex is expected**.

```py
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core import blocks
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel

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
        StreamFieldPanel("content"),
    ]
    
    # OPTIONAL: If you want to include a stylesheet
    #stylesheets = ["css/your_stylesheet.css"]
```

### Usage of `ROUTE_CONFIG`:

A HTML first page, you can access the wagtail page as you're used e.g. *127.0.0.1/mypage*.
The PDF version will be available under *pdf/* e.g. *127.0.0.1/mypage/pdf*

```
class HtmlAndPdfPage(PdfViewPageMixin, Page):

    # HTML first
    ROUTE_CONFIG = [
        ("pdf", r'^pdf/$'),
        ("html", r'^$'),
    ]
    
```

A PDF first page, the PDF version is displayed with the regular url and
you can access the wagtail page under */html*, e.g. *127.0.0.1/mypage/html*

```
class HtmlAndPdfPage(PdfViewPageMixin, Page):
    
    # PDF first
    ROUTE_CONFIG = [
        ("pdf", r'^$'),
        ("html", r'^html/$'),
    ]
    
```

`ROUTE_CONFIG` is build on wagtails [routable_page](https://docs.wagtail.io/en/stable/reference/contrib/routablepage.html), you can specify routes as you want (e.g. `("html", r'^web/$')`)

## Using latex

When you want to use latex instead of HTML, you should be aware of the following:

You need to add django_tex to `INSTALLED_APPS`:

```py
INSTALLED_APPS = [
    ...
    'django_tex',
    ...
]
```

You need to add the jinja tex engine to `TEMPLATES` in your settings.py:
```py
TEMPLATES += [
    {
        'NAME': 'tex',
        'BACKEND': 'django_tex.engine.TeXEngine', 
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'wagtail_pdf_view.environment.latex_environment',
        },
    },
]
```

Set `DEFAULT_PDF_VIEW_PROVIDER` in your settings:

```
from wagtail_pdf_view.views import WagtailTexView
DEFAULT_PDF_VIEW_PROVIDER = WagtailTexView
```

In case you just want to use latex for a specific model settings you can overrite `PDF_VIEW_PROVIDER`:

```
from wagtail_pdf_view.views import WagtailTexView

class SimplePdfPage(PdfViewPageMixin, Page):

    # render with LaTeX instead
    PDF_VIEW_PROVIDER = WagtailTexView
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
