#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007 Søren Roug, European Environment Agency
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# Contributor(s):
#
#import pdb
#pdb.set_trace()
import zipfile
import xml.sax
from xml.sax import handler
from xml.sax.xmlreader import InputSource
from xml.sax.saxutils import escape, quoteattr

try:
    from io import StringIO
except ImportError:
    from io import StringIO

from .namespaces import ANIMNS, CHARTNS, CONFIGNS, DCNS, DR3DNS, DRAWNS, FONS, \
  FORMNS, MATHNS, METANS, NUMBERNS, OFFICENS, PRESENTATIONNS, SCRIPTNS, \
  SMILNS, STYLENS, SVGNS, TABLENS, TEXTNS, XLINKNS

# Handling of styles
#
# First there are font face declarations. These set up a font style that will be
# referenced from a text-property. The declaration describes the font making
# it possible for the application to find a similar font should the system not
# have that particular one. The StyleToCSS stores these attributes to be used
# for the CSS2 font declaration.
#
# Then there are default-styles. These set defaults for various style types:
#  "text", "paragraph", "section", "ruby", "table", "table-column", "table-row",
#  "table-cell", "graphic", "presentation", "drawing-page", "chart".
# Since CSS2 can't refer to another style, ODF2XHTML add these to all
# styles unless overridden.
#
# The real styles are declared in the <style:style> element. They have a
# family referring to the default-styles, and may have a parent style.
# 
# Styles have scope. The same name can be used for both paragraph and
# character etc. styles Since CSS2 has no scope we use a prefix. (Not elegant)
# In ODF a style can have a parent, these parents can be chained.

