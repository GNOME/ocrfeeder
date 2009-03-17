# -*- coding: utf-8 -*-

###########################################################################
#    OCRFeeder - The complete OCR suite
#    Copyright (C) 2009 Joaquim Rocha
# 
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###########################################################################

from odf.draw import Frame, TextBox, Image
from odf.opendocument import OpenDocumentText
from odf.style import Style, MasterPage, GraphicProperties, ParagraphProperties, \
    TextProperties, PageLayout, PageLayoutProperties
from odf.text import P, Page, PageSequence
from pango import WEIGHT_BOLD, WEIGHT_NORMAL, STYLE_ITALIC, STYLE_NORMAL, \
    STYLE_OBLIQUE
from util import TEXT_TYPE, IMAGE_TYPE, ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER, \
    ALIGN_FILL
from util.graphics import getImagePrintSize
from util.lib import debug
import math
import os.path
import shutil
import tempfile

class DocumentGenerator:
    
    def __init__(self):
        self.document = self.makeDocument()
    
    def makeDocument(self):
        raise NotImplementedError('Method not defined!')
    
    def addBox(self, data_box):
        if data_box.getType() == TEXT_TYPE:
            self.addText(data_box)
        elif data_box.getType() == IMAGE_TYPE:
            self.addImage(data_box)
    
    def addText(self, data_box):
        raise NotImplementedError('Method not defined!')
    
    def addImage(self, data_box):
        raise NotImplementedError('Method not defined!')
    
    def addBoxes(self, data_boxes):
        for data_box in data_boxes:
            self.addBox(data_box)
    
    def save(self):
        raise NotImplementedError('Method not defined!')
    
    def newPage(self):
        raise NotImplementedError('Method not defined!')
    
    def convertFontStyle(self, style):
        raise NotImplementedError('Method not defined!')
    
    def convertFontWeight(self, weight):
        raise NotImplementedError('Method not defined!')
    
    def convertTextAlign(self, align):
        if align == ALIGN_LEFT:
            return 'left'
        elif align == ALIGN_RIGHT:
            return 'right'
        elif align == ALIGN_CENTER:
            return 'center'
        elif align == ALIGN_FILL:
            return 'justified'

class PdfGenerator(DocumentGenerator):
    
    def __init__(self, name, image_path):
        width, height = getImagePrintSize(image_path)
        self.document = canvas.Canvas(name, pagesize = (width * inch, height * inch))
    
    def addText(self, data_box):
        text = data_box.getText()
        text_object = self.document.beginText()
        text_object.setTextOrigin(data_box.x, data_box.y)
        text_object.setFont('Times-Roman', data_box.text_data.size)
        text_object.moveCursor(0, data_box.text_data.size)
        text_object.textLines(text)
        self.document.drawText(text_object)
    
    def addImage(self, data_box):
        pass
    
    def save(self):
        self.document.save()
    
    def newPage(self):
        self.document.showPage()

