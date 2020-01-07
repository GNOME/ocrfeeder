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
from ocrfeeder.util import graphics, lib
from ocrfeeder.util.constants import OCRFEEDER_DEBUG, DTP
from ocrfeeder.studio.dataHolder import DataBox
from .imageManipulation import ImageProcessor
from PIL import Image
import re
import math

NONE = 0
TOP = -1
BOTTOM = 1
BOTH = 2
class Block:

    def __init__(self, start_line, finish_line, first_one, last_one=-1, extra_charge=0):
        self.start_line = start_line
        self.finish_line = finish_line
        self.first_one = first_one
        self.last_one = last_one
        self.extra_charge = extra_charge

    def isSingle(self):
        return self.start_line == self.finish_line and self.last_one != -1

    def checkSingleBlockBounds(self, block):
        return block.first_one != -1 and self.first_one >= block.first_one and self.last_one <= block.last_one

    def chargeExtraTop(self):
        if self.extra_charge == BOTTOM:
            self.extra_charge = BOTH
        else:
            self.extra_charge = TOP

    def chargeExtraBottom(self):
        if self.extra_charge == TOP:
            self.extra_charge = BOTH
        else:
            self.extra_charge = BOTTOM

    def testJoin(self, block):
        return self.extra_charge > 0 and (block.extra_charge == BOTH or block.extra_charge == TOP)

    def normalizeExtra(self, block):
        if (self.extra_charge == TOP or self.extra_charge == BOTH) and block.extra_charge > 0:
            self.extra_charge = BOTH
        elif (self.extra_charge == TOP or self.extra_charge == BOTH) and block.extra_charge <= 0:
            self.extra_charge = TOP
        elif (self.extra_charge == NONE or self.extra_charge == BOTTOM) and block.extra_charge > 0:
            self.extra_charge = BOTTOM
        else:
            self.extra_charge = NONE

    def decreaseStartLine(self, number_of_lines):
        self.start_line -= number_of_lines
        if self.extra_charge == TOP:
            self.extra_charge = NONE
        elif self.extra_charge == BOTH:
            self.extra_charge = BOTTOM

    def increaseStartLine(self, number_of_lines):
        self.start_line += number_of_lines
        if self.extra_charge == BOTTOM:
            self.extra_charge = NONE
        elif self.extra_charge == BOTH:
            self.extra_charge = TOP

    def increaseFinishLine(self, number_of_lines):
        self.finish_line += number_of_lines
        if self.extra_charge == BOTH:
            self.extra_charge = TOP
        elif self.extra_charge == BOTTOM:
            self.extra_charge = NONE

    def __getVerticalRange(self):
        return range(self.start_line, self.finish_line + 1)

    def __getHorizontalRange(self):
        return range(self.first_one, self.last_one + 1)

    def __inVerticalRange(self, verticalRange):
        begin = self.start_line
        end = self.finish_line
        if self.extra_charge == TOP or self.extra_charge == BOTH:
            begin -= 1
        elif self.extra_charge == BOTTOM or self.extra_charge == BOTH:
            end +=1
        return (begin in verticalRange[:-1]) or (end in verticalRange[1])

    def __inHorizontalRange(self, horizontalRange):
        return (self.first_one in horizontalRange) or (self.last_one in horizontalRange)

    def equals(self,block):
        return self.start_line == block.start_line and self.finish_line == block.finish_line and self.first_one == block.first_one and self.last_one == block.last_one

    def colides(self, block):
        vertical_range = self.__getVerticalRange()
        if block.__inHorizontalRange(self.__getHorizontalRange()):
            if (block.start_line in vertical_range) or (block.finish_line in vertical_range):
                return True
            if self.extra_charge >= 1:
                if self.finish_line + 1 == block.start_line:
                    return True
            if self.extra_charge == TOP or self.extra_charge == BOTH:
                if self.start_line - 1 == block.finish_line:
                    return True
        return False

    def translateToUnits(self, window_size):
        leftmost_x = self.first_one * window_size
        rightmost_x = self.last_one * window_size + window_size
        highest_y = self.start_line * window_size
        if self.extra_charge == BOTH or self.extra_charge == TOP:
            highest_y -= window_size / 2.0
        lowest_y = self.finish_line * window_size + window_size
        if self.extra_charge > 0:
            lowest_y += window_size / 2.0
        return int(leftmost_x), int(highest_y), int(rightmost_x), int(lowest_y)

    def __str__(self):
        block_str = """
Block ::::::::::::
  Start line:  %(start)s
  Finish line: %(finish)s
  First one: %(first)s
  Last one: %(last)s
  Extra charge: %(extra)s
""" % {'start': self.start_line, 'finish': self.finish_line,
       'first': self.first_one, 'last': self.last_one,
       'extra': self.extra_charge}
        return block_str

    def join(self, block):
        self.start_line = min(self.start_line, block.start_line)
        self.finish_line = max(self.finish_line, block.finish_line)
        self.first_one = min(self.first_one, block.first_one)
        self.last_one = max(self.last_one, block.last_one)
        self.normalizeExtra(block)

    def testUnification(self, block):
        if self.first_one != block.first_one and self.last_one != block.last_one:
            return False
        if self.finish_line + 1 == block.start_line:
            return True
        if self.finish_line + 2 == block.start_line and \
        (self.extra_charge > 0 and (block.extra_charge == BOTH or block.extra_charge == TOP)):
            return True
        return False

    def getOverlappedBlocks(self, block_list):
        overlapped_blocks = []
        i = 0
        while i < len(block_list):
            block = block_list[i]
            if self.equals(block):
                i += 1
                continue
            if self.colides(block):
                overlapped_blocks.append(i)
            i += 1
        return overlapped_blocks

    def getSurroundingBlocks(self, block_list):
        i = 0
        blocks_before = []
        blocks_after = []
        while i < len(block_list):
            block = block_list[i]
            if self.equals(block):
                i += 1
                continue
            if self.checkSingleBlockBounds(block):
                if block.finish_line + 1 == self.start_line:
                    blocks_before.append(i)
                elif block.start_line - 1 == self.finish_line:
                    blocks_after.append(i)
            i += 1
        return blocks_before, blocks_after

    def isContained(self, block_list):
        i = 0
        while i < len(block_list):
            block = block_list[i]
            if self.equals(block):
                i += 1
                continue
            if self.checkSingleBlockBounds(block):
                if self.start_line >= block.start_line and self.finish_line <= block.finish_line:
                    return True
            i += 1
        return False