class StyleToCSS:
    """ The purpose of the StyleToCSS class is to contain the rules to convert
        ODF styles to CSS2. Since it needs the generic fonts, it would probably
        make sense to also contain the Styles in a dict as well..
    """

    def __init__(self):
        # Font declarations
        self.fontdict = {}

        # Fill-images from presentations for backgrounds
        self.fillimages = {}

        self.ruleconversions = {
            (DRAWNS,'fill-image-name'): self.c_drawfillimage,
            (FONS,"background-color"): self.c_fo,
            (FONS,"border"): self.c_fo,
            (FONS,"border-bottom"): self.c_fo,
            (FONS,"border-left"): self.c_fo,
            (FONS,"border-right"): self.c_fo,
            (FONS,"border-top"): self.c_fo,
            (FONS,"color"): self.c_fo,
            (FONS,"font-family"): self.c_fo,
            (FONS,"font-size"): self.c_fo,
            (FONS,"font-style"): self.c_fo,
            (FONS,"font-variant"): self.c_fo,
            (FONS,"font-weight"): self.c_fo,
            (FONS,"line-height"): self.c_fo,
            (FONS,"margin"): self.c_fo,
            (FONS,"margin-bottom"): self.c_fo,
            (FONS,"margin-left"): self.c_fo,
            (FONS,"margin-right"): self.c_fo,
            (FONS,"margin-top"): self.c_fo,
            (FONS,"min-height"): self.c_fo,
            (FONS,"padding"): self.c_fo,
            (FONS,"padding-bottom"): self.c_fo,
            (FONS,"padding-left"): self.c_fo,
            (FONS,"padding-right"): self.c_fo,
            (FONS,"padding-top"): self.c_fo,
            (FONS,"page-width"): self.c_page_width,
            (FONS,"page-height"): self.c_page_height,
            (FONS,"text-align"): self.c_text_align,
            (FONS,"text-indent") :self.c_fo,
            (TABLENS,'border-model') :self.c_border_model,
            (STYLENS,'width') : self.c_width,
            (STYLENS,'column-width') : self.c_width,
            (STYLENS,"font-name"): self.c_fn,
            (STYLENS,'text-position'): self.c_text_position,
            (STYLENS,'horizontal-pos'): self.c_hp,
            # FIXME Should do style:vertical-pos here
        }

    def save_font(self, name, family, generic):
        """ It is possible that the HTML browser doesn't know how to
            show a particular font. Fortunately ODF provides generic fallbacks.
            Unfortunately they are not the same as CSS2.
            CSS2: serif, sans-serif, cursive, fantasy, monospace
            ODF: roman, swiss, modern, decorative, script, system
            This method put the font and fallback into a dictionary
        """
        htmlgeneric = "sans-serif"
        if   generic == "roman": htmlgeneric = "serif"
        elif generic == "swiss": htmlgeneric = "sans-serif"
        elif generic == "modern": htmlgeneric = "monospace"
        elif generic == "decorative": htmlgeneric = "sans-serif"
        elif generic == "script": htmlgeneric = "monospace"
        elif generic == "system": htmlgeneric = "serif"
        self.fontdict[name] = (family, htmlgeneric)

    def c_drawfillimage(self, ruleset, sdict, rule, val):
        """ Fill a figure with an image. Since CSS doesn't let you resize images
            this should really be implemented as an absolutely position <img>
            with a width and a height
        """
        sdict['background-image'] = "url('%s')" % self.fillimages[val]

    def c_fo(self, ruleset, sdict, rule, val):
        """ XSL formatting attributes """
        selector = rule[1]
        sdict[selector] = val

    def c_border_model(self, ruleset, sdict, rule, val):
        """ Convert to CSS2 border model """
        if val == 'collapsing':
            sdict['border-collapse'] ='collapse'
        else:
            sdict['border-collapse'] ='separate'

    def c_width(self, ruleset, sdict, rule, val):
        """ Set width of box """
        sdict['width'] = val

    def c_text_align(self, ruleset, sdict, rule, align):
        """ Text align """
        if align == "start": align = "left"
        if align == "end": align = "right"
        sdict['text-align'] = align

    def c_fn(self, ruleset, sdict, rule, fontstyle):
        """ Generate the CSS font family
            A generic font can be found in two ways. In a <style:font-face>
            element or as a font-family-generic attribute in text-properties.
        """
        generic = ruleset.get((STYLENS,'font-family-generic') )
        if generic is not None:
            self.save_font(fontstyle, fontstyle, generic)
        family, htmlgeneric = self.fontdict.get(fontstyle, (fontstyle, 'serif'))
        sdict['font-family'] = '%s, %s'  % (family, htmlgeneric)

    def c_text_position(self, ruleset, sdict, rule, tp):
        """ Text position. This is used e.g. to make superscript and subscript
        """
        textpos = tp.split(' ')
        if len(textpos) == 2 and textpos[0] != "0%":
            # Bug in OpenOffice. If vertical-align is 0% - ignore the text size.
            sdict['font-size'] = textpos[1]
        sdict['vertical-align'] = textpos[0]

    def c_hp(self, ruleset, sdict, rule, hpos):
        #FIXME: Frames wrap-style defaults to 'parallel', graphics to 'none'.
        # It is properly set in the parent-styles, but the program doesn't
        # collect the information.
        wrap = ruleset.get((STYLENS,'wrap'),'parallel')
        # Can have: from-left, left, center, right, from-inside, inside, outside
        if hpos == "center":
            sdict['margin-left'] = "auto"
            sdict['margin-right'] = "auto"
        else:
            # force it to be *something* then delete it
            sdict['margin-left'] = sdict['margin-right'] = ''
            del sdict['margin-left'], sdict['margin-right']

        if hpos in ("right","outside"):
            if wrap in ( "left", "parallel"):
                sdict['float'] = "right"
            elif wrap == "run-through":
                sdict['position'] = "absolute" # Simulate run-through
                sdict['top'] = "0"
                sdict['right'] = "0"
            else:
                sdict['position'] = "relative" # No wrapping
                sdict['top'] = "0"
                sdict['right'] = "0"
        elif hpos in ("left", "inside"):
            if wrap in ( "right", "parallel"):
                sdict['float'] = "left"
            elif wrap == "run-through":
                sdict['position'] = "absolute" # Simulate run-through
                sdict['top'] = "0"
                sdict['left'] = "0"
            else:
                sdict['position'] = "relative" # No wrapping
                sdict['top'] = "0"
                sdict['left'] = "0"
        elif hpos in ("from-left", "from-inside"):
            if wrap in ( "right", "parallel"):
                sdict['float'] = "left"
            else:
                sdict['position'] = "relative" # No wrapping
                if (SVGNS,'x') in ruleset:
                    sdict['left'] = ruleset[(SVGNS,'x')]

    def c_page_width(self, ruleset, sdict, rule, val):
        """ Set width of box
            HTML doesn't really have a page-width. It is always 100% of the browser width
        """
        sdict['width'] = val

    def c_page_height(self, ruleset, sdict, rule, val):
        """ Set height of box """
        sdict['height'] = val

    def convert_styles(self, ruleset):
        """ Rule is a tuple of (namespace, name). If the namespace is '' then
            it is already CSS2
        """
        sdict = {}
        for rule,val in list(ruleset.items()):
            if rule[0] == '':
                sdict[rule[1]] = val
                continue
            method = self.ruleconversions.get(rule, None )
            if method:
                method(ruleset, sdict, rule, val)
        return sdict


class TagStack:
    def __init__(self):
        self.stack = []

    def push(self, tag, attrs):
        self.stack.append( (tag, attrs) )

    def pop(self):
        item = self.stack.pop()
        return item

    def stackparent(self):
        item = self.stack[-1]
        return item[1]

    def rfindattr(self, attr):
        """ Find a tag with the given attribute """
        for tag, attrs in self.stack:
            if attr in attrs:
                return attrs[attr]
        return None
    def count_tags(self, tag):
        c = 0
        for ttag, tattrs in self.stack:
            if ttag == tag: c = c + 1
        return c

special_styles = {
   'S-Emphasis':'em',
   'S-Citation':'cite',
   'S-Strong_20_Emphasis':'strong',
   'S-Variable':'var',
   'S-Definition':'dfn',
   'S-Teletype':'tt',
   'P-Heading_20_1':'h1',
   'P-Heading_20_2':'h2',
   'P-Heading_20_3':'h3',
   'P-Heading_20_4':'h4',
   'P-Heading_20_5':'h5',
   'P-Heading_20_6':'h6',
   'P-Caption':'caption',
   'P-Addressee':'address',
#  'P-List_20_Heading':'dt',
#  'P-List_20_Contents':'dd',
   'P-Preformatted_20_Text':'pre',
#  'P-Table_20_Heading':'th',
#  'P-Table_20_Contents':'td',
   'P-Text_20_body':'p'
}

