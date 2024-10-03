from wagtail.jinja2tags import WagtailCoreExtension

import jinja2

try:
    import django_tex
except ImportError:
    django_tex = None


from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock

import re
from html.parser import HTMLParser

from django.utils.safestring import mark_safe
from django.conf import settings

from markupsafe import Markup


class WagtailCoreExtensionLatex(WagtailCoreExtension):
    
    def _include_block(self, value, context, use_context, *args):
        """
        Automatically translate richtext blocks into latex
        """

        if isinstance(value.block, blocks.RichTextBlock) or isinstance(value.block, TableBlock):
            
            if hasattr(value, 'render_as_block'):
                if use_context:
                    new_context = context.get_all()
                else:
                    new_context = {}
                
                return Markup(richtext_as_tex(value.render_as_block(context=new_context)))

        return super()._include_block(value, context=context, use_context=use_context, *args)


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
        # table support
        self.table_caption = ''
        self.column_format_key = '__column_format__'
        self.table_column_counter = 0
        self.table_column_counter_max = 0
    
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
            
        # add support for tables
        if tag == "table":
            self.latex.append("\\begin{table}[H]\n\\centering\n\\begin{tabular}{ " + self.column_format_key + " }\n\\hline\n")
        elif tag == "caption":
            self.tex_inline = "\\caption{"
        elif tag == "thead":
            pass
        elif tag == "tbody":
            pass
        elif tag == "tr":
            pass
        elif tag == "th":
            if not self.table_column_counter:
                self.latex.append("\\textbf{")
            else:
                self.latex.append("& \\textbf{")

            # Update column counter
            self.table_column_counter += 1
            # Update maximum value
            if self.table_column_counter_max < self.table_column_counter:
                self.table_column_counter_max = self.table_column_counter
        elif tag == "td":
            if not self.table_column_counter:
                pass
            else:
                self.latex.append("& ")

            # Update column counter
            self.table_column_counter += 1
            # Update maximum value
            if self.table_column_counter_max < self.table_column_counter:
                self.table_column_counter_max = self.table_column_counter

    def handle_endtag(self, tag):
        
        # End inline mode, add line to latex statements
        if self.tex_inline:
            if tag == "a":
                self.latex.append(self.tex_inline+"}\n")
                # reset inline buffer
                self.tex_inline = ''
        else:
            # simple mapping e.g. </b> --> }
            if tag in self.mapping:
                self.latex.append(self.mapping[tag][1])

        # add support for tables
        if tag == "table":
            self.latex.append("\\end{tabular}\n" + self.table_caption + "\\end{table}")
            
            # build column format based on number of columns
            column_format = '|'
            for col in range(self.table_column_counter_max):
                column_format += 'c|'

            # replace column format key
            for idx, line in enumerate(self.latex):
                if self.column_format_key in line:
                    line = line.replace(self.column_format_key, column_format)
                    break
            self.latex[idx] = line
                
        elif tag == "caption":
            self.tex_inline += "}\n"
            self.table_caption = self.tex_inline
            # reset inline buffer
            self.tex_inline = ''
        elif tag == "thead":
            pass
        elif tag == "tbody":
            pass
        elif tag == "tr":
            self.latex.append(" \\\\ \\hline\n")
            # reset column counter
            self.table_column_counter = 0
        elif tag == "th":
            self.latex.append("} ")
        elif tag == "td":
            self.latex.append(" ")

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