class BlockRetriever:

    def __init__(self, string_list):
        self.string_list = string_list
        self.original_string_list = self.string_list
        self.text_blocks = []

    def getFirstOne(self, s):
        return s.find('1')

    def getLastOne(self, s):
        return s.rfind('1')

    def unifyBlockLeft(self, start_line, tolerance = 3):
        leftmost_one = self.getFirstOne(self.string_list[start_line])
        if leftmost_one == -1:
            return None
        test_min = leftmost_one
        current_line = start_line + 1
        while current_line < len(self.string_list) and test_min != -1:
            test_min = self.getFirstOne(self.string_list[current_line])
            if abs(test_min - leftmost_one) < tolerance:
                if test_min < leftmost_one:
                    if test_min != -1:
                        leftmost_one = test_min
                    else:
                        break
            else:
                break
            current_line += 1
        return (leftmost_one, current_line - 1)

    def retrieveBlocks(self):
        blocks = []
        while not self.isBlank():
            i = 0
            current_start_line = 0
            while i < len(self.string_list) and current_start_line < len(self.string_list):
                block_unified = self.unifyBlockLeft(current_start_line)
                if not block_unified:
                    i += 1
                    current_start_line += 1
                    continue
                first_one, finish_line = block_unified
                new_block = Block(current_start_line, finish_line, first_one, self.getFirstColumnOfZeros(current_start_line, finish_line, first_one))
                blocks.append(new_block)
                self.resetBlockStringsWithZeros(new_block)
                if current_start_line == finish_line:
                    current_start_line += 1
                else:
                    current_start_line = finish_line + 1
                i += 1
        return blocks

    def getFirstColumnOfZeros(self, start_line, finish_line, first_one):
        last_one = first_one
        if last_one != -1:
            while not self.__isZerosColumn(self.string_list, start_line, finish_line, last_one) and (last_one < len(self.string_list[start_line])):
                last_one += 1
        if last_one > first_one:
            last_one -= 1
        return last_one

    def __isZerosColumn(self, string_list, start_line, finish_line, col_index):
        if not finish_line < len(string_list):
            return False
        while start_line <= finish_line:
            try:
                if (string_list[start_line])[col_index] != '0':
                    return False
            except IndexError:
                return False
            start_line += 1
        return True

    def resetBlockStringsWithZeros(self, block):
        start_line = block.start_line
        finish_line = block.finish_line
        first_one = block.first_one
        last_one = block.last_one
        if block.first_one != -1:
            block_line_of_zeros = (self.string_list[start_line])[first_one:last_one + 1]
            block_line_of_zeros = block_line_of_zeros.replace('1', '0')
            current_line = start_line
            while current_line <= finish_line:
                current_string_line = self.string_list[current_line]
                self.string_list[current_line] = current_string_line[0:first_one] + block_line_of_zeros + current_string_line[last_one + 1:len(current_string_line)]
                current_line+=1
        return block

    def extendBlocksByBelongingSingles(self):
        self.blocks = self.retrieveBlocks()
        blocks = self.blocks
        i = 0
        while i < len(blocks):
            block = blocks[i]
            if block.isContained(blocks):
                del blocks[i]
                i -= 1
                continue
            if block.isSingle():
                before, after = block.getSurroundingBlocks(blocks)
                if before:
                    if after:
                        blocks[before[0]].chargeExtraBottom()
                        blocks[after[0]].chargeExtraTop()
                        if blocks[before[0]].testUnification(blocks[after[0]]):
                            blocks[before[0]].join(blocks[after[0]])
                            del blocks[after[0]]
                            i = -1
                    else:
                        blocks[before[0]].increaseFinishLine(1)
                        del blocks[i]
                        i = -1
                elif after:
                    blocks[after[0]].decreaseStartLine(1)
                    del blocks[i]
                    i = -1
            i += 1
        return blocks

    def unifyBlocks(self, blocks):
        i = 0
        while i < len(blocks):
            block = blocks[i]
            blocks_before, blocks_after = block.getSurroundingBlocks(blocks)
            if blocks_before:
                block_before = blocks_before[0]
                if blocks[block_before].testUnification(blocks[i]):
                    blocks[block_before].join(blocks[i])
                    del blocks[i]
                    i = 0
                    continue
            if blocks_after:
                block_after = blocks_after[0]
                if blocks[i].testUnification(blocks[block_after]):
                    blocks[i].join(blocks[block_after])
                    del blocks[block_after]
                    i = 0
                    continue
            i += 1
        i = 0
        while i < len(blocks):
            overlapped_blocks = blocks[i].getOverlappedBlocks(blocks)
            if overlapped_blocks:
                index = overlapped_blocks[0]
                blocks[i].join(blocks[index])
                del blocks[index]
                i = 0
                continue
            i += 1
        return blocks

    def isBlank(self):
        for line in self.string_list:
            if self.getFirstOne(line) != -1:
                return False
        return True

    def getAllBlocks(self):
        blocks = self.extendBlocksByBelongingSingles()
        blocks = self.unifyBlocks(blocks)
        if OCRFEEDER_DEBUG:
            for block in blocks:
                debug(block)
        return blocks