#-----------------------------------------------------------------------------
#
# ODFCONTENTHANDLER
#
#-----------------------------------------------------------------------------
class ODF2XHTML(handler.ContentHandler):
    """ The ODF2XHTML parses an ODF file and produces XHTML"""

    def wlines(self,s):
        if s != '': self.lines.append(s)

    def __init__(self):
        self.xmlfile = ''
        self.title = ''
        self.lines = []
        self.wfunc = self.wlines
        self.data = []
        self.tagstack = TagStack()
        self.pstack = []
        self.processelem = True
        self.processcont = True
        self.listtypes = {}
        self.headinglevels = [0, 0,0,0,0,0, 0,0,0,0,0] # level 0 to 10
        self.cs = StyleToCSS()

        # Style declarations
        self.stylestack = []
        self.styledict = {}
        self.currentstyle = None

        # Footnotes and endnotes
        self.notedict = {}
        self.currentnote = 0
        self.notebody = ''

        # Tags from meta.xml
        self.metatags = []

        # Tags
        self.elements = {
        (DCNS, 'title'): (self.s_processcont, self.e_dc_title),
        (DCNS, 'language'): (self.s_processcont, self.e_dc_contentlanguage),
        (DCNS, 'creator'): (self.s_processcont, self.e_dc_metatag),
        (DCNS, 'description'): (self.s_processcont, self.e_dc_metatag),
        (DCNS, 'date'): (self.s_processcont, self.e_dc_metatag),
        (DRAWNS, 'frame'): (self.s_draw_frame, self.e_draw_frame),
        (DRAWNS, 'image'): (self.s_draw_image, None),
        (DRAWNS, 'fill-image'): (self.s_draw_fill_image, None),
        (DRAWNS, "layer-set"):(self.s_ignorexml, None),
        (DRAWNS, 'page'): (self.s_draw_page, self.e_draw_page),
        (METANS, 'keyword'): (self.s_processcont, self.e_dc_metatag),
        (METANS, 'generator'):(self.s_processcont, self.e_dc_metatag),
        (NUMBERNS, "boolean-style"):(self.s_ignorexml, None),
        (NUMBERNS, "currency-style"):(self.s_ignorexml, None),
        (NUMBERNS, "date-style"):(self.s_ignorexml, None),
        (NUMBERNS, "number-style"):(self.s_ignorexml, None),
        (NUMBERNS, "text-style"):(self.s_ignorexml, None),
        (OFFICENS, "automatic-styles"):(self.s_office_automatic_styles, None),
        (OFFICENS, "document-content"):(self.s_office_document_content, self.e_office_document_content),
        (OFFICENS, "forms"):(self.s_ignorexml, None),
        (OFFICENS, "meta"):(self.s_ignorecont, None),
        (OFFICENS, "presentation"):(self.s_office_presentation, self.e_office_presentation),
        (OFFICENS, "spreadsheet"):(self.s_office_spreadsheet, self.e_office_spreadsheet),
        (OFFICENS, "styles"):(self.s_office_styles, None),
        (OFFICENS, "text"):(self.s_office_text, self.e_office_text),
        (OFFICENS, "scripts"):(self.s_ignorexml, None),
        (PRESENTATIONNS, "notes"):(self.s_ignorexml, None),
        (STYLENS, "default-style"):(self.s_style_default_style, self.e_style_default_style),
        (STYLENS, "drawing-page-properties"):(self.s_style_handle_properties, None),
        (STYLENS, "font-face"):(self.s_style_font_face, None),
        (STYLENS, "graphic-properties"):(self.s_style_handle_properties, None),
        (STYLENS, "handout-master"):(self.s_ignorexml, None),
        (STYLENS, "master-page"):(self.s_style_master_page, None),
        (STYLENS, "page-layout-properties"):(self.s_style_handle_properties, None),
        (STYLENS, "page-layout"):(self.s_style_page_layout, self.e_style_page_layout),
        (STYLENS, "paragraph-properties"):(self.s_style_handle_properties, None),
        (STYLENS, "style"):(self.s_style_style, self.e_style_style),
        (STYLENS, "table-cell-properties"):(self.s_style_handle_properties, None),
        (STYLENS, "table-column-properties"):(self.s_style_handle_properties, None),
        (STYLENS, "table-properties"):(self.s_style_handle_properties, None),
        (STYLENS, "text-properties"):(self.s_style_handle_properties, None),
        (TABLENS, 'covered-table-cell'): (self.s_ignorexml, None),
        (TABLENS, 'table-cell'): (self.s_table_table_cell, self.e_table_table_cell),
        (TABLENS, 'table-column'): (self.s_table_table_column, None),
        (TABLENS, 'table-row'): (self.s_table_table_row, self.e_table_table_row),
        (TABLENS, 'table'): (self.s_table_table, self.e_table_table),
        (TEXTNS, 'a'): (self.s_text_a, self.e_text_a),
        (TEXTNS, "alphabetical-index-source"):(self.s_text_x_source, self.e_text_x_source),
        (TEXTNS, "bibliography-configuration"):(self.s_ignorexml, None),
        (TEXTNS, "bibliography-source"):(self.s_text_x_source, self.e_text_x_source),
        (TEXTNS, 'h'): (self.s_text_h, self.e_text_h),
        (TEXTNS, "illustration-index-source"):(self.s_text_x_source, self.e_text_x_source),
        (TEXTNS, 'line-break'):(self.s_text_line_break, None),
        (TEXTNS, "linenumbering-configuration"):(self.s_ignorexml, None),
        (TEXTNS, "list"):(self.s_text_list, self.e_text_list),
        (TEXTNS, "list-item"):(self.s_text_list_item, self.e_text_list_item),
        (TEXTNS, "list-level-style-bullet"):(self.s_text_list_level_style_bullet, self.e_text_list_level_style_bullet),
        (TEXTNS, "list-level-style-number"):(self.s_text_list_level_style_number, self.e_text_list_level_style_number),
        (TEXTNS, "list-style"):(None, None),
        (TEXTNS, "note"):(self.s_text_note, None),
        (TEXTNS, "note-body"):(self.s_text_note_body, self.e_text_note_body),
        (TEXTNS, "note-citation"):(None, self.e_text_note_citation),
        (TEXTNS, "notes-configuration"):(self.s_ignorexml, None),
        (TEXTNS, "object-index-source"):(self.s_text_x_source, self.e_text_x_source),
        (TEXTNS, 'p'): (self.s_text_p, self.e_text_p),
        (TEXTNS, 's'): (self.s_text_s, None),
        (TEXTNS, 'span'): (self.s_text_span, self.e_text_span),
        (TEXTNS, 'tab'): (self.s_text_tab, None),
        (TEXTNS, "table-index-source"):(self.s_text_x_source, self.e_text_x_source),
        (TEXTNS, "table-of-content-source"):(self.s_text_x_source, self.e_text_x_source),
        (TEXTNS, "user-index-source"):(self.s_text_x_source, self.e_text_x_source),
        }

    def writeout(self, s):
        if s != '':
            self.wfunc(s)

    def writedata(self):
        d = ''.join(self.data)
        if d != '':
            self.writeout(escape(d))

    def opentag(self, tag, attrs={}):
        """ Create an open HTML tag """
        a = []
        for key,val in list(attrs.items()):
            a.append('''%s=%s''' % (key, quoteattr(val)))
        if len(a) == 0:
            self.writeout("<%s>" % tag)
        else:
            self.writeout("<%s %s>" % (tag, " ".join(a)))

    def closetag(self, tag):
        self.writeout("</%s>\n" % tag)

    def emptytag(self, tag, attrs={}):
        a = []
        for key,val in list(attrs.items()):
            a.append('''%s=%s''' % (key, quoteattr(val)))
        self.writeout("<%s %s/>\n" % (tag, " ".join(a)))