class HtmlGenerator(DocumentGenerator):
    
    def __init__(self, name):
        self.name = name
        self.document = ''
        self.bodies = []
        self.styles = ''
        self.style_names = []
        self.images = []
    
    def addText(self, data_box):
        text_lines = data_box.getText().splitlines()
        new_div = '''
<div style="position: absolute; margin-left: %(x)spx; margin-top: %(y)spx;">
    <p class="%(class)s">%(text)s</p>
</div>
''' % {'class': self.__handleStyle(data_box.text_data), 'text': '<br/>'.join(text_lines), 'x': data_box.x, 'y': data_box.y}
        self.bodies[-1] += new_div
    
    def addImage(self, data_box):
        format = 'PNG'
        image_file = tempfile.mkstemp(suffix = '.' + format.lower())[1]
        data_box.image.save(image_file, format = format)
        self.images.append(image_file)
        new_div = '''
<div style="position: absolute; margin-left: %(x)spx; margin-top: %(y)spx;">
    <img src="images/%(image)s" alt="%(image)s" />
</div>
''' % {'image': os.path.basename(image_file), 'x': data_box.x, 'y': data_box.y}
        self.bodies[-1] += new_div
    
    def __handleStyle(self, text_data):
        style_name = 'style%s%s%s%s%s%s%s' % (text_data.face, text_data.size, text_data.line_space, 
                                        text_data.letter_space, text_data.justification, 
                                        text_data.weight, text_data.style)
        if not style_name in self.style_names:
            self.style_names.append(style_name)
            self.styles += '''

.%(style_name)s {
    font-family: %(face)s;
    font-size: %(size)spt;
    font-weight: %(weight)s;
    font-style: %(style)s;
    text-align: %(align)s;
    letter-spacing: %(letter_space)spt;
    line-height: %(line_space)spt;
}
''' % {'style_name':style_name, 'face': text_data.face,
       'size': text_data.size, 'weight': self.convertFontWeight(text_data.weight),
       'align': text_data.justification, 'style': self.convertFontStyle(text_data.style),
       'line_space': text_data.line_space, 'letter_space': text_data.letter_space}
        
        return style_name
    
    def convertFontStyle(self, style):
        if style == STYLE_OBLIQUE:
            return 'oblique'
        elif style == STYLE_ITALIC:
            return 'italic'
        return 'normal'
    
    def convertFontWeight(self, weight):
        if weight == WEIGHT_BOLD:
            return 'bold'
        return 'normal'
    
    def addPage(self, page_data):
        self.bodies.append('')
        self.current_page_resolution = page_data.resolution
        self.addBoxes(page_data.data_boxes)
    
    def save(self):
        pages = []
        for i in xrange(len(self.bodies)):
            previous_page = ''
            next_page = ''
            if i != 0:
                if i - 1 == 0:
                    previous_page = '<a href="index.html">&laquo;</a>'
                else:
                    previous_page = '<a href="page%s.html">&laquo;</a>' % (i)
            elif i != len(self.bodies) - 1:
                next_page = '<a href="page%s.html">&raquo;</a>' % (i + 2)
            pages.append('''
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>%(title)s</title>
        <link rel="stylesheet" type="text/css" href="style.css" />
    </head>
    <body>
        <div style="margin-left: auto; margin-right: auto; width: 800px; overflow: hidden;">
            <div style="float: left;">
                %(previous_page)s
            </div>
            <div style="float: right;">
                %(next_page)s
            </div>
        </div>
        <hr/>
        %(body)s
    </body>
</html>
''' % {'title': self.name, 'body': self.bodies[i], 'previous_page': previous_page, 'next_page': next_page} 
        )
        if not os.path.isdir(self.name):
            os.mkdir(self.name)
        images_folder = os.path.join(self.name, 'images')
        if not os.path.exists(images_folder):
            os.mkdir(images_folder)
        if pages:
            file = open(os.path.join(self.name, 'index.html'), 'w')
            file.write(pages[0])
            file.close()
            if len(pages) > 1:
                for i in xrange(1, len(pages)):
                    file = open(os.path.join(self.name, 'page%s.html' % (i + 1)), 'w')
                    file.write(pages[i])
                    file.close()
        if self.styles:
            file = open(os.path.join(self.name, 'style.css'), 'w')
            file.write(self.styles)
            file.close()
        for image in self.images:
            shutil.move(image, images_folder)

