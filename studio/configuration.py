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

from studio.dataHolder import PageData, DataBox, TextData
from util.lib import debug
from xml.dom import minidom
import os.path
import re
import shutil
import tempfile
import zipfile

class ProjectSaver:
    
    def __init__(self, pages_data, temp_dir = '/tmp'):
        
        self.pages_data = pages_data
        self.document = minidom.Document()
        self.images = {}
        self.temp_dir = temp_dir
    
    def __handleImageEmbedding(self, page_data):
        base_name = os.path.basename(page_data.image_path)
        embedded_names = []
        for original_path, embedded_name in self.images.items():
            embedded_names.append(embedded_name)
            if os.path.samefile(original_path, page_data.image_path):
                return embedded_name
        i = 0
        while base_name in embedded_names:
            base_name += '_%s' % i
            i += 1
        self.images[page_data.image_path] = base_name
        return base_name
    
    def __imagesToXml(self, root_node):
        for page_data in self.pages_data:
            self.__handleImageEmbedding(page_data)
        images_node = root_node.appendChild(self.document.createElement('images'))
        for original_name, embedded_name in self.images.items():
            original = self.document.createElement('original_name')
            original.appendChild(self.document.createTextNode(original_name))
            embedded = self.document.createElement('embedded_name')
            embedded.appendChild(self.document.createTextNode(embedded_name))
            new_image = self.document.createElement('image')
            new_image.appendChild(original)
            new_image.appendChild(embedded)
            images_node.appendChild(new_image)
    
    def convertToXml(self, item, root_node):
        if type(item) == dict:
            for key, value in item.items():
                new_node = self.document.createElement(key)
                self.convertToXml(value, new_node)
                root_node.appendChild(new_node)
        elif type(item) == list:
            for element in item:
                self.convertToXml(element, root_node)
        else:
            text_node = self.document.createTextNode(str(item))
            root_node.appendChild(text_node)
        return root_node
    
    def serialize(self, file_name):
        root_node = self.document.createElement('ocrfeeder')
        pages_dict = {'pages': [page_data.convertToDict() for page_data in self.pages_data]}
        new_node = self.convertToXml(pages_dict, root_node)
        self.__imagesToXml(root_node)
        self.__createProjectFile(new_node.toxml(), file_name)
    
    def __createProjectFile(self, xml_content, file_name):
        temp_dir = tempfile.mkstemp(dir = self.temp_dir)[1]
        try:
            os.remove(temp_dir)
        except:
            pass
        os.mkdir(temp_dir)
        old_dir = os.curdir
        os.chdir(temp_dir)
        images_dir = os.path.join(os.curdir, 'images')
        os.mkdir(images_dir)
        zip = zipfile.ZipFile(file_name, 'w')
        for original_name, embbeded_name in self.images.items():
            embedded_name = os.path.join(images_dir, embbeded_name)
            shutil.copy(original_name, embedded_name)
            zip.write(embedded_name)
        f = open(os.path.join(os.curdir, 'project.xml'), 'w')
        f.write(xml_content)
        f.close()
        zip.write(os.path.join(os.curdir, 'project.xml'))
        zip.close()
        os.chdir(old_dir)
        shutil.rmtree(temp_dir, ignore_errors = True)
    