#--------------------------------------------------
    def characters(self, data):
        if self.processelem and self.processcont:
            self.data.append(data)

    def handle_starttag(self, tag, method, attrs):
        method(tag,attrs)

    def handle_endtag(self, tag, attrs, method):
        method(tag, attrs)

    def startElementNS(self, tag, qname, attrs):
        self.pstack.append( (self.processelem, self.processcont) )
        if self.processelem:
            method = self.elements.get(tag, (None, None) )[0]
            if method:
                self.handle_starttag(tag, method, attrs)
            else:
                self.unknown_starttag(tag,attrs)
        self.tagstack.push( tag, attrs )

    def endElementNS(self, tag, qname):
        stag, attrs = self.tagstack.pop()
        if self.processelem:
            method = self.elements.get(tag, (None, None) )[1]
            if method:
                self.handle_endtag(tag, attrs, method)
            else:
                self.unknown_endtag(tag, attrs)
        self.processelem, self.processcont = self.pstack.pop()

    def unknown_starttag(self, tag, attrs):
        pass

    def unknown_endtag(self, tag, attrs):
        pass

    def s_ignorexml(self, tag, attrs):
        """ Ignore this xml element and all children of it
            It will automatically stop ignoring
        """
        self.processelem = False

    def s_ignorecont(self, tag, attrs):
        self.processcont = False

    def s_processcont(self, tag, attrs):
        self.processcont = True

    def classname(self, attrs):
        """ Generate a class name from a style name """
        c = attrs[(TEXTNS,'style-name')]
        c = c.replace(".","_")
        return c

#--------------------------------------------------

    def purgedata(self):
        self.data = []

