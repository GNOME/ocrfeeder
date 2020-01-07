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

import os.path
from ocrfeeder.util import graphics
from PIL import Image
from gi.repository import GObject, Pango
from ocrfeeder.util.graphics import getImagePrintSize, getImageResolution
from ocrfeeder.util import TEXT_TYPE, IMAGE_TYPE, ALIGN_LEFT, lib

class TextData:

    def __init__(self, face = 'Sans', size = 12, justification = ALIGN_LEFT,
                 line_space = 0, letter_space = 0, style = Pango.Style.NORMAL,
                 weight = Pango.Weight.NORMAL, language = ''):
        self.face = face
        self.size = size
        self.line_space = line_space
        self.letter_space = letter_space
        self.justification = justification
        self.style = style
        self.weight = weight
        self.angle = 0
        self.language = language

    def convertToDict(self):
        dictionary = lib.getDictFromVariables(['face', 'size', 'line_space',
                                               'letter_space', 'justification', 'angle', 'language'], self)
        dictionary['style'] = repr(self.style).split(' ')[1].strip('PANGO_')
        dictionary['weight'] = repr(self.weight).split(' ')[1].strip('PANGO_')
        return {'TextData': dictionary}

class DataBox(GObject.GObject):

    __gtype_name__ = 'DataBox'

    __gsignals__ = {
        'changed_x' : (GObject.SIGNAL_RUN_LAST,
                     GObject.TYPE_NONE,
                     (GObject.TYPE_INT,)),
        'changed_y' : (GObject.SIGNAL_RUN_LAST,
                     GObject.TYPE_NONE,
                     (GObject.TYPE_INT,)),
        'changed_width' : (GObject.SIGNAL_RUN_LAST,
                     GObject.TYPE_NONE,
                     (GObject.TYPE_INT,)),
        'changed_height' : (GObject.SIGNAL_RUN_LAST,
                     GObject.TYPE_NONE,
                     (GObject.TYPE_INT,)),
        'changed_image' : (GObject.SIGNAL_RUN_LAST,
                     GObject.TYPE_NONE,
                     (GObject.TYPE_PYOBJECT,)),
        'changed_type' : (GObject.SIGNAL_RUN_LAST,
                     GObject.TYPE_NONE,
                     (GObject.TYPE_INT,))
        }

    def __init__(self, x = 0, y = 0, width = 0, height = 0, image = None, type = TEXT_TYPE, text = ''):
        super(DataBox, self).__init__()
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.image = image
        self.setType(type)
        self.text_data = TextData()
        self.setText(text)

    def configTextData(self, face = 'Sans', size = 12, justification = ALIGN_LEFT, line_space = 1, letter_space = 1):
        self.text_data = TextData(face, size, justification, line_space, letter_space)

    def setX(self, new_x):
        self.x = max(0, new_x)
        self.emit('changed_x', self.x)

    def setY(self, new_y):
        self.y = max(0, new_y)
        self.emit('changed_y', self.y)

    def setWidth(self, new_width):
        self.width = new_width
        self.emit('changed_width', self.width)

    def setHeight(self, new_height):
        self.height = new_height
        self.emit('changed_height', self.height)

    def setImage(self, pixbuf):
        self.image = graphics.convertPixbufToImage(pixbuf)
        self.emit('changed_image', pixbuf)

    def setType(self, new_type):
        self.type = new_type
        self.emit('changed_type', self.type)

    def getType(self):
        return self.type

    def toogleType(self):
        if self.type == TEXT_TYPE:
            self.setType(IMAGE_TYPE)
        else:
            self.setType(TEXT_TYPE)

    def setFontFace(self, font_face):
        self.text_data.face = font_face

    def setFontSize(self, font_size):
        self.text_data.size = font_size

    def setFontStyle(self, font_style):
        self.text_data.style = font_style

    def setFontWeight(self, font_weight):
        self.text_data.weight = font_weight

    def setText(self, text):
        self.text = text

    def getText(self):
        return self.text

    def setAngle(self, angle):
        self.text_data.angle = angle

    def getAngle(self):
        return self.text_data.angle

    def setTextAlign(self, align_option):
        self.text_data.justification = align_option

    def setLetterSpacing(self, spacing):
        self.text_data.letter_space = spacing

    def setLineSpacing(self, spacing):
        self.text_data.line_space = spacing

    def setLanguage(self, language):
        self.text_data.language = language

    def getLanguage(self):
        return self.text_data.language

    def getLetterSpacing(self):
        return self.text_data.letter_space

    def getLineSpacing(self):
        return self.text_data.line_space

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def getWidth(self):
        return self.width

    def getHeight(self):
        return self.height

    def getBoundsPrintSize(self, resolution):
        x_resolution, y_resolution = float(resolution[0]), float(resolution[1])
        x, y, width, height = self.getX(), self.getY(), \
                                self.getWidth(), self.getHeight()
        return x / x_resolution, y / y_resolution, width / x_resolution, height / y_resolution

    def convertToDict(self):
        dictionary = lib.getDictFromVariables(['x', 'y', 'width',
                                               'height',  'type', 'text'], self)
        dictionary['text_data'] = self.text_data.convertToDict()
        return {'DataBox': dictionary}

    def updateBoundsFromBox(self, box):
        x, y, width, height = int(box.props.x), int(box.props.y), \
                              int(box.props.width), int(box.props.height)
        self.setX(x)
        self.setY(y)
        self.setWidth(width)
        self.setHeight(height)
        return (x, y, width, height)

    def updateImage(self, pixbuf):
        pixbuf_width = pixbuf.get_width()
        pixbuf_height = pixbuf.get_height()
        sub_pixbuf = pixbuf.new_subpixbuf(self.x, self.y,
                                          min(self.width, pixbuf_width),
                                          min(self.height, pixbuf_height))
        sub_pixbuf.x = self.x
        sub_pixbuf.y = self.y
        sub_pixbuf.width = pixbuf_width
        self.setImage(sub_pixbuf)


class PageData:

    def __init__(self, image_path, data_boxes = []):
        image = Image.open(image_path)
        self.pixel_width, self.pixel_height = image.size
        self.image_path = image_path
        self.setSize(getImagePrintSize(image))
        self.resolution = getImageResolution(image)
        self.data_boxes = data_boxes

    def setSize(self, page_size):
        self.width, self.height = page_size
        self.resolution = self.pixel_width / self.width, self.pixel_height / self.height

    def setResolution(self, new_resolution):
        self.resolution = new_resolution

    def convertToDict(self):
        dictionary = lib.getDictFromVariables(['pixel_width', 'pixel_height', 'image_path', 'resolution'], self)
        data_boxes_converted = [data_box.convertToDict() for data_box in self.data_boxes]
        dictionary['data_boxes'] = data_boxes_converted
        return {'PageData': dictionary}

    def getTextFromBoxes(self, data_boxes=None):
        text = ''
        if data_boxes is None:
            data_boxes = self.data_boxes
        number_of_boxes = len(data_boxes)
        for i in range(number_of_boxes):
            data_box = data_boxes[i]
            if data_box and data_box.getType() != TEXT_TYPE:
                continue
            text += data_box.getText()
            if number_of_boxes > 1 and i < number_of_boxes - 1:
                text += '\n\n'
        return text

def create_images_dict_from_liststore(list_store):
    images_dict = {}
    iter = list_store.get_iter_root()
    while iter != None:
        pixbuf = list_store.get_value(iter, 2)
        image_path = list_store.get_value(iter, 0)
        images_dict[pixbuf] = image_path
        iter = list_store.iter_next(iter)
    return images_dict
