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

from lib import getStandardDeviation
from util.lib import debug
import Image
import gtk
import math

def getContainerRectangle(points_list):
    points_list = list(points_list)
    points_list.sort()
    leftmost_x = (points_list[0])[0]
    rightmost_x = (points_list[-1])[0]
    i = 0
    while i < len(points_list):
        current_point = points_list[i]
        points_list[i] = (current_point[1], current_point[0])
        i += 1
    points_list.sort()
    highest_y = (points_list[0])[0]
    lowest_y = (points_list[-1])[0]
    return leftmost_x, highest_y, rightmost_x, lowest_y

def getBoundsFromStartEndPoints(start_point, end_point):
    start_x, start_y = start_point
    end_x, end_y = end_point
    width = end_x - start_x
    height = end_y - start_y
    if width < 0:
        start_x += width
        width = abs(width)
    if height < 0:
        start_y += height
        height = abs(height)
    return start_x, start_y, width, height

def convertPixbufToImage(pixbuf):
    assert(pixbuf.get_colorspace() == gtk.gdk.COLORSPACE_RGB)
    dimensions = pixbuf.get_width(), pixbuf.get_height()
    stride = pixbuf.get_rowstride()
    pixels = pixbuf.get_pixels()
    mode = pixbuf.get_has_alpha() and "RGBA" or "RGB"
    return Image.frombuffer(mode, dimensions, pixels,
                            "raw", mode, stride, 1)
    width, height = pixbuf.get_width(), pixbuf.get_height()
    return Image.fromstring("RGBA", (width, height), pixbuf.get_pixels())

def rgbaToInteger(rgba):
    r, g, b, a = rgba
    return (r << 24) | (g << 16) | (b << 8) | a

def colorsContrast(color1, color2, tolerance = 120):
    return abs(color1 - color2) > tolerance

def getImageResolution(image_object):
    image_object
    resolution = (300, 300)
    if 'dpi' in image_object.info.keys():
        resolution = image_object.info['dpi']
    return resolution

def getImageResolutionFromPath(image_path):
    image = Image.open(image_path)
    return getImageResolution(image)

def getImagePrintSizeFromPath(image_path):
    image_object = Image.open(image_path)
    return getImagePrintSize(image_object)

def getImagePrintSize(image_object):
    resolution = getImageResolution(image_object)
    x_resolution, y_resolution = resolution
    width, height = image_object.size
    return ( float(width) / float(x_resolution), float(height) / float(y_resolution) )
    

def OLDgetTextSizeFromImage(image):
    width, height = image.size
    text_sizes = [0]
    line_spaces = [0]
    remove_last_space = True
    for i in range(getTextBeginHeight(image), height, 1):
        current_line = image.crop((0, i - 1, width, i))
        current_line.convert('L')
        blank_line = True
        colors = current_line.getcolors()
        background_color = 255
        if colors:
            background_color = (list(colors[0][1])).pop()
        if colors:
            for color in colors:
                if colorsContrast(list(color[1]).pop(), background_color):
                    blank_line = False
                    break
            if blank_line:
                remove_last_space = True
                if len(text_sizes) > 1 or text_sizes[0] != 0:
                    line_spaces[-1] += 1
                if text_sizes[-1]:
                    text_sizes.append(0)
            else:
                remove_last_space = False
                text_sizes[-1] += 1
                if line_spaces:
                    if line_spaces[-1]:
                        line_spaces.append(0)
    if remove_last_space:
        if line_spaces:
            del line_spaces[-1]
    text_sizes.sort()
    text_sizes = [i for i in text_sizes if i != 0]
    line_spaces.sort()
    line_spaces = [i for i in line_spaces if i != 0]
    
    text_size = 0
    if text_sizes:
        text_sizes_avg = sum(text_sizes) / len(text_sizes)
        for i in text_sizes:
            if i > text_sizes_avg:
                text_size = math.floor(i)
                break
        text_size = max(text_sizes)
    line_space = 0
    if line_spaces:
        line_spaces_avg = sum(line_spaces) / len(line_spaces)
        for i in line_spaces:
            if i > line_spaces_avg:
                line_space = math.floor(i)
                break
        line_space = max(line_spaces)
    return text_size, 0