class ImageDeskewer(object):

    def __init__(self, bg_color = 255,
                 contrast_tolerance = 120):
        self.angle_step = 2
        self.bg_color = bg_color
        self.contrast_tolerance = contrast_tolerance

    def deskew(self, image_path, deskewed_image_path):
        try:
            image = Image.open(image_path)
        except:
            return False
        deskew_angle = self.get_deskew_angle(image)
        if not deskew_angle:
            return False
        deskewed_image = image.convert('RGBA').rotate(-deskew_angle,
                                                       Image.BICUBIC)
        collage = Image.new('L', image.size, color = self.bg_color)
        collage.paste(deskewed_image, None, deskewed_image)
        collage = collage.convert('RGB')
        collage.save(deskewed_image_path, format=image.format)
        return True

    def get_deskew_angle(self, image_orig):
        width, height = image_orig.size
        resize_ratio = 600 / float(width)
        # Convert image to grayscale and resize it for better
        # performance
        image = image_orig.convert('L')
        image = image.resize((int(round(width * resize_ratio)),
                              int(round(height * resize_ratio))))
        width, height = image.size
        max_r = int(round(math.sqrt(width ** 2 + height ** 2)))
        hough_accumulator = {}

        for x in range(0, width):
            for y in range(0, height - 1):
                if y + 1 > height:
                    break
                color = image.getpixel((x, y))
                color_below = image.getpixel((x, y + 1))
                if graphics.colorsContrast(color, self.bg_color,
                                           self.contrast_tolerance) and \
                   graphics.colorsContrast(color, color_below,
                                           self.contrast_tolerance):
                   for r, angle in self.__getDistanceAndAngle(x, y):
                       if 0 < r < max_r:
                           vote_value = hough_accumulator.get((r, angle), 0)
                           hough_accumulator[(r, angle)] = vote_value + 1

        if not hough_accumulator:
            return 0
        max_voted = list(hough_accumulator.keys())[0]
        for r_angle in hough_accumulator:
            max_voted_value = hough_accumulator.get(max_voted)
            if hough_accumulator[r_angle] > max_voted_value:
                max_voted = r_angle

        return 90 - max_voted[1]

    def __getDistanceAndAngle(self, x, y):
        for angle in range(1, 180, 1):
            angle_radians = angle * math.pi / 180
            r = math.cos(angle_radians) * x + math.sin(angle_radians) * y
            r = int(round(r))
            yield r, angle

