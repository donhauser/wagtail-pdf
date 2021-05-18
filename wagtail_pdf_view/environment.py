from wagtail.core.jinja2tags import WagtailCoreExtension

import jinja2

try:
    import django_tex
except ImportError:
    django_tex = None


from wagtail.core import blocks

import re
from html.parser import HTMLParser

from django.utils.safestring import mark_safe
from django.conf import settings


class WagtailCoreExtensionLatex(WagtailCoreExtension):
    
    def _include_block(self, value, context=None):
        """
        Automatically translate richtext blocks into latex
        """
        
        if isinstance(value.block, blocks.RichTextBlock):
            
            if hasattr(value, 'render_as_block'):
                if context:
                    new_context = context.get_all()
                else:
                    new_context = {}
                
                return jinja2.Markup(richtext_as_tex(value.render_as_block(context=new_context)))

        return super()._include_block(value, context=context)


def latex_escape(string):
    # Map every special latex character to its escaped version
    
    string = string.replace("\\", "\\textbackslash")
    
    for symbol in "&%$#_{}":
        string = string.replace(symbol, "\\"+symbol)
        
    string = string.replace("~", "\\textasciitilde")
    string = string.replace("^", "\\textasciicircum")

    return string


class SimpleHtmlToLatexParser(HTMLParser):
    """
    Translate HTML into LateX
    
    This is a relatively basic parser, which maps common html tags to latex
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.latex = []
        self.tex_inline = ''
    
    # Some simple HTML Tags, which have a similar representation in latex
    mapping = {
        'i': [" \\textit{", "} "],
        'b': [" \\textbf{", "} "],
        'p': ["\n", "\n"],
        'h1': ["\n\\section{", "}\n"],
        'h2': ["\n\\subsection{", "}\n"],
        'h3': ["\n\\subsubsection{", "}\n"],
        'h4': ["\n\\paragraph{", "}\n"],
        'ul': ["\n\\begin{itemize}\n", "\n\\end{itemize}\n"],
        'ol': ["\n\\begin{enumerate}\n", "\n\\end{enumerate}\n"],
        'li': ["\\item ", "\n"],
        'br': ["\n\\\\\n", ""],
        #'img':["\\includegraphics{", "}"],
        #'a': ["\\href{", "}"],
    }
    
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        
        # simple mapping e.g. <b> --> \textbf{
        if tag in self.mapping:
            self.latex.append(self.mapping[tag][0])
        
        # the link must be in one line i.e. WITHOUT linebreaks --> Inline mode
        if tag == "a":
            self.tex_inline = "\n\\href{"+a.get("href", '')+"}{"
        
        # simply embedding <img> as includegraphics is not very useful, as LateX does not support CSS and classes
        # For this reason <img> is translated into a command which can then be customized within latex
        if tag == "img":
            self.latex.append("\\wagtailimage{"+a.get("src", '')+"}{"+a.get("class", '')+"}")
            

    def handle_endtag(self, tag):
        
        # End inline mode, add line to latex statements
        if self.tex_inline:
            if tag == "a":
                self.latex.append(self.tex_inline+"}\n")
            
            self.tex_inline = ''
        else:
            # simple mapping e.g. </b> --> }
            if tag in self.mapping:
                self.latex.append(self.mapping[tag][1])

    def handle_data(self, data):
        
        # preprocess the data 
        data = latex_escape(data).strip()
        
        # inline mode (no breaks)
        if self.tex_inline:
            self.tex_inline += data
        else:
            self.latex.append(data)
            
    def parse(self, html):
        # reset
        self.latex = []
        self.tex_inline = ''
        
        # process html
        self.feed(html)
        
        latex = "".join(self.latex)
        
        # remove multiple spaces
        latex = re.sub(' +', ' ', latex)
        
        # we're outputting latex so autoescape does not make any sense.
        return mark_safe(latex)


# The user may define a custom latex parser
HTML_TO_LATEX_PARSER = getattr(settings, "HTML_TO_LATEX_PARSER", SimpleHtmlToLatexParser)

def richtext_as_tex(richtext):
    # Parse a richtext as latex
    try:
        html = richtext.__html__()
    except AttributeError:
        html = str(richtext)
    
    return HTML_TO_LATEX_PARSER().parse(html)


if django_tex:
    from django_tex.filters import FILTERS

    def latex_environment(**options):
        # Setup a Jinja2 environment usable for wagtail in latex mode
        
        if not "autoescape" in options.keys():
            options["autoescape"] = None
        
        if not "extensions" in options.keys():
            options["extensions"] = []
        
        options["extensions"].append("django_tex.extensions.GraphicspathExtension")
        options["extensions"].append(WagtailCoreExtensionLatex)
        
        # add django-tex filters and richtext filter
        env = jinja2.Environment(**options)
        env.filters.update(FILTERS)
        env.filters["richtext"] = richtext_as_tex
        
        return env
