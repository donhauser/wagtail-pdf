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

Default configuration:

```py
class PdfOnlyPage(PdfViewPageMixin, Page):

    # PDF only
    ROUTE_CONFIG = [
        ("pdf", r'^$'),
        ("html", None),
    ]
    
```
By default only the pdf-view is available, i.e. you may only view this page as pdf.
This is useful when you just want to display a generated pdf document easily.


A HTML first page: You can access the wagtail page as you're used e.g. *127.0.0.1/mypage*.
The PDF version will be available under *pdf/* e.g. *127.0.0.1/mypage/pdf*

```py
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
class HtmlAndPdfPage(PdfViewPageMixin, Page):
    
    # PDF first
    ROUTE_CONFIG = [
        ("pdf", r'^$'),
        ("html", r'^html/$'),
    ]
    
```

`ROUTE_CONFIG` is build on wagtails [routable_page](https://docs.wagtail.io/en/stable/reference/contrib/routablepage.html), you can specify routes as you want (e.g. `("html", r'^web/$')`)

#### Reversing and using URLs in templates

As of version 1.4 reversing url patterns is supported.

This feature is useful in cases when you are serving multiple views (i.e. html and pdf).

You can access the URLs for the different views by using `routablepageurl` from the [routable_page](https://docs.wagtail.io/en/stable/reference/contrib/routablepage.html) module:

```html
{% load wagtailroutablepage_tags %}

<!-- HTML Page URL-->
{% routablepageurl page "html" %}

<!-- PDF Page URL-->
{% routablepageurl page "pdf" %}


<!-- TODO can this be removed?-->
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

If you are just interested in the extention to the normal page url:

```py
# this will be 'pdf/' in HTML-first mode
page.reverse_subpage('pdf')
```

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

```py
from wagtail_pdf_view.views import WagtailTexView
DEFAULT_PDF_VIEW_PROVIDER = WagtailTexView
```

In case you just want to use latex for a specific model settings you can overrite `PDF_VIEW_PROVIDER`:

```py
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
