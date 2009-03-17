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
import mimetypes
import tempfile
import gtk
import math
from util.constants import *
from gnome import url_show

def getIconOrLabel(icon_name, label_text, icon_size = gtk.ICON_SIZE_SMALL_TOOLBAR):
    icon = gtk.Image()
    theme = gtk.icon_theme_get_default()
    if theme.lookup_icon(icon_name, icon_size, gtk.ICON_LOOKUP_USE_BUILTIN):
        icon = gtk.image_new_from_icon_name(icon_name, icon_size)
    else:
        icon.set_from_stock(gtk.STOCK_EXECUTE, icon_size)
    label = label_text
    if icon != None:
        label = None
    return icon, label

def convertPdfToImages(pdf_file, temp_dir = '/tmp'):
    dir_name = tempfile.mkstemp(dir = temp_dir)[1]
    try:
        os.remove(dir_name)
        os.mkdir(dir_name)
    except:
        pass
    command = 'gs -SDEVICE=jpeg -r600x600 -sPAPERSIZE=letter -sOutputFile=%(temp_name)s/%(file_name)s_%%04d.jpg -dNOPAUSE -dBATCH -- %(pdf_file)s' % {'temp_dir': temp_dir, 'temp_name': dir_name, 
                                                                                                                                                      'file_name': os.path.basename(dir_name), 'pdf_file': pdf_file}
    os.popen(command)
    return dir_name

def getImagesFromFolder(folder):
    if not os.path.isdir(folder):
        return []
    content = os.listdir(folder)
    images = []
    for item in content:
        item = os.path.join(folder, item)
        mime_type = mimetypes.guess_type(item)[0]
        if mime_type:
            type, detail = mime_type.split('/')
            if type == 'image' and not detail.startswith('svg'):
                images.append(item)
    return images

def getDictFromVariables(variable_list, instance):
    dictionary = {}
    for variable in variable_list:
        dictionary[variable] = eval('instance.%s' % variable)
    return dictionary

def getNonExistingFileName(file_name):
    
    if not os.path.exists(file_name):
        return file_name
    name, ext = os.path.splitext(file_name)
    i = 1
    while os.path.exists(name + str(i) + ext) and i < 500:
        i += 1
    return name + str(i) + ext

def openUrl(widget, url, data):
    url_show(url)

def getStandardDeviation(list_of_values):
    if not list_of_values:
        return 0
    number_of_values = len(list_of_values)
    average = sum(list_of_values) / float(number_of_values)
    op_list = []
    for i in list_of_values:
        op_list.append((i - average) ** 2)
    new_average = sum(op_list) / float(number_of_values)
    return math.sqrt(new_average)

def debug(*args):
    if OCRFEEDER_DEBUG:
        print 'OCRFEEDER DEBUG :::::: ', args
