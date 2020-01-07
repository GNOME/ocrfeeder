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

from ocrfeeder.feeder.ocrEngines import Engine
from ocrfeeder.util.lib import getExecPath
from ocrfeeder.util.log import debug
from ocrfeeder.util.constants import OCRFEEDER_COMPACT_NAME, USER_CONFIG_DIR
import tempfile
import shutil
from xml.dom import minidom
import os.path
import locale

PREDEFINED_ENGINES = {'tesseract': {'name': 'Tesseract',
                                    'image_format': 'TIF',
                                    'engine_path': 'tesseract',
                                    'arguments': '$LANG $IMAGE $FILE >'
                                    ' /dev/null 2> /dev/null; cat '
                                    '$FILE.txt; rm $FILE $FILE.txt',
                                    'old_arguments': ['$IMAGE $FILE >'
                                       ' /dev/null 2> /dev/null; cat '
                                       '$FILE.txt; rm $FILE $FILE.txt',
                                                  '$IMAGE $FILE; cat '
                                       '$FILE.txt; rm $FILE $FILE.txt'],
                                    'language_argument': '-l',
                                    'languages': 'af:afr,ar:ara,az:aze,be:bel,'
                                       'bn:ben,bg:bul,ca:cat,cs:cse,zh:chi-sim,'
                                       'chr:chr,da:dan,de:deu,el:ell,en:eng,'
                                       'et:est,eu:eus,fi:fin,fr:fra,gl:glg,he:heb,'
                                       'hi:hin,hr:hrv,hu:hun,id:ind,is:isl,it:ita,'
                                       'ja:jpn,kn:kan,ko:kor,lv:lav,lt:lit,ml:mal,'
                                       'mk:mkd,mt:mlt,ms:msa,nl:nld,no:nor,pl:pol,'
                                       'pt:por,ro:ron,ru:rus,sk:slk,sl:slv,es:spa,'
                                       'sq:sqi,sr:srp,sw:swa,sv:swe,ta:tam,te:tel,'
                                       'tl:tgl,th:tha,tr:tur,uk:ukr,vi:vie',
                                    'version': 0.2},
                      'ocrad': {'name': 'Ocrad',
                                'image_format': 'PPM',
                                'engine_path': 'ocrad',
                                'arguments': '-F utf8 $IMAGE',
                                'old_arguments': [],
                                'version': 0.0},
                      'gocr': {'name': 'GOCR',
                               'image_format': 'PPM',
                               'engine_path': 'gocr',
                               'arguments': '-f UTF8 $IMAGE',
                               'old_arguments': [],
                               'version': 0.0},
                      'cuneiform': {'name': 'Cuneiform',
                               'image_format': 'BMP',
                               'engine_path': 'cuneiform',
                               'arguments': '$LANG -f text -o $FILE $IMAGE >'
                               ' /dev/null 2> /dev/null && cat $FILE'
                               ' && rm $FILE',
                               'old_arguments': ['-f text -o $FILE $IMAGE >'
                                      ' /dev/null 2> /dev/null && cat $FILE'
                                      ' && rm $FILE'],
                               'language_argument': '-l',
                               'languages': 'en:eng,de:ger,fr:fra,ru:rus,sv:swe,'
                                            'es:spa,it:ita,uk:ukr,'
                                            'sr:srp,hr:hrv,pl:pol,da:dan,pt:por,'
                                            'nl:dut,cs:cze,ro:rum,hu:hun,bg:bul,'
                                            'sl:slv,lv:lav,lt:lit,et:est,tr:tur',
                               'version': 0.1},
                     }

