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

import os
import mimetypes
import Image
import tempfile
import gtk
import math
from constants import *
import sane
import tempfile
import locale
from lxml import etree

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
    dir_name = tempfile.mkdtemp(dir = temp_dir)
    debug('Converting PDF: ', pdf_file, ' to image')
    resolution = 300
    file_name = os.path.splitext(os.path.basename(pdf_file))[0]
    command = 'gs -SDEVICE=jpeg -r%(resolution)sx%(resolution)s -sPAPERSIZE=letter ' \
              '-sOutputFile="%(temp_name)s/%(file_name)s_%%04d.jpg" ' \
              '-dNOPAUSE -dBATCH -- "%(pdf_file)s"' % \
              {'temp_name': dir_name,
               'file_name': file_name,
               'pdf_file': pdf_file,
               'resolution': resolution}
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
    images.sort()
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

def getExecPath(exec_name):
    real_exec_name = None
    if os.path.isfile(exec_name) and os.access(exec_name, os.X_OK):
        real_exec_name = exec_name
    exec_base_name = os.path.basename(exec_name)
    for path in os.environ["PATH"].split(os.pathsep):
        exec_path = os.path.join(path, exec_base_name)
        if os.path.isfile(exec_path) and os.access(exec_path, os.X_OK):
            real_exec_name = exec_path
    return real_exec_name

def getUnpaperCommand(configuration_manager):
    command = '%s --layout single --overwrite ' % configuration_manager.unpaper
    if not configuration_manager.unpaper_use_black_filter:
        command += ' --no-blackfilter'
    if configuration_manager.unpaper_noise_filter_intensity == 'none':
        command += ' --no-noisefilter'
    elif configuration_manager.unpaper_noise_filter_intensity != 'auto':
        command += ' --noisefilter-intensity %s' % \
            configuration_manager.unpaper_noise_filter_intensity
    if configuration_manager.unpaper_gray_filter_size == 'none':
        command += ' --no-grayfilter'
    elif configuration_manager.unpaper_gray_filter_size != 'auto':
        command += ' --grayfilter-size %s' % \
            configuration_manager.unpaper_gray_filter_size
    command += ' %s ' % configuration_manager.unpaper_extra_options
    return command

def unpaperImage(configuration_manager, image_path):
    tmp_dir = configuration_manager.TEMPORARY_FOLDER
    prefix = os.path.splitext(image_path)[0]
    unpapered_name = os.path.join(tmp_dir, os.path.basename(prefix) + '.ppm')
    if os.path.exists(unpapered_name):
        unpapered_name = getNonExistingFileName(unpapered_name)
    image_path = Image.open(image_path)
    image_path.save(unpapered_name, format = 'PPM')
    command = getUnpaperCommand(configuration_manager)
    command += ' %s %s' % (unpapered_name, unpapered_name)
    print command
    try:
        os.system(command)
    except Exception, exception:
        debug(exception)
        return None
    return unpapered_name

def obtainScanners():
    sane.init()
    try:
        devices = sane.get_devices()
        return devices
    except (RuntimeError, sane._sane.error), msgerr:
        return None

def scan(device):
    try:
        result = sane.open(device).scan()
        filename = tempfile.mktemp(suffix='.png')
        result.save(filename, 'PNG')
        return filename
    except (RuntimeError, sane._sane.error), msgerr:
        return None

languages = {}

def getLanguages():
    global languages
    if not languages:
        lc, encoding = locale.getdefaultlocale()
        language_country = lc.split('_')
        root = etree.parse(ISO_CODES_PATH + 'iso_639.xml')
        for element in root.findall('//iso_639_entry[@iso_639_1_code]'):
            languages[element.get('iso_639_1_code')] = element.get('name')
    return languages
