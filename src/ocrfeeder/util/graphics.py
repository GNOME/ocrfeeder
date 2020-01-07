###########################################################################
#    OCRFeeder - The complete OCR suite
#    Copyright (C) 2009-2013 Joaquim Rocha <me@joaquimrocha.com>
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

from .lib import getNonExistingFileName
from .log import debug
from PIL import Image
from gi.repository import GdkPixbuf
import math
import imghdr
import os

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
    assert(pixbuf.get_colorspace() == GdkPixbuf.Colorspace.RGB)
    dimensions = pixbuf.get_width(), pixbuf.get_height()
    pixels = pixbuf.get_pixels()
    mode = pixbuf.get_has_alpha() and "RGBA" or "RGB"
    num_channels = len(mode)

    # When calling get_pixels() on subpixbufs, the buffer is the same
    # as the original pixbuf's but the first character is given by the
    # x and y of the subpixbuf. This means that we have to extract the
    # right buffer part corresponding only to the subpixbuf's pixels when
    # creating the Image from bytes.
    if pixbuf.get_byte_length() > num_channels * dimensions[0] * dimensions[1]:
        i = 0
        p = b''
        for j in range(pixbuf.get_height()):
            p += pixels[i:i + pixbuf.get_width() * num_channels]
            i += pixbuf.get_rowstride()
        pixels = p

    return Image.frombytes(mode, dimensions, pixels)

def rgbaToInteger(rgba):
    r, g, b, a = rgba
    return (r << 24) | (g << 16) | (b << 8) | a

def colorsContrast(color1, color2, tolerance = 120):
    return abs(color1 - color2) > tolerance

def getImageResolution(image_object):
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

def getTextSizeFromImage(image):
    width, height = image.size
    colors = image.getcolors(width * height)
    background_color = 255
    if colors:
        colors.sort()
        background_color = colors[-1][1]
    text_sizes = []
    for i in range(1, height):
        blank_line = True
        for j in range(0, width, 3):
            color = image.getpixel((j, i - 1))
            if colorsContrast(color, background_color):
                blank_line = False
                break
        if blank_line:
            if text_sizes and text_sizes[-1]:
                text_sizes.append(0)
        else:
            if text_sizes and text_sizes[-1]:
                text_sizes[-1] += 1
            else:
                text_sizes.append(1)
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
    debug('Text Size: %s', text_size)
    return text_size

def getTextBeginHeight(image):
    width, height = image.size
    for i in range(1, height, 1):
        current_line = image.crop((0, i - 1, width, i))
        colors = current_line.getcolors()
        for color in colors:
            if colorsContrast(color, 0) == 0:
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

def convertMultiImage(image_path, temp_dir):
    converted_paths = []
    if imghdr.what(image_path) != 'tiff':
        return [image_path]

    debug('Checking for multiple images in TIFF')
    i = 0
    base_name = os.path.basename(image_path)
    name, extension = os.path.splitext(base_name)
    image = Image.open(image_path)
    try:
        while True:
            image.seek(i)
            file_name = os.path.join(temp_dir, name + ' #' + str(i + 1) + \
                                     extension)
            image_name = getNonExistingFileName(file_name)
            image.save(image_name, format='TIFF')
            debug('Saved %s', image_name)
            converted_paths.append(image_name)
            i += 1
    except EOFError:
        # No more images in the file
        pass

    return converted_paths

def convertMultiImagesInList(image_list, temp_dir):
    for i in range(len(image_list)):
        converted_images = convertMultiImage(image_list[i], temp_dir)
        converted_list = image_list[:i] + converted_images + image_list[i + 1:]
        image_path_list = converted_list
    return converted_list
