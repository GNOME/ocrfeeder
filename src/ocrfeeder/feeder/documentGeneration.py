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

from ocrfeeder.odf.draw import Frame, TextBox, Image
from ocrfeeder.odf.opendocument import OpenDocumentText
from ocrfeeder.odf.style import Style, MasterPage, GraphicProperties, ParagraphProperties, \
    TextProperties, PageLayout, PageLayoutProperties
from ocrfeeder.odf.text import P, Page, PageSequence
from ocrfeeder.util import TEXT_TYPE, IMAGE_TYPE, ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER, \
    ALIGN_FILL
from ocrfeeder.util.configuration import ConfigurationManager
from ocrfeeder.util.graphics import getImagePrintSize
from ocrfeeder.util.log import debug
from gi.repository import Pango
from reportlab.pdfgen import canvas
from reportlab.lib import units
from reportlab.lib.utils import ImageReader, simpleSplit
import math
import os.path
import shutil
import tempfile

class DocumentGeneratorManager(object):

    GENERATORS = {}

    def __init__(self):
        pass

    def register(self, id, generator):
        self.GENERATORS[id] = generator

    def get(self, id):
        return self.GENERATORS.get(id)

    def getFormats(self):
        return list(self.GENERATORS.keys())

class DocumentGenerator(object):

    def __init__(self):
        pass

    def makeDocument(self):
        raise NotImplementedError('Method not defined!')

    def addBox(self, data_box):
        print(data_box)
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
        image_file = tempfile.mkstemp(dir = ConfigurationManager.TEMPORARY_FOLDER,
                                      suffix = '.' + format.lower())[1]
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
        if style == Pango.Style.OBLIQUE:
            return 'oblique'
        elif style == Pango.Style.ITALIC:
            return 'italic'
        return 'normal'

    def convertFontWeight(self, weight):
        if weight == Pango.Weight.BOLD:
            return 'bold'
        return 'normal'

    def addPage(self, page_data):
        self.bodies.append('')
        self.current_page_resolution = page_data.resolution
        self.addBoxes(page_data.data_boxes)

    def save(self):
        pages = []
        for i in range(len(self.bodies)):
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
            file.write(pages[0].encode('utf-8'))
            file.close()
            if len(pages) > 1:
                for i in range(1, len(pages)):
                    file = open(os.path.join(self.name, 'page%s.html' % (i + 1)), 'w')
                    file.write(pages[i].encode('utf-8'))
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
        self.temp_images = []
        frame_style = Style(name='FrameStyle', family = 'graphic')
        frame_style.addElement(GraphicProperties(borderlinewidth='none'))
        self.document.styles.addElement(frame_style)
        frame_style_rotated = Style(name='FrameStyleRotated', family = 'graphic')
        frame_style_rotated.addElement(GraphicProperties(fill = 'none', stroke = 'none', verticalpos = 'from-top', verticalrel = 'paragraph'))
        self.document.automaticstyles.addElement(frame_style_rotated)

    def addText(self, data_box):
        text = data_box.getText()
        frame_style = Style(name='FrameStyle', family = 'graphic')
        debug('Angle: %s' % data_box.text_data.angle)
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
        image_file = tempfile.mkstemp(dir = ConfigurationManager.TEMPORARY_FOLDER,
                                      suffix = '.' + format)[1]
        data_box.image.save(image_file, format = format)
        x, y, width, height = data_box.getBoundsPrintSize(self.current_page_resolution)
        photo_frame = Frame(stylename=self.photo_style, x = '%sin' % x, y = '%sin' % y, width = '%sin' % width, height = '%sin' % height, anchortype='paragraph')
        self.current_page.addElement(photo_frame)
        location = self.document.addPicture(image_file)
        photo_frame.addElement(Image(href=location))
        self.temp_images.append(image_file)

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
        for image in self.temp_images:
            try:
                os.unlink(image)
            except:
                debug('Error removing image: %s' % image)

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
        if style == Pango.Style.OBLIQUE:
            return 'oblique'
        elif style == Pango.Style.ITALIC:
            return 'italic'
        return 'normal'

    def convertFontWeight(self, weight):
        if weight == Pango.Weight.BOLD:
            return 'bold'
        return 'normal'

