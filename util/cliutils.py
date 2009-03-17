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

import os.path

class ArgsRetriever:
    
    def __init__(self, args_list, command_prefix = '--', discard_first_arg = True):
        self.args_list = args_list
        self.command_prefix = command_prefix
        if discard_first_arg:
            del self.args_list[0]
    
    def getParams(self, command, failure_action = None):
        args = list(self.args_list)
        command_index = self.getCommandIndex(command)
        if command_index == -1:
            return failure_action or []
        if command_index == len(args) - 1:
            return []
        args = args[command_index + 1:]
        next_command = self.getNextCommand(args)
        if next_command == -1:
            return args
        return args[:next_command]
    
    def getNextCommand(self, args_list):
        i = 0
        for arg in args_list:
            if arg.startswith(self.command_prefix):
                return i
            i += 1
        return -1
    
    def getCommandIndex(self, command):
        command = command.strip(self.command_prefix)
        i = 0
        for arg in self.args_list:
            if arg == self.command_prefix + command:
                return i
            i += 1
        return -1
    
    def hasCommand(self, command):
        return self.getCommandIndex(command) != -1