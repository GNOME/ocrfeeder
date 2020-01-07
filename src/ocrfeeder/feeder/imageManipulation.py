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

from ocrfeeder.util.log import debug

import gettext
from PIL import Image, ImageDraw
import os.path
from ocrfeeder.util import graphics
import sys

_ = gettext.gettext

class ImageProcessor:

    def __init__(self, path_to_image,
                 window_size = None, contrast_tolerance = 120):
        self.window_size = window_size
        self.contrast_tolerance = contrast_tolerance
        error_message = _("A problem occurred while trying to open the image:\n %s\n"
                          "Ensure the image exists or try converting it to another format.") % path_to_image
        if os.path.isfile(path_to_image):
            try:
                self.original_image = Image.open(path_to_image)
                self.black_n_white_image = self.original_image.convert('L')
                if not self.window_size:
                    self.window_size = self.original_image.size[1] / 60.
                debug('Window Size: %s', self.window_size)
            except:
                debug(sys.exc_info())
                raise ImageManipulationError(error_message)
        else:
            debug(sys.exc_info())
            raise ImageManipulationError(error_message)
        self.bg_color = 255

    def __windowContrast(self, bgcolor, x, y):
        image = self.black_n_white_image
        width, height = image.size

        image_upper_left_corner_x = x * self.window_size
        image_upper_left_corner_y = y * self.window_size

        i, j = 1, 1
        while j < self.window_size + 1:
            if not image_upper_left_corner_y + j < height:
                break
            while i < self.window_size + 1:
                if not image_upper_left_corner_x + i < width:
                    break
                pixel_point = (image_upper_left_corner_x + i,
                               image_upper_left_corner_y + j)
                if graphics.colorsContrast(image.getpixel(pixel_point),
                                           bgcolor,
                                           self.contrast_tolerance):
                    return 1
                i += 3
            i = 1
            j += 3
        return 0

    def imageToBinary(self):
        image = self.black_n_white_image
        binary_info = ['']
        width, height = image.size
        i, j = 0, 0
        while j < height / self.window_size:
            while i < width / self.window_size:
                binary_info[-1] += str(self.__windowContrast(self.bg_color, i, j))
                i += 1
            i = 0
            binary_info += ['']
            j += 1
        return binary_info

    def divideImageClipInColumns(self, clip_dimensions, column_min_width):
        if column_min_width == 0:
            return [clip_dimensions]
        if column_min_width is None:
            column_min_width = int(self.window_size / 2)

        clip = self.black_n_white_image.crop(clip_dimensions)
        width, height = clip.size
        content_column_bounds = self.__getImageContentColumnsBounds(clip,
                                                               column_min_width)
        x0, y0, x1, y1 = clip_dimensions
        column_bounds = []
        for i in range(0, len(content_column_bounds), 2):
            column_bounds.append((x0 + content_column_bounds[i], y0,
                                  x0 + content_column_bounds[i + 1], y1))

        return column_bounds

    def __getImageContentColumnsBounds(self, image, column_min_width):
        width, height = image.size
        column_bounds = []
        i = 0
        while i < width:
            next_step = min(i + column_min_width, width)
            slice_bounds = (i, 0, next_step, height)
            slice_clip = image.crop(slice_bounds)
            has_contrast = self.__imageHasContrast(slice_clip)
            if has_contrast:
                if not column_bounds:
                    column_bounds.extend([i, next_step])
                elif column_bounds[-1] == i:
                    column_bounds[-1] = next_step
                else:
                    column_bounds.extend([i, next_step])
            i = next_step
        return column_bounds

    def __imageHasContrast(self, image):
        colors = image.getcolors()
        has_contrast = True
        for color_count in colors:
            color = color_count[1]
            has_contrast = graphics.colorsContrast(color,
                                                   self.bg_color,
                                                   self.contrast_tolerance)
            if has_contrast:
                break
        return has_contrast

    def adjustImageClipMargins(self, clip_dimensions, margins_min_width):
        if margins_min_width == 0:
            return clip_dimensions
        if margins_min_width is None:
            margins_min_width = int(self.window_size / 2)
        x0, y0, x1, y1 = clip_dimensions

        clip = self.black_n_white_image.crop(clip_dimensions)
        left, top, right, bottom = self.__getImageMargins(clip,
                                                          margins_min_width)

        x0, y0, x1, y1 = x0 + left, y0 + top, x1 - right, y1 - bottom

        # Prevent having contents outside of the image's limits
        width, height = self.black_n_white_image.size
        x1 = min(x1, width)
        y1 = min(y1, height)

        return x0, y0, x1, y1

    def __getImageMargins(self, image, margins_min_width):
        width, height = image.size
        margins = [0, 0, 0, 0]

        # Left margin
        i = 0
        while i < width - margins_min_width:
            clip = image.crop((i, 0, i + margins_min_width, height))
            if self.__imageHasContrast(clip):
                margins[0] = i
                break
            i += margins_min_width

        # Right margin
        i = width
        while i > margins_min_width:
            clip = image.crop((i - margins_min_width, 0, i, height))
            if self.__imageHasContrast(clip):
                margins[2] = width - i
                break
            i -= margins_min_width

        # Top margin
        i = 0
        while i < height - margins_min_width:
            clip = image.crop((0, i, width, i + margins_min_width))
            if self.__imageHasContrast(clip):
                margins[1] = i
                break
            i += margins_min_width

        # Bottom margin
        i = height
        while i > margins_min_width:
            clip = image.crop((0, i - margins_min_width, width, i))
            if self.__imageHasContrast(clip):
                margins[3] = height - i
                break
            i -= margins_min_width

        return margins

class ContentAnalyser:

    def __init__(self, image):
        self.image = image

    def getHeight(self):
        width, height = self.image.size
        image_draw = ImageDraw.Draw(self.image)
        i = 0
        while i+3 < height:
            current_line_image = self.image.crop((0, i, width, i + 3))
            if len(current_line_image.getcolors()) < 10:
                image_draw.rectangle((0, i, width, i + 3), fill = (255, 255, 255))
            i += 3

    def __getBlankSpaceFromTopToBottom(self, image):
        width, height = image.size
        i = 0
        while i + 2 < height:
            current_line_image = image.crop((0, i, width, i + 1))
            if len(current_line_image.getcolors()) > 1:
                break
            i += 2
        return i

class ImageManipulationError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class InsuficientPointsForPolygon(Exception):

    def __init__(self):
        pass

    def __str__(self):
        return 'Insufficient number of points for polygon. Must be at least three points.'
