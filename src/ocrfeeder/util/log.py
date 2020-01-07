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

import logging
from .constants import OCRFEEDER_COMPACT_NAME, OCRFEEDER_DEBUG

logger = logging.getLogger(OCRFEEDER_COMPACT_NAME)
LOG_FORMAT = "%(asctime)-15s %(levelname)s: %(message)s"
logging.basicConfig(format=LOG_FORMAT)

def debug(*args):
    if OCRFEEDER_DEBUG:
        logger.setLevel(logging.DEBUG)
    logger.debug(*args)

info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
log = logger.log