class ProjectLoader:
    
    def __init__(self, project_file, temp_dir = '/tmp'):
        self.temp_dir = temp_dir
        if not (os.path.isfile(project_file) and project_file.endswith('.ocrf')):
            #raise
            pass
        self.configuration_dir = self.unzipFile(project_file)
    
    def loadConfiguration(self, folder = None):
        folder = folder or self.configuration_dir
        project_xml = os.path.join(folder, 'project.xml')
        if not project_xml:
            return None
        document = minidom.parse(project_xml)
        root_node = document.documentElement
        images_node = document.getElementsByTagName('image')
        images = self.__getImagesInfo(images_node)
        page_data_nodes = document.getElementsByTagName('PageData')
        pages = []
        for page_data in self.__getPageDataInfo(page_data_nodes):
            debug('Page Data:', page_data)
            data_boxes = []
            for data_box in page_data['data_boxes']:
                args = []
                # text variable is to avoid problems with
                # escaping characters 
                text = ''
                for var_name, value in data_box.items():
                    if var_name == 'text':
                        text = value
                        continue
                    real_value = '"""%s"""' % re.escape(value)
                    try:
                        real_value = int(value)
                    except ValueError:
                        pass
                    args.append('%s = %s' % (var_name, real_value))
                exec('box = DataBox(%s)' % ', '.join(args))
                box.text = text
                data_boxes.append(box)
            image_path = page_data['image_path']
            if not os.path.exists(image_path):
                image_path = os.path.join(self.configuration_dir, 'images', images[image_path])
            page = PageData(image_path, data_boxes)
            pages.append(page)
        return pages
    
    def __getImagesInfo(self, images_nodes_list):
        images = {}
        for image_node in images_nodes_list:
            original_name = ''
            embedded_name = ''
            for child in image_node.childNodes:
                if child.localName == 'original_name':
                    original_name = child.childNodes[0].nodeValue
                elif child.localName == 'embedded_name':
                    embedded_name = child.childNodes[0].nodeValue
            if original_name and embedded_name:
                images[original_name] = embedded_name
        return images
    
    def __getPageDataInfo(self, pages_nodes_list):
        page_data_info = []
        for page in pages_nodes_list:
            page_data = {}
            for child in page.childNodes:
                if child.localName == 'data_boxes':
                    page_data[child.localName] = self.__getDataBoxesInfo(child)
                    pass
                elif child.nodeType == child.ELEMENT_NODE:
                    page_data[child.localName] = child.childNodes[0].nodeValue
            page_data_info.append(page_data)
        return page_data_info
    
    def __getDataBoxesInfo(self, data_boxes_node):
        data_boxes_info = []
        for child in data_boxes_node.childNodes:
            if child.localName == 'DataBox':
                data_boxes_info.append(self.__getDataBoxInfo(child))
        return data_boxes_info
    
    def __getDataBoxInfo(self, data_box_node):
        data_box_info = {}
        for child in data_box_node.childNodes:
            if child.localName == 'text_data':
                pass
            elif child.nodeType == child.ELEMENT_NODE:
                childNodes = child.childNodes
                if childNodes:
                    data_box_info[child.localName] = childNodes[0].nodeValue
                else:
                    data_box_info[child.localName] = ''
        return data_box_info
    
    def __getTextDatasInfo(self, text_datas):
        text_datas_info = []
        for child in text_datas.childNodes:
            if child.localName == 'TextData':
                text_datas_info.append(self.__getTextDataInfo(child))
        return text_datas_info
    
    def __getTextDataInfo(self, text_data):
        text_data_info = {}
        for child in text_data.childNodes:
            text_data_info[child.localName] = child.childNodes[0].nodeValue
        return text_data_info
    
    def unzipFile(self, file):
        base_name = os.path.basename(file)
        export_dir = os.path.join(self.temp_dir, os.path.splitext(base_name)[0])
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir, ignore_errors = True)
        os.mkdir(export_dir)
        project_zip = zipfile.ZipFile(file)
        for name in project_zip.namelist():
            if name.endswith(os.path.sep):
                os.mkdir(os.path.join(export_dir, name))
            else:
                dir_name = os.path.dirname(name)
                dir_name_path = os.path.join(export_dir, dir_name)
                if dir_name:
                    if not os.path.exists(dir_name_path):
                        os.makedirs(dir_name_path)
                outfile = open(os.path.join(export_dir, name), 'wb')
                outfile.write(project_zip.read(name))
                outfile.close()
        return export_dir

