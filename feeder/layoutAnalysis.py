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

from util.lib import debug
from util.constants import OCRFEEDER_DEBUG 

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
        return xrange(self.start_line, self.finish_line + 1)
        
    def __getHorizontalRange(self):
        return xrange(self.first_one, self.last_one + 1)
    
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
        return leftmost_x, highest_y, rightmost_x, lowest_y
    
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