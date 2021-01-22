from wagtail.core.jinja2tags import WagtailCoreExtension
from jinja2 import Environment

import jinja2

from django_tex.filters import FILTERS


from wagtail.core import blocks

class WagtailCoreExtensionLatex(WagtailCoreExtension):
    
    def _include_block(self, value, context=None):
        
        if isinstance(value.block, blocks.RichTextBlock):
            
            if hasattr(value, 'render_as_block'):
                if context:
                    new_context = context.get_all()
                else:
                    new_context = {}
                
                return jinja2.Markup(richtext_as_tex(value.render_as_block(context=new_context)))

        return super()._include_block(value, context=context)


from html.parser import HTMLParser

# TODO try escape_latex from django-tex
def latex_escape(string):
    
    string = string.replace("\\", "\\textbackslash")
    
    for symbol in "&%$#_{}":
        string = string.replace(symbol, "\\"+symbol)
        
    string = string.replace("~", "\\textasciitilde")
    string = string.replace("^", "\\textasciicircum")

    return string

from django.utils.safestring import mark_safe

class SimpleHtmlToLatexParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.latex = []
        self.tex_inline = ''
        
    mapping = {
        'i': ["\\textit{", "}"],
        'b': ["\\textbf{", "}"],
        'p': ["\n", "\n"],
        'h2': ["\n\\subsection{", "}\n"],
        'h3': ["\n\\subsubsection{", "}\n"],
        'h4': ["\n\\paragraph{", "}\n"],
        'ul': ["\n\\begin{itemize}\n", "\n\\end{itemize}\n"],
        'ol': ["\n\\begin{enumerate}\n", "\n\\end{enumerate}\n"],
        'li': ["\\item ", "\n"],
        'br': ["\n\\\\\n", ""],
        #'img':["\\includegraphics{", ""],
        #'a': ["\\href{", "}"],
    }
    
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        
        if tag in self.mapping:
            self.latex.append(self.mapping[tag][0])
            
        if tag == "a":
            self.tex_inline = "\n\\href{"+a.get("href", '')+"}{"
            
        if tag == "img":
            self.latex.append("\\wagtailimage{"+a.get("src", '')+"}{"+a.get("class", '')+"}")
            

    def handle_endtag(self, tag):
        
        if self.tex_inline:
            if tag == "a":
                self.latex.append(self.tex_inline+"}\n")
            
            self.tex_inline = ''
        else:
            if tag in self.mapping:
                self.latex.append(self.mapping[tag][1])

    def handle_data(self, data):
        data = latex_escape(data).strip()#.replace("\n","")
        
        if self.tex_inline:
            self.tex_inline += data
        else:
            self.latex.append(data)
            
    def parse(self, html):
        self.latex = []
        self.tex_inline = ''
        
        self.feed(html)
        
        return mark_safe("".join(self.latex))


from django.conf import settings

HTML_TO_LATEX_PARSER = getattr(settings, "HTML_TO_LATEX_PARSER", SimpleHtmlToLatexParser)

def richtext_as_tex(richtext):
    return HTML_TO_LATEX_PARSER().parse(richtext.__html__())


def my_environment(**options):
    
    if not "autoescape" in options:
        options["autoescape"] = None
    
    options["extensions"].append("django_tex.extensions.GraphicspathExtension")
    options["extensions"].append(WagtailCoreExtensionLatex)
    
    env = Environment(**options)
    env.filters.update(FILTERS)
    env.filters["richtext"] = richtext_as_tex
    
    return env