class LayoutAnalysis(object):

    def __init__(self,
                 ocr_engine,
                 window_size = None,
                 improve_column_detection = True,
                 column_size = None,
                 clean_text = True,
                 adjust_boxes_bounds = True,
                 boxes_bounds_adjustment_size = None):
        self.ocr_engine = ocr_engine
        self.window_size = window_size
        self.column_size = column_size
        self.improve_column_detection = improve_column_detection
        self.clean_text = clean_text
        self.adjust_boxes_bounds = adjust_boxes_bounds
        self.boxes_bounds_adjustment_size = boxes_bounds_adjustment_size

    def recognize(self, path_to_image, page_resolution):
        image_processor = ImageProcessor(path_to_image,
                                         self.window_size)
        block_retriever = BlockRetriever(image_processor.imageToBinary())

        # Get "untouched" block bounds
        blocks = block_retriever.getAllBlocks()
        block_bounds = [block.translateToUnits(image_processor.window_size) \
                        for block in blocks]

        # Perform column subdivision (optimization of results)
        if self.improve_column_detection:
            bounds_optimized = []
            for bounds in block_bounds:
                bounds_divided = image_processor.divideImageClipInColumns(bounds,
                                                               self.column_size)
                bounds_optimized.extend(bounds_divided)
            block_bounds = bounds_optimized

        # Adjust margins (optimization of results)
        if self.adjust_boxes_bounds:
            block_bounds = [image_processor.adjustImageClipMargins(bounds, \
                                        self.boxes_bounds_adjustment_size) \
                            for bounds in block_bounds]

        image = image_processor.original_image
        data_boxes = [self.__recognizeImageFromBounds(image,
                                                      bounds,
                                                      page_resolution) \
                      for bounds in block_bounds]
        return data_boxes

    def __recognizeImageFromBounds(self, image, bounds, page_resolution):
        clip = image.crop(bounds)
        text = clip_type = None
        language = ''
        if self.ocr_engine:
            language = self.ocr_engine.getLanguage()
            text = self.readImage(clip)
            clip_type = self.ocr_engine.classify(text)

        x0, y0, x1, y1 = bounds
        x, y, width, height = graphics.getBoundsFromStartEndPoints((x0, y0),
                                                                   (x1, y1))

        data_box = DataBox(x, y, width, height, clip)
        data_box.setLanguage(language)
        if text:
            data_box.setText(text)
            data_box.setType(clip_type)

        if clip.mode == 'L':
            grayscale_clip = clip
        else:
            grayscale_clip = clip.convert('L')
        text_size = self.getTextSizeFromImage(grayscale_clip, page_resolution)

        if text_size:
            data_box.setFontSize(text_size)

        return data_box

    def getTextSizeFromImage(self, image, page_resolution):
        if image.mode != 'L':
            image = image.convert('L')
        width, height = image.size
        # We get the right half of the image only because this
        # way we avoid measuring eventual "initial chars" which
        # leads to false text sizes (obviously this will fail
        # for right-to-left languages)
        image_right_half = image.crop((width / 2, 0, width, height))
        text_size = graphics.getTextSizeFromImage(image_right_half)
        if not text_size:
            return None
        y_resolution = float(page_resolution)
        text_size /= y_resolution
        text_size *= DTP
        return round(text_size)

    def readImage(self, image):
        self.ocr_engine.setImage(image)
        text = self.ocr_engine.read()
        if self.clean_text:
            text = self.__cleanText(text)
        return text

    def __cleanText(self, text):
        clean_text = re.sub(r'(?<!-)-\n(?!\n)', r'', text)
        clean_text = re.sub(r'(?<!\n)\n', r' ', clean_text)
        return clean_text