class OdtGenerator(DocumentGenerator):
    
    def __init__(self, name):
        self.name = name
        self.document = OpenDocumentText()
        self.current_page = None
        self.photo_style = Style(name="Photo", family="graphic")
        self.document.styles.addElement(self.photo_style)
        self.font_styles = []
        self.page_layouts = []
        self.page_masters = []
        self.page_styles = []
        frame_style = Style(name='FrameStyle', family = 'graphic')
        frame_style.addElement(GraphicProperties(borderlinewidth='none'))
        self.document.styles.addElement(frame_style)
        frame_style_rotated = Style(name='FrameStyleRotated', family = 'graphic')
        frame_style_rotated.addElement(GraphicProperties(fill = 'none', stroke = 'none', verticalpos = 'from-top', verticalrel = 'paragraph'))
        self.document.automaticstyles.addElement(frame_style_rotated)
        
    def addText(self, data_box):
        text = data_box.getText()
        frame_style = Style(name='FrameStyle', family = 'graphic')
        debug('Angle: ', data_box.text_data.angle)
        angle = data_box.text_data.angle
        if angle:
            frame_style = Style(name='FrameStyleRotated', family = 'graphic')
        x, y, width, height = data_box.getBoundsPrintSize(self.current_page_resolution)
        frame = Frame(stylename = frame_style, width = str(width) + 'in', height = str(height) + 'in', x = str(x) + 'in', y = str(y) + 'in', anchortype = 'paragraph')
        if angle:
            frame.addAttribute('transform', 'rotate (%s) translate (%scm %scm)' % (abs(math.radians(angle)), x, y))
        self.current_page.addElement(frame)
        textbox = TextBox()
        frame.addElement(textbox)
        for line in text.split('\n'):
            textbox.addElement(P(stylename = self.__handleFrameStyle(data_box.text_data), text = line))
    
    def addImage(self, data_box):
        format = 'PNG'
        image_file = tempfile.mkstemp(suffix = '.' + format)[1]
        data_box.image.save(image_file, format = format)
        x, y, width, height = data_box.getBoundsPrintSize(self.current_page_resolution)
        photo_frame = Frame(stylename=self.photo_style, x = '%sin' % x, y = '%sin' % y, width = '%sin' % width, height = '%sin' % height, anchortype='paragraph')
        self.current_page.addElement(photo_frame)
        location = self.document.addPicture(image_file)
        photo_frame.addElement(Image(href=location))
    
    def newPage(self, page_data):
        master_name = self.__handlePageMaster(page_data)
        page_style_name = '%sPage' % master_name
        if not page_style_name in self.page_styles:
            page_style = Style(name = page_style_name, family = 'paragraph', masterpagename = master_name)
            page_style.addElement(ParagraphProperties(breakbefore = 'page'))
            self.document.automaticstyles.addElement(page_style)
        new_page = P(stylename = page_style_name)
        self.document.text.addElement(new_page)
        return new_page
    
    def addPage(self, page_data):
        self.current_page = self.newPage(page_data)
        self.current_page_resolution = page_data.resolution
        self.addBoxes(page_data.data_boxes)
    
    def save(self):
        name = self.name
        if not name.lower().endswith('.odt'):
            name += '.odt'
        self.document.save(name)
    
    def __handlePageMaster(self, page_data):
        layout_name = 'Page%s%s' % (page_data.width, page_data.height)
        if not layout_name in self.page_layouts:
            page_layout = PageLayout(name = layout_name)
            page_layout.addElement(PageLayoutProperties(margintop = '0in', marginbottom = '0in', marginleft = '0in', marginright = '0in', pagewidth = '%sin' % page_data.width, pageheight = '%sin' % page_data.height))
            self.document.automaticstyles.addElement(page_layout)
            self.page_layouts.append(layout_name)
        master_name = layout_name + 'Master'
        if not master_name in self.page_masters:
            master_page = MasterPage(name = master_name, pagelayoutname = layout_name)
            self.document.masterstyles.addElement(master_page)
            self.page_masters.append(master_name)
        return master_name
    
    def __handleFrameStyle(self, text_data):
        style_name = 'box%s%s%s%s%s' % (text_data.face, text_data.size, text_data.line_space, 
                                        text_data.letter_space, text_data.justification)
        if not style_name in self.font_styles:
            frame_style = Style(name = style_name, family = 'paragraph')
            frame_style.addElement(ParagraphProperties(linespacing = '%spt' % text_data.line_space, textalign = self.convertTextAlign(text_data.justification)))
            frame_style.addElement(TextProperties(letterspacing = '%spt' % text_data.letter_space, fontstyle = self.convertFontStyle(text_data.style), fontweight = self.convertFontWeight(text_data.weight), fontsize = '%spt' % text_data.size, fontfamily = str(text_data.face)))
            self.document.styles.addElement(frame_style)
            self.font_styles.append(style_name)
        return style_name
    
    def __handleFrameStyleRotated(self, text_data):
        style_name = 'box%s%s%s%s%sRotated' % (text_data.face, text_data.size, text_data.line_space, 
                                        text_data.letter_space, text_data.justification)
        if not style_name in self.font_styles:
            frame_style = Style(name = style_name, family = 'paragraph')
            frame_style.addElement(ParagraphProperties(linespacing = '%spt' % text_data.line_space, textalign = self.convertTextAlign(text_data.justification)))
            frame_style.addElement(TextProperties(letterspacing = '%spt' % text_data.letter_space, fontstyle = self.convertFontStyle(text_data.style), fontweight = self.convertFontWeight(text_data.weight), fontsize = '%spt' % text_data.size, fontfamily = str(text_data.face)))
            self.document.automaticstyles.addElement(frame_style)
            self.font_styles.append(style_name)
        return style_name
    
    def convertFontStyle(self, style):
        if style == STYLE_OBLIQUE:
            return 'oblique'
        elif style == STYLE_ITALIC:
            return 'italic'
        return 'normal'
    
    def convertFontWeight(self, weight):
        if weight == WEIGHT_BOLD:
            return 'bold'
        return 'normal'