#!/usr/bin/env python

from setuptools import setup
from util import constants
import glob
import os

def get_locale_files():
    files = glob.glob('locale/*/*/*.mo')
    file_list = []
    for file in files:
        file_list.append((os.path.dirname(os.path.join(constants.RESOURCES_DIR, file)), [file]))
        return file_list

setup(name = 'OCRFeeder',
     version = constants.OCRFEEDER_STUDIO_VERSION,
     description = '''A complete Optical Character Recognition and
                      Document Analysis and Recognition program.''',
     author = 'Joaquim Rocha',
     author_email = 'joaquimrocha1@gmail.com',
     url = constants.OCRFEEDER_WEBSITE,
     license = 'GPL v3',
     packages = ['feeder', 'studio',
                 'util', 'odf',
                 ],
     scripts = ['ocrfeeder', 'ocrfeeder-cli'],
     data_files = [(constants.RESOURCES_DIR + '/icons', ['resources/icons/detect_icon.svg',
                                                         'resources/icons/ocr.svg',
                                                         'resources/icons/window_icon.png']
                    ),
                   ] + get_locale_files()
     )