# Generates a .txt file
class PlaintextGenerator(DocumentGenerator):
    def __init__(self, name):
        self.name = name
        self.text = ''

    def addText(self, newText):
        self.text += newText

    def addPage(self, page):
        self.addText(page.getTextFromBoxes())

    def save(self):
        try:
            # This will create a new file or **overwrite an existing file
            f = open(self.name, "w")
            try:
                f.write(self.text.encode('utf-8'))
            finally:
                f.close() # Close the file
        except IOError:
            pass

class PdfGenerator(DocumentGenerator):

    def __init__(self, name, from_scratch = False):
        self.name = name
        self._from_scratch = from_scratch
        self.canvas = canvas.Canvas(self.name)
        self.page_data = None

    def addText(self, box):
        x, y, width, height = box.getBoundsPrintSize(self.page_data.resolution)
        text = self.canvas.beginText()
        # Make the text transparent if we are not
        # creating a PDF from scratch
        if not self._from_scratch:
            text.setTextRenderMode(3)
        text.setTextOrigin(x * units.inch,
                           (self.page_data.height - y) * units.inch)
        text.setCharSpace(box.text_data.letter_space)
        text.setLeading(box.text_data.line_space + box.text_data.size)
        text.moveCursor(0, box.text_data.size)
        #todo: efficiently add the required font
        self.canvas.setFontSize(box.text_data.size)
        if not box.text:
            return
        lines = simpleSplit(box.text,
                            self.canvas._fontname,
                            box.text_data.size,
                            box.width)
        text.textLines('\n'.join(lines))
        self.canvas.drawText(text)

    def addImage(self, box):
        # Do nothing as the images will be already
        # seen in the PDF
        if not self._from_scratch:
            return
        x, y, width, height = box.getBoundsPrintSize(self.page_data.resolution)
        self.canvas.drawInlineImage(box.image,
                                    x * units.inch,
                                    (self.page_data.height - (y + height)) * \
                                        units.inch,
                                    width * units.inch,
                                    height * units.inch)

    def addPage(self, page_data):
        self.canvas.setPageSize((page_data.width * units.inch,
                                 page_data.height * units.inch))
        self.page_data = page_data
        # Paste the source image that users will read
        # in the PDF
        if not self._from_scratch:
            image = ImageReader(page_data.image_path)
            self.canvas.drawImage(image, 0, 0,
                                  page_data.width * units.inch,
                                  page_data.height * units.inch)
        self.addBoxes(page_data.data_boxes)
        self.canvas.showPage()

    def save(self):
        self.canvas.save()

class MarkdownGenerator(DocumentGenerator):
    def __init__(self, name):
        self.name = name
        self.document = ''
        self.images = []
        self.text = []
        self.image_counter = 1

    def addPage(self, page):
        self.addBoxes(page.data_boxes)

    def addText(self, data_box):
        self.text.append(data_box.getText())

    def addImage(self, data_box):
        format = 'PNG'
        image_file = tempfile.mkstemp(dir = ConfigurationManager.TEMPORARY_FOLDER,
                                      suffix = '.' + format.lower())[1]
        data_box.image.save(image_file, format = format)
        self.images.append(image_file)
        alt_text = "Image " + str(self.image_counter)
        self.text.append(str('![%s](%s) "%s")\n' % (alt_text, image_file, alt_text)))
        self.image_counter += 1

    def save(self):
        if not os.path.isdir(self.name):
            os.mkdir(self.name)
        images_folder = os.path.join(self.name, 'images')
        if not os.path.exists(images_folder):
            os.mkdir(images_folder)
        for image in self.images:
            shutil.move(image, images_folder)
        with open(os.path.join(self.name, 'document.md'), 'w') as fle:
            for line in self.text:
                try:
                    fle.write(line)
                except:
                    print('could not write')
                    print(line)

manager = DocumentGeneratorManager()
manager.register('HTML', HtmlGenerator)
manager.register('ODT', OdtGenerator)
manager.register('TXT', PlaintextGenerator)
manager.register('PDF', PdfGenerator)
manager.register('MD', MarkdownGenerator)