#-----------------------------------------------------------------------------
#
# Handle meta data
#
#-----------------------------------------------------------------------------
    def e_dc_title(self, tag, attrs):
        """ Get the title from the meta data and create a HTML <title>
        """
        self.metatags.append('<title>%s</title>\n' % escape(''.join(self.data)))
        self.title = ''.join(self.data)
        self.data = []

    def e_dc_metatag(self, tag, attrs):
        """ Any other meta data is added as a <meta> element
        """
        self.metatags.append('<meta name="%s" content=%s/>\n' % (tag[1], quoteattr(''.join(self.data))))
        self.data = []

    def e_dc_contentlanguage(self, tag, attrs):
        """ Set the content language. Identifies the targeted audience
        """
        self.metatags.append('<meta http-equiv="content-language" content="%s"/>\n' % ''.join(self.data))
        self.data = []

    def s_draw_frame(self, tag, attrs):
        """ A <draw:frame> is made into a <div> in HTML which is then styled
        """
        name = "G-" + attrs.get( (DRAWNS,'style-name'), "")
        if name == 'G-':
            name = "PR-" + attrs.get( (PRESENTATIONNS,'style-name'), "")
        name = name.replace(".","_")
        style = "position: absolute;"
        if (SVGNS,"width") in attrs:
            style = style + "width:" + attrs[(SVGNS,"width")] + ";"
        if (SVGNS,"height") in attrs:
            style = style + "height:" +  attrs[(SVGNS,"height")] + ";"
        if (SVGNS,"x") in attrs:
            style = style + "left:" +  attrs[(SVGNS,"x")] + ";"
        if (SVGNS,"y") in attrs:
            style = style + "top:" +  attrs[(SVGNS,"y")] + ";"
        self.opentag('div', {'class': name, 'style': style})

    def e_draw_frame(self, tag, attrs):
        """ End the <draw:frame>
        """
        self.closetag('div')

    def s_draw_fill_image(self, tag, attrs):
        name = attrs.get( (DRAWNS,'name'), "NoName")
        imghref = attrs[(XLINKNS,"href")]
        imghref = self.rewritelink(imghref)
        self.cs.fillimages[name] = imghref

    def rewritelink(self, imghref):
        """ Intended to be overloaded if you don't store your pictures
            in a Pictures subfolder
        """
        return imghref

    def s_draw_image(self, tag, attrs):
        """ A <draw:image> becomes an <img/> element
        """
        parent = self.tagstack.stackparent()
        anchor_type = parent.get((TEXTNS,'anchor-type'))
        imghref = attrs[(XLINKNS,"href")]
        imghref = self.rewritelink(imghref)
        htmlattrs = {'alt':"", 'src':imghref }
        if anchor_type != "character":
            htmlattrs['style'] = "display: block;"
        self.emptytag('img', htmlattrs)

    def s_draw_page(self, tag, attrs):
        """ A <draw:page> is a slide in a presentation. We use a <fieldset> element in HTML.
            Therefore if you convert a ODP file, you get a series of <fieldset>s.
            Override this for your own purpose.
        """
        name = attrs.get( (DRAWNS,'name'), "NoName")
        stylename = attrs.get( (DRAWNS,'style-name'), "")
        stylename = stylename.replace(".","_")
        masterpage = attrs.get( (DRAWNS,'master-page-name'),"")
        masterpage = masterpage.replace(".","_")
        self.opentag('fieldset', {'class':"DP-%s MP-%s" % (stylename, masterpage) })
        self.opentag('legend')
        self.writeout(escape(name))
        self.closetag('legend')

    def e_draw_page(self, tag, attrs):
        self.closetag('fieldset')

    def html_body(self, tag, attrs):
        self.writedata()
        self.opentag('style', {'type':"text/css"})
        self.writeout('\nimg { width: 100%; height: 100%; }\n')
        self.writeout('* { padding: 0; margin: 0; }\n')
        self.generate_stylesheet()
        self.closetag('style')
        self.purgedata()
        self.closetag('head')
        self.opentag('body')

    def generate_stylesheet(self):
        for name in self.stylestack:
            styles = self.styledict.get(name)
            # Preload with the family's default style
            if '__style-family' in styles and styles['__style-family'] in self.styledict:
                #if styles['__style-family'] == 'p': pdb.set_trace()
                familystyle = self.styledict[styles['__style-family']].copy()
                del styles['__style-family']
                for style, val in list(styles.items()):
                    familystyle[style] = val
                styles = familystyle
            # Resolve the remaining parent styles
            while '__parent-style-name' in styles and styles['__parent-style-name'] in self.styledict:
                parentstyle = self.styledict[styles['__parent-style-name']].copy()
                del styles['__parent-style-name']
                for style, val in list(styles.items()):
                    parentstyle[style] = val
                styles = parentstyle
            self.styledict[name] = styles
        # Write the styles to HTML
        for name in self.stylestack:
            styles = self.styledict.get(name)
            css2 = self.cs.convert_styles(styles)
            self.writeout("%s {\n" % name)
            for style, val in list(css2.items()):
                self.writeout("\t%s: %s;\n" % (style, val) )
            self.writeout("}\n")

    def generate_footnotes(self):
        for key,note in list(self.notedict.items()):
            self.opentag('div')
            self.opentag('a', { 'name':"footnote-%d" % key })
            self.closetag('a')
            self.opentag('sup')
            self.writeout(escape(note['citation']))
            self.closetag('sup')
            self.writeout(escape(note['body']))
            self.closetag('div')

    def s_office_automatic_styles(self, tag, attrs):
        if self.xmlfile == 'styles.xml':
            self.autoprefix = "A"
        else:
            self.autoprefix = ""

    def s_office_document_content(self, tag, attrs):
        """ First tag in the content.xml file"""
        self.writeout('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" ')
        self.writeout('"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')
        self.opentag('html', {'xmlns':"http://www.w3.org/1999/xhtml"})
        self.opentag('head')
        self.emptytag('meta', { 'http-equiv':"Content-Type", 'content':"text/html;charset=UTF-8"})
        for metaline in self.metatags:
            self.writeout(metaline)

    def e_office_document_content(self, tag, attrs):
        """ Last tag """
        self.closetag('html')

    def s_office_presentation(self, tag, attrs):
        """ For some odd reason, OpenOffice Impress doesn't define a default-style
            for the 'paragraph'. We therefore force a standard when we see
            it is a presentation
        """
        self.styledict['p'] = {(FONS,'font-size'): "24pt" }
        self.styledict['presentation'] = {(FONS,'font-size'): "24pt" }
        self.html_body(tag, attrs)

    def e_office_presentation(self, tag, attrs):
        self.generate_footnotes()
        self.closetag('body')

    def s_office_spreadsheet(self, tag, attrs):
        self.html_body(tag, attrs)

    def e_office_spreadsheet(self, tag, attrs):
        self.generate_footnotes()
        self.closetag('body')

    def s_office_styles(self, tag, attrs):
        self.autoprefix = ""

    def s_office_text(self, tag, attrs):
        """ OpenDocument text """
        self.styledict['frame'] = { (STYLENS,'wrap'): 'parallel'}
        self.html_body(tag, attrs)

    def e_office_text(self, tag, attrs):
        self.generate_footnotes()
        self.closetag('body')

    def s_style_handle_properties(self, tag, attrs):
        """ Copy all attributes to a struct.
            We will later convert them to CSS2
        """
        for key,attr in list(attrs.items()):
            self.styledict[self.currentstyle][key] = attr


    familymap = {'frame':'frame', 'paragraph':'p', 'presentation':'presentation',
        'text':'span','section':'div',
        'table':'table','table-cell':'td','table-column':'col',
        'table-row':'tr','graphic':'graphic' }

    def s_style_default_style(self, tag, attrs):
        """ A default style is like a style on an HTML tag
        """
        family = attrs[(STYLENS,'family')]
        htmlfamily = self.familymap.get(family,'unknown')
        self.currentstyle = htmlfamily