class ConfigurationManager(object):

    TEXT_FILL = 'text_fill'
    IMAGE_FILL = 'image_fill'
    BOXES_STROKE = 'boxes_stroke'
    WINDOW_SIZE = 'window_size'
    UNPAPER = 'unpaper'
    UNPAPER_USE_BLACK_FILTER = 'unpaper_use_black_filter'
    UNPAPER_NOISE_FILTER_INTENSITY = 'unpaper_noise_filter_intensity'
    UNPAPER_GRAY_FILTER_SIZE = 'unpaper_gray_filter_size'
    UNPAPER_EXTRA_OPTIONS = 'unpaper_extra_options'
    UNPAPER_IMAGES_AFTER_ADDITION = 'unpaper_images_after_addition'
    FAVORITE_ENGINE = 'favorite_engine'
    IMPROVE_COLUMN_DETECTION = 'improve_column_detection'
    COLUMN_MIN_WIDTH = 'column_min_width'
    CLEAN_TEXT = 'clean_text'
    ADJUST_BOXES_BOUNDS = 'adjust_boxes_bounds'
    BOUNDS_ADJUSTMENT_SIZE = 'bounds_adjustment_size'
    DESKEW_IMAGES_AFTER_ADDITION = 'deskew_images_after_addition'
    LANGUAGE = 'language'

    TEMPORARY_FOLDER = tempfile.mkdtemp(prefix = OCRFEEDER_COMPACT_NAME + '_')

    DEFAULT_LOCALE = locale.getdefaultlocale()[0]

    DEFAULTS = {TEXT_FILL: (94, 156, 235, 150),
                BOXES_STROKE: (94, 156, 235, 250),
                IMAGE_FILL: (0, 183, 0, 150),
                WINDOW_SIZE: 'auto',
                UNPAPER: getExecPath('unpaper') or '',
                UNPAPER_USE_BLACK_FILTER: True,
                UNPAPER_NOISE_FILTER_INTENSITY: 'auto',
                UNPAPER_GRAY_FILTER_SIZE: 'auto',
                FAVORITE_ENGINE: 'tesseract',
                IMPROVE_COLUMN_DETECTION: True,
                COLUMN_MIN_WIDTH: 'auto',
                CLEAN_TEXT: True,
                ADJUST_BOXES_BOUNDS: True,
                BOUNDS_ADJUSTMENT_SIZE: 'auto',
                DESKEW_IMAGES_AFTER_ADDITION: False,
                UNPAPER_IMAGES_AFTER_ADDITION: False,
                UNPAPER_EXTRA_OPTIONS: '',
                LANGUAGE: DEFAULT_LOCALE.split('_')[0] if DEFAULT_LOCALE else '',
                }

    conf = dict(DEFAULTS)

    def __init__(self):
        self.user_configuration_folder = USER_CONFIG_DIR
        self.migrateOldConfigFolder()
        self.user_engines_folder = os.path.join(self.user_configuration_folder, 'engines')
        self.makeUserConfigurationFolder()
        self.has_unpaper = self.getDefault(self.UNPAPER)

    def makeUserConfigurationFolder(self):
        if not os.path.exists(self.user_engines_folder):
            os.makedirs(self.user_engines_folder)
        if [file_name for file_name in os.listdir(self.user_engines_folder)\
            if file_name.endswith('.xml')]:
            return
        for engine in self.getEnginesInSystem():
            engine_file = os.path.join(self.user_engines_folder, engine.name)
            engine.saveToXml('%s.xml' % engine_file)

    def getEnginesInSystem(self):
        existing_engines = []
        engines_paths = [(name, getExecPath(conf['engine_path']))\
                         for name, conf in PREDEFINED_ENGINES.items()]
        for name, path in engines_paths:
            if not path:
                continue
            engine_name = PREDEFINED_ENGINES[name].get('name', None)
            arguments = PREDEFINED_ENGINES[name].get('arguments', None)
            if not arguments or not engine_name:
                continue
            image_format = PREDEFINED_ENGINES[name].get('image_format', 'PPM')
            failure_string = PREDEFINED_ENGINES[name].get('failure_string', '')
            version = PREDEFINED_ENGINES[name].get('version', 0.0)
            language_argument = PREDEFINED_ENGINES[name].get('language_argument', '')
            languages = PREDEFINED_ENGINES[name].get('languages', '')
            favorite_language = PREDEFINED_ENGINES[name].get('favorite_language', '')
            engine = Engine(engine_name,
                            path,
                            arguments,
                            temporary_folder = self.TEMPORARY_FOLDER,
                            image_format = image_format,
                            failure_string = failure_string,
                            languages = languages,
                            language_argument = language_argument,
                            version = version)
            existing_engines.append(engine)
        return sorted(existing_engines, key=lambda x: x.name, reverse=False)

    def setConf(self, conf_key, value):
        ConfigurationManager.conf[conf_key] = value

    def getConf(self, conf_key):
        return ConfigurationManager.conf[conf_key]

    def setFavoriteEngine(self, engine_name):
        self.setConf(self.FAVORITE_ENGINE, engine_name)

    def getFavoriteEngine(self):
        return self.getConf(self.FAVORITE_ENGINE)

    def __getColorFromString(self, color):
        if type(color) != str:
            return color
        color_list = [value.strip('()\ ') for value in color.split(',')]
        try:
            int_color_list = [int(value) for value in color_list]
        except ValueError as exception:
            return None
        return tuple(int_color_list)

    def setTextFill(self, color):
        self.setConf(self.TEXT_FILL, color)

    def setBoxesStroke(self, color):
        self.setConf(self.BOXES_STROKE, color)

    def setImageFill(self, color):
        self.setConf(self.IMAGE_FILL, color)

    def getTextFill(self):
        return self.__getColorFromString(self.getConf(self.TEXT_FILL))

    def getBoxesStroke(self):
        return self.__getColorFromString(self.getConf(self.BOXES_STROKE))

    def getImageFill(self):
        return self.__getColorFromString(self.getConf(self.IMAGE_FILL))

    def setWindowSize(self, window_size):
        self.setConf(self.WINDOW_SIZE, window_size)

    def getWindowSize(self):
        return self.getConf(self.WINDOW_SIZE)

    def setUnpaper(self, unpaper):
        self.setConf(self.UNPAPER, unpaper)

    def getUnpaper(self):
        return self.getConf(self.UNPAPER)

    def setUseBlackFilter(self, use_black_filter):
        self.setConf(self.UNPAPER_USE_BLACK_FILTER, use_black_filter)

    def getUseBlackFilter(self):
        use_black_filter = self.getConf(self.UNPAPER_USE_BLACK_FILTER)
        return self.__convertBoolSetting(use_black_filter)

    def setNoiseFilterIntensity(self, noise_filter_intensity):
        self.setConf(self.UNPAPER_NOISE_FILTER_INTENSITY,
                     noise_filter_intensity)

    def getNoiseFilterIntensity(self):
        noise_filter_intensity = \
            self.getConf(self.UNPAPER_NOISE_FILTER_INTENSITY)
        if noise_filter_intensity == 'auto' or noise_filter_intensity == 'none':
            return noise_filter_intensity
        try:
            noise_filter_intensity_int = int(noise_filter_intensity)
        except ValueError:
            return 'auto'
        return noise_filter_intensity_int

    def setGrayFilterSize(self, gray_filter_size):
        self.setConf(self.UNPAPER_GRAY_FILTER_SIZE,
                     gray_filter_size)

    def getGrayFilterSize(self):
        gray_filter_size = self.getConf(self.UNPAPER_GRAY_FILTER_SIZE)
        if gray_filter_size == 'auto' or gray_filter_size == 'none':
            return gray_filter_size
        try:
            gray_filter_size_int = int(gray_filter_size)
        except ValueError:
            return 'auto'
        return gray_filter_size_int

    def setUnpaperExtraOptions(self, extra_options):
        self.setConf(self.UNPAPER_EXTRA_OPTIONS, extra_options)

    def getUnpaperExtraOptions(self):
        return self.getConf(self.UNPAPER_EXTRA_OPTIONS)

    def setUnpaperImagesAfterAddition(self, unpaper_images_after_addition):
        self.setConf(self.UNPAPER_IMAGES_AFTER_ADDITION,
                     unpaper_images_after_addition)

    def getUnpaperImagesAfterAddition(self):
        unpaper = self.getConf(self.UNPAPER_IMAGES_AFTER_ADDITION)
        return self.__convertBoolSetting(unpaper)

    def setImproveColumnDetection(self, improve_column_detection):
        self.setConf(self.IMPROVE_COLUMN_DETECTION, improve_column_detection)

    def getImproveColumnDetection(self):
        improve = self.getConf(self.IMPROVE_COLUMN_DETECTION)
        return self.__convertBoolSetting(improve)

    def setColumnMinWidth(self, column_min_width):
        self.setConf(self.COLUMN_MIN_WIDTH, column_min_width)

    def getColumnMinWidth(self):
        column_min_width = self.getConf(self.COLUMN_MIN_WIDTH)
        if column_min_width == 'auto':
            return column_min_width
        try:
            column_min_width_int = int(column_min_width)
        except ValueError:
            return 'auto'
        return column_min_width_int

    def getCleanText(self):
        clean_text = self.getConf(self.CLEAN_TEXT)
        return self.__convertBoolSetting(clean_text)

    def setCleanText(self, clean_text):
        self.setConf(self.CLEAN_TEXT, clean_text)

    def getLanguage(self):
        lang = self.getConf(self.LANGUAGE)
        return lang

    def setLanguage(self, language):
        self.setConf(self.LANGUAGE, language)

    def setAdjustBoxesBounds(self, adjust_boxes_bounds):
        self.setConf(self.ADJUST_BOXES_BOUNDS, adjust_boxes_bounds)

    def getAdjustBoxesBounds(self):
        adjust = self.getConf(self.ADJUST_BOXES_BOUNDS)
        return self.__convertBoolSetting(adjust)

    def setDeskewImagesAfterAddition(self, deskew_images_after_addition):
        self.setConf(self.DESKEW_IMAGES_AFTER_ADDITION,
                     deskew_images_after_addition)

    def getDeskewImagesAfterAddition(self):
        deskew = self.getConf(self.DESKEW_IMAGES_AFTER_ADDITION)
        return self.__convertBoolSetting(deskew)

    def setBoundsAdjustmentSize(self, adjustment_size):
        self.setConf(self.BOUNDS_ADJUSTMENT_SIZE, adjustment_size)

    def getBoundsAdjustmentSize(self):
        adjustment_size = self.getConf(self.BOUNDS_ADJUSTMENT_SIZE)
        if adjustment_size == 'auto':
            return adjustment_size
        try:
            adjustment_size_int = int(adjustment_size)
        except ValueError:
            return 'auto'
        return adjustment_size_int

    def __convertBoolSetting(self, setting):
        if type(setting) == str:
            if setting == 'True':
                setting = True
            else:
                setting = False
        return setting

    def setDefaults(self):
        ConfigurationManager.conf = dict(self.DEFAULTS)

    def getDefault(self, variable_name):
        if variable_name in self.DEFAULTS.keys():
            return self.DEFAULTS[variable_name]
        else:
            return ''

    def getEngineDefaultConfiguration(self, engine_path):
        path = os.path.basename(engine_path)
        for name, conf in PREDEFINED_ENGINES.items():
            if conf['engine_path'] == path:
                return conf
        return None

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
                            ConfigurationManager.conf[key] = str(child.nodeValue)
                            break
        return True

    def configurationToXml(self):
        configuration_file = os.path.join(self.user_configuration_folder, 'preferences.xml')
        doc = minidom.Document()
        root_node = doc.createElement('ocrfeeder')
        for key, value in list(ConfigurationManager.conf.items()):
            new_node = doc.createElement(key)
            new_node.appendChild(doc.createTextNode(str(value)))
            root_node.appendChild(new_node)
        configuration = doc.toxml(encoding = 'utf-8')
        configuration += b'\n' + root_node.toxml(encoding = 'utf-8')
        new_configuration_file = open(configuration_file, 'wb')
        new_configuration_file.write(configuration)
        new_configuration_file.close()

    def removeTemporaryFolder(self):
        try:
            shutil.rmtree(self.TEMPORARY_FOLDER)
        except:
            debug('Error when removing the temporary folder: ' + \
                  self.TEMPORARY_FOLDER)

    def migrateOldConfigFolder(self):
        old_config_folder = os.path.expanduser('~/.ocrfeeder')
        if os.path.exists(old_config_folder) and \
           not os.path.exists(self.user_configuration_folder):
            shutil.copytree(old_config_folder, self.user_configuration_folder)
            debug('Migrated old configuration directory "%s" to the '
                  'new one: "%s"',
                  old_config_folder, self.user_configuration_folder)

    text_fill = property(getTextFill,
                         setTextFill)
    image_fill = property(getImageFill,
                          setImageFill)
    boxes_stroke = property(getBoxesStroke,
                            setBoxesStroke)
    favorite_engine = property(getFavoriteEngine,
                               setFavoriteEngine)
    window_size = property(getWindowSize,
                           setWindowSize)
    unpaper = property(getUnpaper,
                       setUnpaper)

    unpaper_use_black_filter = property(getUseBlackFilter,
                                        setUseBlackFilter)

    unpaper_gray_filter_size = property(getGrayFilterSize,
                                        setGrayFilterSize)

    unpaper_noise_filter_intensity = property(getNoiseFilterIntensity,
                                              setNoiseFilterIntensity)

    unpaper_images_after_addition = property(getUnpaperImagesAfterAddition,
                                             setUnpaperImagesAfterAddition)

    unpaper_extra_options = property(getUnpaperExtraOptions,
                                     setUnpaperExtraOptions)

    improve_column_detection = property(getImproveColumnDetection,
                                        setImproveColumnDetection)
    column_min_width = property(getColumnMinWidth,
                                setColumnMinWidth)

    clean_text = property(getCleanText,
                          setCleanText)

    adjust_boxes_bounds = property(getAdjustBoxesBounds,
                                   setAdjustBoxesBounds)

    bounds_adjustment_size = property(getBoundsAdjustmentSize,
                                      setBoundsAdjustmentSize)

    deskew_images_after_addition = property(getDeskewImagesAfterAddition,
                                            setDeskewImagesAfterAddition)

    language = property(getLanguage, setLanguage)
