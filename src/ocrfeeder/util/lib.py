###########################################################################
#    OCRFeeder - The complete OCR suite
#    Copyright (C) 2013 Joaquim Rocha <me@joaquimrocha.com>
#    Copyright (C) 2009-2012 Igalia, S.L.
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

import math
import mimetypes
import os
import re
import shlex
import subprocess
import tempfile
import xml.etree.ElementTree as etree

import sane
from gi.repository import Gtk
from PIL import Image

from .constants import *
from .log import debug


def getIconOrLabel(icon_name, label_text, icon_size = Gtk.IconSize.SMALL_TOOLBAR):
    icon = Gtk.Image()
    theme = Gtk.IconTheme.get_default()
    if theme.lookup_icon(icon_name, icon_size, Gtk.IconLookupFlags.USE_BUILTIN):
        icon = Gtk.Image.new_from_icon_name(icon_name, icon_size)
    else:
        icon.set_from_stock(Gtk.STOCK_EXECUTE, icon_size)
    label = label_text
    if icon != None:
        label = None
    return icon, label

def getSafeGhostscriptPath(file_path):
    return re.sub(r'[^\w !#$%&()*+,./:;<=>?@\[\\\]^_`{|}~-]', '_', file_path)

def getSafeGhostscriptOutputBasename(file_name):
    return re.sub(r'[%]', '_', getSafeGhostscriptPath(file_name))

def convertPdfToImages(pdf_file, temp_dir = '/tmp'):
    if not os.path.isfile(pdf_file):
        debug('Unable to convert PDF: File does not exist: %s', pdf_file)
        return None
    try:
        dir_name = tempfile.mkdtemp(dir = temp_dir)
    except:
        debug('Unable to convert PDF: Cannot create temp dir in: %s', temp_dir)
        return None

    debug('Converting PDF: %s to image', pdf_file)

    file_name = os.path.basename(pdf_file)
    base_name = os.path.splitext(file_name)[0]
    # GhostScript will interpret the '%' character, which is allowed
    # in Unix file names, so we need to escape it
    base_name_safe = getSafeGhostscriptOutputBasename(base_name)

    runGhostscript(dir_name, base_name_safe, pdf_file)

    return dir_name

def runGhostscript(dir_name, base_name, pdf_path, format = 'jpeg', resolution = 300, size = 'letter'):
    command = [
        'gs',
        f'-SDEVICE={format}',
        f'-r{resolution}x{resolution}',
        f'-sPAPERSIZE={size}',
        f'-sOutputFile={dir_name}/{base_name}_%04d.jpg',
        '-dNOPAUSE',
        '-dBATCH',
        '--',
        pdf_path
    ]
    subprocess.run(command)

def getImagesFromFolder(folder):
    if folder is None:
        return []
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
    command = [
        configuration_manager.unpaper,
        '--layout', 'single',
        '--overwrite',
    ]
    if not configuration_manager.unpaper_use_black_filter:
        command.append('--no-blackfilter')
    if configuration_manager.unpaper_noise_filter_intensity == 'none':
        command.append('--no-noisefilter')
    elif configuration_manager.unpaper_noise_filter_intensity != 'auto':
        command += ['--noisefilter-intensity', configuration_manager.unpaper_noise_filter_intensity]
    if configuration_manager.unpaper_gray_filter_size == 'none':
        command.append('--no-grayfilter')
    elif configuration_manager.unpaper_gray_filter_size != 'auto':
        command += ['--grayfilter-size', configuration_manager.unpaper_gray_filter_size]
    extra_options = configuration_manager.unpaper_extra_options.strip()
    if extra_options:
        command += shlex.split(extra_options)
    return command

def unpaperImage(configuration_manager, image_path):
    tmp_dir = configuration_manager.TEMPORARY_FOLDER
    prefix = os.path.splitext(image_path)[0]
    basename = os.path.basename(prefix)
    unpapered_in = getNonExistingFileName(os.path.join(tmp_dir,
                                                       basename + '_orig.pnm'))
    unpapered_name = getNonExistingFileName(os.path.join(tmp_dir,
                                                         basename + '.pnm'))
    image_path = Image.open(image_path)
    image_path.save(unpapered_in, format = 'PPM')
    command = getUnpaperCommand(configuration_manager)
    command += [unpapered_in, unpapered_name]
    debug(command)
    try:
        subprocess.run(command)
    except Exception as exception:
        debug(exception)
        return None
    finally:
        os.unlink(unpapered_in)
    return unpapered_name

def obtainScanners():
    sane.init()
    try:
        devices = sane.get_devices()
        return devices
    except (RuntimeError, sane._sane.error) as msgerr:
        return None

def getScannerOption (scandev, name):
    options = scandev.get_options()

    for option in options:
        if option[1] == name:
            return option
    return None

def scan(device):
    try:
        scandev = sane.open(device)
        try:
            scandev.mode = 'Color24'
        except:
            debug('Unable to set scanner mode to "Color24".')
            try:
                scandev.mode = 'Color'
            except:
                debug('Unable to set scanner mode to "Color". Using default.')
        try:
            scandev.resolution = 300
        except:
            debug('Unable to set scanner resolution to 300 DPI. Using default.')
        try:
            scandev.tl_x = 0
            scandev.tl_y = 0
            scandev.br_x = getScannerOption(scandev, 'br-x')[8][1]
            scandev.br_y = getScannerOption(scandev, 'br-y')[8][1]
        except:
            debug('Unable to set scan geometry. Using default.')
        result = scandev.scan()
        filename = tempfile.mktemp(suffix='.png')
        result.save(filename, 'PNG')
        scandev.close()
        return filename
    except (RuntimeError, sane._sane.error) as msgerr:
        return None

languages = {}

def getLanguages():
    global languages
    if not languages:
        root = etree.parse(os.path.join(ISO_CODES_PATH, 'iso_639.xml'))
        for element in root.findall('.//iso_639_entry[@iso_639_1_code]'):
            languages[element.get('iso_639_1_code')] = element.get('name')
    return languages

def makeRadioButton(label, from_widget=None):
    if from_widget:
        button = Gtk.RadioButton.new_from_widget(from_widget)
    else:
        button = Gtk.RadioButton()
    button.set_label(label)
    button.set_use_underline(True)

    return button
