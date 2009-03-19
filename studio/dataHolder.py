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

import os.path
from util import graphics
import Image
import gobject
from util.graphics import getImagePrintSize, getImageResolution
from util import TEXT_TYPE, IMAGE_TYPE, ALIGN_LEFT, lib
from pango import WEIGHT_NORMAL, STYLE_NORMAL
    
class TextData:
    
    def __init__(self, face = 'Sans', size = 12, justification = ALIGN_LEFT, line_space = 0, letter_space = 0, style = STYLE_NORMAL, weight = WEIGHT_NORMAL):
        self.face = face
        self.size = size
        self.line_space = line_space
        self.letter_space = letter_space
        self.justification = justification
        self.style = style
        self.weight = weight
        self.angle = 0
    
    def convertToDict(self):
        dictionary = lib.getDictFromVariables(['face', 'size', 'line_space', 
                                               'letter_space', 'justification', 'angle'], self)
        dictionary['style'] = repr(self.style).split(' ')[1].strip('PANGO_')
        dictionary['weight'] = repr(self.weight).split(' ')[1].strip('PANGO_')
        return {'TextData': dictionary}

class DataBox(gobject.GObject):
    
    __gtype_name__ = 'DataBox'
    
    __gsignals__ = {
        'changed_x' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_INT,)),
        'changed_y' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_INT,)),
        'changed_width' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_INT,)),
        'changed_height' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_INT,)),
        'changed_image' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,)),
        'changed_type' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_INT,))
        }
    
    def __init__(self, x = 0, y = 0, width = 0, height = 0, image = None, type = TEXT_TYPE, text = None):
        super(DataBox, self).__init__()
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.image = image
        self.setType(type)
        self.text_data = TextData()
        self.text = text
    
    def configTextData(self, face = 'Sans', size = 12, justification = ALIGN_LEFT, line_space = 1, letter_space = 1):
        self.text_data = TextData(face, size, justification, line_space, letter_space)
    
    def setX(self, new_x):
        self.x = new_x
        self.emit('changed_x', self.x)
    
    def setY(self, new_y):
        self.y = new_y
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
    
    
def create_images_dict_from_liststore(list_store):
    images_dict = {}
    iter = list_store.get_iter_root()
    while iter != None:
        pixbuf = list_store.get_value(iter, 2)
        image_path = list_store.get_value(iter, 0)
        images_dict[pixbuf] = image_path
        iter = list_store.iter_next(iter)
    return images_dict