count = 0
def OLDgetTextSizeFromImage(image):
    width, height = image.size
    global count
    debug('Image #%s' % count)
    image.save('/tmp/img%s.png' % count , 'PNG')
    count += 1
    text_sizes = [0]
    for i in xrange(getTextBeginHeight(image), height):
        current_line = image.crop((0, i - 1, width, i))
        current_line.convert('L')
        blank_line = True
        colors = current_line.getcolors()
        background_color = 255
        if colors:
            colors.sort()
            background_color = (list(colors[-1][1])).pop()
            for color in colors:
                if colorsContrast(list(color[1]).pop(), background_color):
                    blank_line = False
                    break
            if blank_line:
                if text_sizes[-1]:
                    text_sizes.append(0)
            else:
                text_sizes[-1] += 1
    text_sizes.sort()
    text_sizes = [i for i in text_sizes if i != 0]
    text_size = 0
    if text_sizes:
        text_sizes_avg = sum(text_sizes) / len(text_sizes)
        for i in text_sizes:
            if i > text_sizes_avg:
                text_size = math.floor(i)
                break
        text_size = max(text_sizes)
    debug('Text Size: ', text_size)
    return text_size

def getTextSizeFromImage(image):
    width, height = image.size
    colors = image.getcolors(width * height)
    background_color = 255
    if colors:
        colors.sort()
        background_color = (list(colors[-1][1])).pop()
    text_sizes = [0]
    for i in xrange(getTextBeginHeight(image), height):
        current_line = image.crop((0, i - 1, width, i))
        current_line.convert('L')
        blank_line = True
        for i in range(0, current_line.size[0], 3):
            color = current_line.getpixel((i, 0))
            if colorsContrast(list(color).pop(), background_color):
                blank_line = False
                break
        if blank_line:
            if text_sizes[-1]:
                text_sizes.append(0)
        else:
            text_sizes[-1] += 1
    text_sizes.sort()
    text_sizes = [i for i in text_sizes if i != 0]
    text_size = 0
    if text_sizes:
        text_sizes_avg = sum(text_sizes) / len(text_sizes)
        for i in text_sizes:
            if i > text_sizes_avg:
                text_size = math.floor(i)
                break
        text_size = max(text_sizes)
    debug('Text Size: ', text_size)
    return text_size

def getTextBeginHeight(image):
    width, height = image.size
    for i in range(1, height, 1):
        current_line = image.crop((0, i - 1, width, i))
        colors = current_line.getcolors()
        foreground_color = [0, 0, 0]
        if colors:
            foreground_color = [0 for value in list((colors[0][1])[:-1])]
        if colors:
            for color in colors:
                if list(color[1])[:-1] == foreground_color:
                    return i
    return -1

def getHorizontalAngleForText(image):
    width, height = image.size
    longest_axis = math.sqrt(width ** 2 + height ** 2)
    collage = Image.new('RGBA', (longest_axis, longest_axis), 'white')
    test_image = image.copy().convert('RGBA')
    y_to_paste = (longest_axis - test_image.size[1]) / 2
    x_to_paste = (longest_axis - test_image.size[0]) / 2
    original_paste = collage.copy()
    original_paste.paste(test_image, (x_to_paste, y_to_paste), test_image)
    previous_text_begin = getTextBeginHeight(original_paste)
    paste_image = original_paste.copy()
    angle = 0
    while angle > -360:
        current_text_begin = getTextBeginHeight(paste_image)
        if previous_text_begin > current_text_begin or current_text_begin == -1:
            break
        previous_text_begin = getTextBeginHeight(paste_image)
        angle -=5
        paste_image = original_paste.rotate(angle)
        collage = Image.new('RGBA', paste_image.size, 'white')
        collage.paste(paste_image, (0,0), paste_image)
        paste_image = collage
    if angle:
        return angle + 5
    return angle

def getImageRotated(image, angle):
    transparent_bg_image = image.copy().convert('RGBA')
    transparent_bg_image = transparent_bg_image.rotate(angle, Image.BICUBIC, expand = True)
    collage = Image.new('RGBA', transparent_bg_image.size, 'white')
    collage.paste(transparent_bg_image, (0, 0), transparent_bg_image)
    return collage