class ConfigurationManager:
    
    DEFAULTS = {'temporary_dir': '/tmp',
                'text_fill': '94, 156, 235, 150',
                'text_stroke': '94, 156, 235, 250',
                'image_fill': '0, 183, 0, 150',
                'image_stroke': '94, 156, 235, 250',
                'window_size': 'auto',
                'unpaper': '/usr/bin/unpaper',
                'favorite_engine': 'ocrad'
                }
    
    def __init__(self):
        self.setDefaults()
        self.user_configuration_folder = os.path.expanduser('~/.ocrfeeder')
        self.user_engines_folder = os.path.join(self.user_configuration_folder, 'engines')
        self.makeUserConfigurationFolder()
            
    def makeUserConfigurationFolder(self):
        if not os.path.exists(self.user_engines_folder):
            os.makedirs(self.user_engines_folder)
        folder_contents = [item for item in os.listdir(self.user_engines_folder) if item.endswith('.xml')]
        if not folder_contents:
            dir_name = os.path.dirname(__file__)
            engines_folder = os.path.abspath(os.path.join(dir_name, os.pardir, 'engines'))
            for file in [item for item in os.listdir(engines_folder) if item.endswith('.xml')]:
                shutil.copyfile(os.path.join(engines_folder, file), os.path.join(self.user_engines_folder, file))
    
    def setTemporaryDir(self, temp_dir):
        self.temporary_dir = temp_dir
    
    def getTemporaryDir(self):
        return self.temporary_dir
    
    def setFavoriteEngine(self, engine_name):
        self.favorite_engine = engine_name
    
    def getFavoriteEngine(self):
        return self.favoriteEngine
    
    def __getColorString(self, color):
        string_color = ', '.join([str(color_value) for color_value in list(color)])
        return string_color
    
    def setTextFill(self, color):
        self.text_fill = self.__getColorString(color)
    
    def setTextStroke(self, color):
        self.text_stroke = self.__getColorString(color)
    
    def setImageFill(self, color):
        self.image_fill = self.__getColorString(color)
    
    def setImageStroke(self, color):
        self.image_stroke = self.__getColorString(color)
    
    def getTextFill(self):
        return eval(self.text_fill)
    
    def getTextStroke(self):
        return eval(self.text_stroke)
    
    def getImageFill(self):
        return eval(self.image_fill)
    
    def getImageStroke(self):
        return eval(self.image_stroke)
    
    def setWindowSize(self, window_size):
        self.window_size = window_size
    
    def setUnpaper(self, unpaper):
        self.unpaper = unpaper
    
    def getUnpaper(self):
        return self.unpaper
    
    def setDefaults(self):
        for key, value in self.DEFAULTS.items():
            exec('self.%s = "%s"' % (key, value))
    
    def getDefault(self, variable_name):
        if variable_name in self.DEFAULTS.keys():
            return self.DEFAULTS[variable_name]
        else:
            return ''
    
    def loadConfiguration(self):
        configuration_file = os.path.join(self.user_configuration_folder, 'preferences.xml')
        if not os.path.isfile(configuration_file):
            return False
        document = minidom.parse(configuration_file)
        for key in self.DEFAULTS.keys():
            nodeList = document.getElementsByTagName(key)
            if nodeList:
                for node in nodeList:
                    for child in node.childNodes:
                        if child.nodeType == child.TEXT_NODE:
                            exec('self.%s = "%s"' % (key, child.nodeValue))
                            break
        return True
    
    def configurationToXml(self):
        configuration_file = os.path.join(self.user_configuration_folder, 'preferences.xml')
        doc = minidom.Document()
        root_node = doc.createElement('ocrfeeder')
        for key in self.DEFAULTS.keys():
            new_node = doc.createElement(key)
            new_node.appendChild(doc.createTextNode("""%s""" % eval('self.%s' % key)))
            root_node.appendChild(new_node)
        configuration = doc.toxml(encoding = 'utf-8')
        configuration += '\n' + root_node.toxml(encoding = 'utf-8')
        new_configuration_file = open(configuration_file, 'w')
        new_configuration_file.write(configuration)
        new_configuration_file.close()
