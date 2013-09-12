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

from gi.repository import Gtk

class PlainFrame(Gtk.Frame):

    def __init__(self, label):
        super(PlainFrame, self).__init__()
        label_widget = Gtk.Label()
        label_widget.set_markup('<b>' + label + '</b>')
        self.set_label_widget(label_widget)
        self._container = Gtk.Alignment.new(0, 0, 1, 1)
        self._container.set_padding(12, 0, 12, 12)
        super(PlainFrame, self).add(self._container)
        self.set_shadow_type(Gtk.ShadowType.NONE)

    def add(self, widget):
        self._container.add(widget)

class PlainExpander(Gtk.Expander):

    def __init__(self, label):
        super(PlainExpander, self).__init__()
        label_widget = Gtk.Label()
        label_widget.set_markup('<b>' + label + '</b>')
        self.set_label_widget(label_widget)
        self._container = Gtk.Alignment.new(0, 0, 1, 1)
        self._container.set_padding(12, 0, 12, 12)
        super(PlainExpander, self).add(self._container)
        self.set_expanded(False)

    def add(self, widget):
        self._container.add(widget)