#       self.stylestack.append(self.currentstyle)
        self.styledict[self.currentstyle] = {}

    def e_style_default_style(self, tag, attrs):
        self.currentstyle = None

    def s_style_font_face(self, tag, attrs):
        """ It is possible that the HTML browser doesn't know how to
            show a particular font. Luckily ODF provides generic fallbacks
            Unluckily they are not the same as CSS2.
            CSS2: serif, sans-serif, cursive, fantasy, monospace
            ODF: roman, swiss, modern, decorative, script, system
        """
        name = attrs[(STYLENS,"name")]
        family = attrs[(SVGNS,"font-family")]
        generic = attrs.get( (STYLENS,'font-family-generic'),"" )
        self.cs.save_font(name, family, generic)

    def s_style_page_layout(self, tag, attrs):
        """ Collect the formatting for the page layout style.
        """
        name = attrs[(STYLENS,'name')]
        name = name.replace(".","_")
        self.currentstyle = ".PL-" + name
        self.stylestack.append(self.currentstyle)
        self.styledict[self.currentstyle] = {}

    def e_style_page_layout(self, tag, attrs):
        """ End this style
        """
        self.currentstyle = None

    def s_style_master_page(self, tag, attrs):
        """ Collect the formatting for the page layout style.
        """
        name = attrs[(STYLENS,'name')]
        name = name.replace(".","_")

        self.currentstyle = ".MP-" + name
        self.stylestack.append(self.currentstyle)
        self.styledict[self.currentstyle] = {('','position'):'relative'}
        # Then load the pagelayout style if we find it
        pagelayout = attrs.get( (STYLENS,'page-layout-name'), None)
        if pagelayout:
            pagelayout = ".PL-" + pagelayout
            if pagelayout in self.styledict:
                styles = self.styledict[pagelayout]
                for style, val in list(styles.items()):
                    self.styledict[self.currentstyle][style] = val
            else:
                self.styledict[self.currentstyle]['__parent-style-name'] = pagelayout
        self.s_ignorexml(tag, attrs)

    # Short prefixes for class selectors
    familyshort = {'drawing-page':'DP', 'paragraph':'P', 'presentation':'PR',
        'text':'S', 'section':'D',
         'table':'T', 'table-cell':'TD', 'table-column':'TC',
         'table-row':'TR', 'graphic':'G' }

    def s_style_style(self, tag, attrs):
        """ Collect the formatting for the style.
            Styles have scope. The same name can be used for both paragraph and
            character styles Since CSS has no scope we use a prefix. (Not elegant)
            In ODF a style can have a parent, these parents can be chained.
            We may not have encountered the parent yet, but if we have, we resolve it.
        """
        name = attrs[(STYLENS,'name')]
        name = name.replace(".","_")
        family = attrs[(STYLENS,'family')]
        htmlfamily = self.familymap.get(family,'unknown')
        sfamily = self.familyshort.get(family,'X')
        name = "%s%s-%s" % (self.autoprefix, sfamily, name)
        parent = attrs.get( (STYLENS,'parent-style-name') )
        self.currentstyle = special_styles.get(name,"."+name)
        self.stylestack.append(self.currentstyle)
        self.styledict[self.currentstyle] = {}

        self.styledict[self.currentstyle]['__style-family'] = htmlfamily

        # Then load the parent style if we find it
        if parent:
            parent = "%s-%s" % (sfamily, parent)
            parent = special_styles.get(parent, "."+parent)
            if parent in self.styledict:
                styles = self.styledict[parent]
                for style, val in list(styles.items()):
                    self.styledict[self.currentstyle][style] = val
            else:
                self.styledict[self.currentstyle]['__parent-style-name'] = parent

    def e_style_style(self, tag, attrs):
        """ End this style
        """
        self.currentstyle = None

    def s_table_table(self, tag, attrs):
        """ Start a table
        """
        c = attrs.get( (TABLENS,'style-name'), None)
        if c:
            c = c.replace(".","_")
            self.opentag('table',{ 'class': "T-%s" % c })
        else:
            self.opentag('table')
        self.purgedata()

    def e_table_table(self, tag, attrs):
        """ End a table
        """
        self.writedata()
        self.closetag('table')
        self.purgedata()

    def s_table_table_cell(self, tag, attrs):
        #FIXME: number-columns-repeated § 8.1.3
        #repeated = int(attrs.get( (TABLENS,'number-columns-repeated'), 1))
        htmlattrs = {}
        rowspan = attrs.get( (TABLENS,'number-rows-spanned') )
        if rowspan:
            htmlattrs['rowspan'] = rowspan
        colspan = attrs.get( (TABLENS,'number-columns-spanned') )
        if colspan:
            htmlattrs['colspan'] = colspan

        c = attrs.get( (TABLENS,'style-name') )
        if c:
            htmlattrs['class'] = 'TD-%s' % c.replace(".","_")
        self.opentag('td', htmlattrs)
        self.purgedata()

    def e_table_table_cell(self, tag, attrs):
        self.writedata()
        self.closetag('td')
        self.purgedata()

    def s_table_table_column(self, tag, attrs):
        c = attrs.get( (TABLENS,'style-name'), None)
        repeated = int(attrs.get( (TABLENS,'number-columns-repeated'), 1))
        htmlattrs = {}
        if c:
            htmlattrs['class'] = "TC-%s" % c.replace(".","_")
        for x in range(repeated):
            self.emptytag('col', htmlattrs)
        self.purgedata()

    def s_table_table_row(self, tag, attrs):
        #FIXME: table:number-rows-repeated
        c = attrs.get( (TABLENS,'style-name'), None)
        htmlattrs = {}
        if c:
            htmlattrs['class'] = "TR-%s" % c.replace(".","_")
        self.opentag('tr', htmlattrs)
        self.purgedata()

    def e_table_table_row(self, tag, attrs):
        self.writedata()
        self.closetag('tr')
        self.purgedata()

    def s_text_a(self, tag, attrs):
        """ Anchors start """
        self.writedata()
        href = attrs[(XLINKNS,"href")].split("|")[0]
        self.opentag('a', {'href':href})
        self.purgedata()

    def e_text_a(self, tag, attrs):
        self.writedata()
        self.closetag('a')
        self.purgedata()

    def s_text_h(self, tag, attrs):
        """ Headings start """
        level = int(attrs[(TEXTNS,'outline-level')])
        if level > 6: level = 6 # Heading levels go only to 6 in XHTML
        if level < 1: level = 1
        self.headinglevels[level] = self.headinglevels[level] + 1
        name = self.classname(attrs)
        for x in range(level + 1,10):
            self.headinglevels[x] = 0
        special = special_styles.get("P-"+name)
        if special:
            self.opentag('h%s' % level)
        else:
            self.opentag('h%s' % level, {'class':"P-%s" % name })
        self.purgedata()

    def e_text_h(self, tag, attrs):
        """ Headings end """
        self.writedata()
        level = int(attrs[(TEXTNS,'outline-level')])
        if level > 6: level = 6 # Heading levels go only to 6 in XHTML
        if level < 1: level = 1
        lev = self.headinglevels[1:level+1]
        outline = '.'.join(map(str,lev) )
        self.opentag('a', {'name':"%s.%s" % ( outline, ''.join(self.data))} )
        self.closetag('a')
        self.closetag('h%s' % level)
        self.purgedata()

    def s_text_line_break(self, tag, attrs):
        self.writedata()
        self.emptytag('br')
        self.purgedata()

    def s_text_list(self, tag, attrs):
        """ To know which level we're at, we have to count the number
            of <text:list> elements on the tagstack.
        """
        name = attrs.get( (TEXTNS,'style-name') )
        if name:
            name = name.replace(".","_")
            level = 1
        else:
            # FIXME: If a list is contained in a table cell or text box,
            # the list level must return to 1, even though the table or
            # textbox itself may be nested within another list.
            level = self.tagstack.count_tags(tag) + 1
            name = self.tagstack.rfindattr( (TEXTNS,'style-name') )
        self.opentag('%s' % self.listtypes.get(name), {'class':"%s_%d" % (name, level) })
        self.purgedata()

    def e_text_list(self, tag, attrs):
        self.writedata()
        name = attrs.get( (TEXTNS,'style-name') )
        if name:
            name = name.replace(".","_")
            level = 1
        else:
            # FIXME: If a list is contained in a table cell or text box,
            # the list level must return to 1, even though the table or
            # textbox itself may be nested within another list.
            level = self.tagstack.count_tags(tag) + 1
            name = self.tagstack.rfindattr( (TEXTNS,'style-name') )
        self.closetag(self.listtypes.get(name))
        self.purgedata()

    def s_text_list_item(self, tag, attrs):
        self.opentag('li')
        self.purgedata()

    def e_text_list_item(self, tag, attrs):
        self.writedata()
        self.closetag('li')
        self.purgedata()

    def s_text_list_level_style_bullet(self, tag, attrs):
        name = self.tagstack.rfindattr( (STYLENS,'name') )
        self.listtypes[name] = 'ul'
        level = attrs[(TEXTNS,'level')]
        self.prevstyle = self.currentstyle
        self.currentstyle = ".%s_%s" % ( name.replace(".","_"), level)
        self.stylestack.append(self.currentstyle)
        self.styledict[self.currentstyle] = {}

        level = int(level)
        if level % 3 == 1: listtype = "disc"
        if level % 3 == 2: listtype = "circle"
        if level % 3 == 0: listtype = "square"
        self.styledict[self.currentstyle][('','list-style-type')] = listtype

    def e_text_list_level_style_bullet(self, tag, attrs):
        self.currentstyle = self.prevstyle
        del self.prevstyle

    def s_text_list_level_style_number(self, tag, attrs):
        name = self.tagstack.stackparent()[(STYLENS,'name')]
        self.listtypes[name] = 'ol'
        level = attrs[(TEXTNS,'level')]
        num_format = attrs.get( (STYLENS,'name'),"1")
        self.prevstyle = self.currentstyle
        self.currentstyle = ".%s_%s" % ( name.replace(".","_"), level)
        self.stylestack.append(self.currentstyle)
        self.styledict[self.currentstyle] = {}
        if   num_format == "1": listtype = "decimal"
        elif num_format == "I": listtype = "upper-roman"
        elif num_format == "i": listtype = "lower-roman"
        elif num_format == "A": listtype = "upper-alpha"
        elif num_format == "a": listtype = "lower-alpha"
        else: listtype = "decimal"
        self.styledict[self.currentstyle][('','list-style-type')] = listtype

    def e_text_list_level_style_number(self, tag, attrs):
        self.currentstyle = self.prevstyle
        del self.prevstyle

    def s_text_note(self, tag, attrs):
        self.currentnote = self.currentnote + 1
        self.notedict[self.currentnote] = {}
        self.notebody = []

    def e_text_note(self, tag, attrs):
        pass

    def collectnote(self,s):
        if s != '':
            self.notebody.append(s)

    def s_text_note_body(self, tag, attrs):
        self.orgwfunc = self.wfunc
        self.wfunc = self.collectnote

    def e_text_note_body(self, tag, attrs):
        self.wfunc = self.orgwfunc
        self.notedict[self.currentnote]['body'] = ''.join(self.notebody)
        self.notebody = ''
        del self.orgwfunc

    def e_text_note_citation(self, tag, attrs):
        mark = ''.join(self.data)
        self.notedict[self.currentnote]['citation'] = mark
        self.opentag('a',{ 'href': "#footnote-%s" % self.currentnote })
        self.opentag('sup')
        self.writeout( escape(mark) )
        self.closetag('sup')
        self.closetag('a')

    def s_text_p(self, tag, attrs):
        """ Paragraph
        """
        c = attrs.get( (TEXTNS,'style-name'), None)
        htmlattrs = {}
        if c:
            c = c.replace(".","_")
            special = special_styles.get("P-"+c)
            if special is None:
                htmlattrs['class'] = "P-%s" % c
        self.opentag('p', htmlattrs)
        self.purgedata()

    def e_text_p(self, tag, attrs):
        """ End Paragraph
        """
        self.writedata()
        self.closetag('p')
        self.purgedata()

    def s_text_s(self, tag, attrs):
        """ Generate a number of spaces. ODF has an element; HTML uses &nbsp;
            We use &#160; so we can send the output through an XML parser if we desire to
        """
        c = attrs.get( (TEXTNS,'c'),"1")
        for x in range(int(c)):
            self.writeout('&#160;')

    def s_text_span(self, tag, attrs):
        """ The <text:span> element matches the <span> element in HTML. It is
            typically used to properties of the text.
        """
        self.writedata()
        c = attrs.get( (TEXTNS,'style-name'), None)
        htmlattrs = {}
        if c:
            c = c.replace(".","_")
            special = special_styles.get("S-"+c)
            if special is None:
                htmlattrs['class'] = "S-%s" % c
        self.opentag('span', htmlattrs)
        self.purgedata()

    def e_text_span(self, tag, attrs):
        """ End the <text:span> """
        self.writedata()
        self.closetag('span')
        self.purgedata()

    def s_text_tab(self, tag, attrs):
        """ Move to the next tabstop. We ignore this in HTML
        """
        self.writedata()
        self.writeout(' ')
        self.purgedata()

    def s_text_x_source(self, tag, attrs):
        """ Various indexes and tables of contents. We ignore those.
        """
        self.writedata()
        self.purgedata()
        self.s_ignorexml(tag, attrs)

    def e_text_x_source(self, tag, attrs):
        """ Various indexes and tables of contents. We ignore those.
        """
        self.writedata()
        self.purgedata()


#-----------------------------------------------------------------------------
#
# Reading the file
#
#-----------------------------------------------------------------------------

    def odf2xhtml(self, odtfile):
        # Extract the interesting files
        z = zipfile.ZipFile(odtfile)

        parser = xml.sax.make_parser()
        parser.setFeature(handler.feature_namespaces, 1)
        parser.setContentHandler(self)
        parser.setErrorHandler(handler.ErrorHandler())
        inpsrc = InputSource()

        for xmlfile in ('meta.xml', 'styles.xml', 'content.xml'):
            self.xmlfile = xmlfile
            content = z.read(xmlfile)
            inpsrc.setByteStream(StringIO(content))
            parser.parse(inpsrc)
        z.close()
        return ''.join(self.lines)

if __name__ == "__main__":
    import sys
    odhandler = ODF2XHTML()

    result = odhandler.odf2xhtml(sys.argv[1])
    sys.stdout.write(result.encode('utf-8'))

