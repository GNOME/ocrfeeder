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

import string

import tempfile
import os
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from studio.dataHolder import TEXT_TYPE, IMAGE_TYPE
from util import lib
IMAGE_ARGUMENT = '$IMAGE'
FILE_ARGUMENT = '$FILE'

class Engine:
    
    def __init__(self, name, engine_path, arguments, image = None, temporary_folder = '/tmp/', image_format = 'PPM', failure_string = ''):
        
        self.name = name
        self.engine_path = engine_path
        self.arguments = arguments
        if not self.name:
            raise WrongSettingsForEngine("The engine's name cannot be empty!")
        if not self.engine_path or not os.path.isfile(self.engine_path):
            raise WrongSettingsForEngine("The engine's path must exist! Path: %s" % self.engine_path)
        if image == None:
            self.image_path = None
        else:
            self.image_path = self.setImage(image)
        self.image_format = image_format
        self.failure_string = failure_string
        self.temporary_folder = temporary_folder
        self.__color_information = None
    
    def setImage(self, image):
        image_file = tempfile.mkstemp(suffix = '.' + self.image_format.lower())[1]
        image = image.convert('L')
        try:
            image.save(image_file, format = self.image_format)
        except KeyError:
            image.save(image_file)
        self.image_path = image_file
    
    def read(self):
        parsed_arguments = self.arguments.replace(IMAGE_ARGUMENT, self.image_path)
        file_name = None
        if self.arguments.find(FILE_ARGUMENT) != -1:
            file_name = tempfile.mkstemp(dir = self.temporary_folder)[1]
            parsed_arguments = parsed_arguments.replace(FILE_ARGUMENT, file_name)
        text = os.popen(self.engine_path + ' ' + parsed_arguments).read()
        try:
            try:
                text = unicode(text, 'latin-1', 'replace').encode('utf-8', 'replace')
            except UnicodeDecodeError:
                text = unicode(text, 'ascii', 'replace').encode('utf-8', 'replace')
        finally:
            os.unlink(self.image_path)
        return text
            
    def classify(self, reading_output, rules = []):
        stripped_output = reading_output.strip()
        if not stripped_output:
            return IMAGE_TYPE
        if self.failure_string and stripped_output.count(self.failure_string) > len(stripped_output) / 2:
            return IMAGE_TYPE
        if self.__punctuationTest(stripped_output):
            return IMAGE_TYPE
        return TEXT_TYPE
        #else
        # FINISH THIS!
    def __punctuationTest(self, output):
        no_punctuation_output = output
        for char in string.punctuation:
            no_punctuation_output = no_punctuation_output.replace(char, '')
        no_punctuation_output = no_punctuation_output.replace(self.failure_string, '')
        no_punctuation_output = no_punctuation_output.replace(' ', '')
        if len(no_punctuation_output) < len(output) / 2:
            return True
        return False
        
    def __is_not_greyscale(self, image):
        colors = image.get_colors()
        if colors:
            for color in colors:
                if ((color[1])[0] - (color[1])[1])>10 or ((color[1])[0] - (color[1])[2])>10:
                    return False
        return True

class OcrEnginesManager:
    
    def __init__(self, configuration_manager):
        self.ocr_engines = []
        self.configuration_manager = configuration_manager
    
    def getEnginesNames(self):
        return [engine.name for engine in self.ocr_engines]
    
    def makeEnginesFromFolder(self, folder):
        self.ocr_engines = []
        for xml_file in self.getXmlFilesInFolder(folder):
            self.ocr_engines.append(self.getEngineFromXml(xml_file))
    
    def getEngineFromXml(self, xml_file_name):
        document = minidom.parse(xml_file_name)
        root_node = document.documentElement
        arguments = []
        for child in root_node.childNodes:
            if child.childNodes:
                if child.childNodes[0].nodeType == child.TEXT_NODE:
                    arguments.append('%s = "%s"' % (child.localName, child.childNodes[0].nodeValue))
        return eval('Engine(%s)' % ', '.join(arguments))
    
    def getXmlFilesInFolder(self, folder):
        return [os.path.join(folder, file) for file in os.listdir(folder) if file.endswith('.xml')]
    
    def newEngine(self, name, engine_path, arguments, image_format, failure_string):
        engine = Engine(name = name, engine_path = engine_path, arguments = arguments, image_format = image_format, failure_string = failure_string)
        return engine
    
    def delete(self, index):
        engine = self.ocr_engines[index].name
        path = os.path.join(self.configuration_manager.user_engines_folder, engine + '.xml')
        os.remove(path)
        del self.ocr_engines[index]
    
    def addNewEngine(self, engine):
        self.ocr_engines.append(engine)
        self.engineToXml(engine)
    
    def engineToXml(self, engine):
        engine_info = {'name': engine.name, 'engine_path': engine.engine_path, 'arguments': engine.arguments, 'image_format': engine.image_format, 'failure_string': engine.failure_string}
        doc = minidom.Document()
        root_node = doc.createElement('engine')
        for key, value in engine_info.items():
            if not value:
                continue
            new_node = doc.createElement(key)
            new_node.appendChild(doc.createTextNode(value))
            root_node.appendChild(new_node)
        engine_content = doc.ttesseractoxml(encoding = 'utf-8')
        engine_content += '\n' + root_node.toxml(encoding = 'utf-8')
        new_engine = os.path.join(self.configuration_manager.user_engines_folder, engine_info['name'] + '.xml')
        new_engine = lib.getNonExistingFileName(new_engine)
        new_engine_file = open(new_engine, 'w')
        new_engine_file.write(engine_content)
        new_engine_file.close()
        

class WrongSettingsForEngine(Exception):
    
    def __init__(self, message):
        super(WrongSettingsForEngine, self).__init__(message)
