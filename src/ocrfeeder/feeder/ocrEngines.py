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
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError
from ocrfeeder.studio.dataHolder import TEXT_TYPE, IMAGE_TYPE
from ocrfeeder.util import lib
from ocrfeeder.util.log import debug
IMAGE_ARGUMENT = '$IMAGE'
FILE_ARGUMENT = '$FILE'
LANGUAGE_ARGUMENT = '$LANG'

class Engine:

    def __init__(self, name, engine_path, arguments,
                 image = None, temporary_folder = '/tmp/',
                 image_format = 'PPM', failure_string = '',
                 languages = '', language_argument = '',
                 version = 0.0):

        self.name = name
        self.engine_path = engine_path
        self.arguments = arguments
        self.version = version
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
        self.language_argument = language_argument
        self.setLanguages(languages)
        self.temporary_folder = temporary_folder
        self.__color_information = None
        self.setLanguage('')

    def setImage(self, image):
        image_file = tempfile.mkstemp(dir = self.temporary_folder,
                                      suffix = '.' + self.image_format.lower())[1]
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

        if self._favorite_language:
            if self.languages:
                favorite_language = self.languages.get(self._favorite_language, '')
                if not favorite_language:
                    values = list(self.languages.values())
                    if values:
                        favorite_language = values[0]
                parsed_arguments = parsed_arguments.replace(LANGUAGE_ARGUMENT,
                                         '%s %s' % (self.language_argument,
                                                    favorite_language))
        else:
            parsed_arguments = parsed_arguments.replace(LANGUAGE_ARGUMENT, '')

        return os.popen(self.engine_path + ' ' + parsed_arguments).read()

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

    def saveToXml(self, file_path):
        engine_info = {'name': self.name,
                       'engine_path': self.engine_path,
                       'arguments': self.arguments,
                       'image_format': self.image_format,
                       'failure_string': self.failure_string,
                       'language_argument': self.language_argument,
                       'languages': self.serializeLanguages(self.languages),
                       'version': self.version}
        root = ET.Element('engine')
        for key, value in engine_info.items():
            if not key or not value:
                continue
            subelement = ET.SubElement(root, key)
            subelement.text = str(value)
        return ET.ElementTree(root).write(file_path, 'UTF-8')

    def unserializeLanguages(self, languages):
        langs_dict = {}
        langs_list = languages.split(',')
        for language in langs_list:
            language_split = language.split(':')
            if len(language_split) == 2:
                langs_dict[language_split[0]] = language_split[1]
        return langs_dict

    def serializeLanguages(self, language_dict):
        return ','.join(['%s:%s' % (lang, engine_lang)
                         for lang, engine_lang in language_dict.items()])

    def hasLanguages(self):
        return self.languages and self.language_argument and \
            self.arguments.find(LANGUAGE_ARGUMENT) != -1

    def setLanguages(self, languages):
        self._languages = self.unserializeLanguages(languages)

    def getLanguages(self):
        return self._languages

    def setLanguage(self, language):
        self._favorite_language = language

    def getLanguage(self):
        return self._favorite_language

    languages = property(getLanguages, setLanguages)

class OcrEnginesManager:

    def __init__(self, configuration_manager):
        self.ocr_engines = []
        self.configuration_manager = configuration_manager

    def getEnginesNames(self):
        return [engine.name for engine, path in self.ocr_engines]

    def getEnginePath(self, engine):
        for eng, path in self.ocr_engines:
            if eng == engine:
                return path
        return None

    def replaceEngine(self, engine, new_engine):
        for i in range(len(self.ocr_engines)):
            eng, path = self.ocr_engines[i]
            if eng == engine:
                new_path = self.engineToXml(new_engine, path)
                self.ocr_engines[i] = new_engine, path
                return True
        return False

    def makeEnginesFromFolder(self, folder):
        self.ocr_engines = []
        favorite_engine_exists = False
        for xml_file in self.getXmlFilesInFolder(folder):
            engine = self.getEngineFromXml(xml_file)
            if engine:
                self.ocr_engines.append((engine, xml_file))
                favorite_engine_exists = favorite_engine_exists or \
                    self.configuration_manager.favorite_engine == engine.name
        if not len(self.ocr_engines):
            debug("Warning: no engines found!")
        elif not favorite_engine_exists:
            self.configuration_manager.favorite_engine = self.ocr_engines[-1][0].name
        engines_needing_update = {'auto': [],
                                  'manual': []}
        for engine, path in self.ocr_engines:
            path = engine.engine_path
            default_conf = \
                self.configuration_manager.getEngineDefaultConfiguration(path)
            if default_conf is None:
                continue
            if float(engine.version) < float(default_conf['version']):
                update_type = 'manual'
                for arguments in default_conf['old_arguments']:
                    if engine.arguments == arguments:
                        update_type = 'auto'
                        break
                engines_needing_update[update_type].append({'engine': engine,
                                               'configuration': default_conf})
        return engines_needing_update

    def migrateEngine(self, engine, configuration, only_version = False):
        if not only_version:
            engine.arguments = configuration['arguments']
            engine.language_argument = configuration['language_argument']
            engine.setLanguages(configuration['languages'])
        engine.version = configuration['version']
        self.replaceEngine(engine, engine)

    def getEngineFromXml(self, xml_file_name):
        document = ET.parse(xml_file_name)
        root_node = document.getroot()
        arguments = {}
        for child in list(root_node):
            arg_name = child.tag
            arg_value = child.text
            arguments[arg_name] = arg_value

        try:
            engine = Engine(**arguments)
        except TypeError as exception:
            debug('Error when unserializing engine: %s', exception.message)
            engine = None
        except WrongSettingsForEngine as we:
            debug("Cannot load engine at %s: %s", xml_file_name, str(we))
            engine = None
        else:
            engine.temporary_folder = self.configuration_manager.TEMPORARY_FOLDER
        return engine

    def getXmlFilesInFolder(self, folder):
        return [os.path.join(folder, file) for file in sorted(os.listdir(folder)) if file.endswith('.xml')]

    def newEngine(self, name, engine_path, arguments,
                  image_format, failure_string, languages,
                  language_argument, version):
        engine = Engine(name = name, engine_path = engine_path,
                        arguments = arguments, image_format = image_format,
                        temporary_folder = self.configuration_manager.TEMPORARY_FOLDER,
                        failure_string = failure_string,
                        languages = languages,
                        language_argument = language_argument,
                        version = version)
        return engine

    def delete(self, index):
        path = self.ocr_engines[index][1]
        os.remove(path)
        del self.ocr_engines[index]

    def addNewEngine(self, engine):
        path = self.engineToXml(engine)
        self.ocr_engines.append((engine,path))

    def engineToXml(self, engine, path = None):
        if not path:
            path = os.path.join(self.configuration_manager.user_engines_folder, engine.name + '.xml')
            path = lib.getNonExistingFileName(path)
        engine_content = engine.saveToXml(path)
        return path

class WrongSettingsForEngine(Exception):

    def __init__(self, message):
        super(WrongSettingsForEngine, self).__init__(message)
