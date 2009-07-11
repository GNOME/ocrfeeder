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

import pygtk
pygtk.require('2.0')
import gtk, goocanvas
import os.path
import gobject
import gettext
_ = gettext.gettext

class SelectableBoxesArea(goocanvas.Canvas):
    
    __gtype_name__ = 'SelectableBoxesArea'
    
    __gsignals__ = {
        'selected_box' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,)),
        'removed_box' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,)),
        'updated_box' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,)),
        'dragged_box' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,)),
        'changed_zoom' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_FLOAT,))
        }
    
    def __init__(self, image_path):
        super(SelectableBoxesArea, self).__init__()
        self.image = goocanvas.Image()
        self.setBackgroundImage(image_path)
        self.grab_focus(self.image)
        self.set_bounds(0, 0, self.image.props.width, self.image.props.height)
        self.set_property('background-color-rgb', self.__rgbaToInteger((220, 218, 213, 255)))
        self.get_root_item().add_child(self.image, -1)
        self.area_fill_rgba = (94, 156, 235, 150)
        self.area_stroke_rgba = (94, 156, 235, 250)
        self.area_selected_stroke_rgba = (255, 255, 0, 255)
        self.image.connect('button_press_event', self.startSelectionArea)
        self.image.connect('button_release_event', self.endSelectionArea)
        self.image.connect('motion_notify_event', self.updateSelectionArea)
        self.image.connect('key_press_event', self.pressedKeyOnImage)
        self.selected_area = None
        self.currently_created_area = None
    
    def __rgbaToInteger(self, rgba):
        r, g, b, a = rgba
        return (r << 24) | (g << 16) | (b << 8) | a
    
    def __getRectangleFromPoints(self, start_point, end_point):
        start_x, start_y = start_point
        start_x, start_y = self.convert_from_pixels(start_x, start_y)
        end_x, end_y = end_point
        width = end_x - start_x
        height = end_y - start_y
        if width < 0:
            width = abs(width)
            start_x = end_x
        if height < 0:
            height = abs(height)
            start_y = end_y
        return start_x, start_y, width, height
    
    def setBackgroundImage(self, image_path):
        pixbuf = gtk.gdk.pixbuf_new_from_file(image_path)
        self.image.set_property('pixbuf', pixbuf)
    
    def setCurrentArea(self, area):
        self.set_data('current_area', area)
    
    def setSelectedArea(self, area):
        self.selected_area = area
    
    def getSelectedArea(self):
        return self.selected_area
    
    def selectArea(self, area):
        area.set_property('stroke_color_rgba',self.__rgbaToInteger(self.area_selected_stroke_rgba))
        self.grab_focus(area)
        area.connect('key_press_event', self.keyPressed)
    
    def deselectAreas(self):
        selected_area = self.selected_area
        if selected_area != None:
            selected_area.set_property('stroke_color_rgba',self.__rgbaToInteger(self.area_stroke_rgba))
        self.grab_focus(self.image)
    
    def zoom(self, zoom_value, add_zoom = True):
        new_zoom = zoom_value
        if add_zoom:
            current_zoom = self.get_scale()
            new_zoom = current_zoom + zoom_value
            if 2 > new_zoom > 0.2:
                self.set_scale(new_zoom)
        else:
            self.set_scale(new_zoom)
        self.emit('changed_zoom', self.get_scale())

    def getImageSize(self):
        return self.image.props.height, self.image.props.width
    
    def startSelectionArea(self, item, target, event):
        self.deselectAreas()
        fill_color = self.__rgbaToInteger(self.area_fill_rgba)
        stroke_color = self.__rgbaToInteger(self.area_stroke_rgba)
        self.currently_created_area = goocanvas.Rect(fill_color_rgba = fill_color, stroke_color_rgba = stroke_color)
        self.currently_created_area.props.x = event.x * self.get_scale()
        self.currently_created_area.props.y = event.y * self.get_scale()
        self.currently_created_area.set_data('start_point', (self.currently_created_area.props.x, self.currently_created_area.props.y))
        self.currently_created_area.connect('button_press_event', self.pressedWithinArea)
        self.currently_created_area.connect('button_release_event', self.releasedWithinArea)
        self.currently_created_area.connect('motion_notify_event', self.dragArea)
        self.get_root_item().add_child(self.currently_created_area, -1)
        return False
    
    def updateSelectionArea(self, item, target, event):
        if self.currently_created_area != None:
            start_point = self.currently_created_area.get_data('start_point')
            end_x = event.x
            end_y = event.y
            if event.x > self.image.props.width:
                end_x = self.image.props.width
            if event.y > self.image.props.height:
                end_y = self.image.props.height
            end_point = (end_x, end_y)
            x, y, width, height = self.__getRectangleFromPoints(start_point, end_point)
            self.currently_created_area.props.x = x
            self.currently_created_area.props.y = y
            self.currently_created_area.props.width = width
            self.currently_created_area.props.height = height
            return True
    
    def endSelectionArea(self, item, target, event):
        self.selected_area = None
        if self.currently_created_area != None:
            if self.currently_created_area.props.width < 5 or self.currently_created_area.props.height < 5:
                self.currently_created_area.remove()
                self.currently_created_area = None
                return False
        self.handleOverlapedAreas(self.getOverlapedAreas(self.currently_created_area))
        self.currently_created_area = None
    
    def getOverlapedAreas(self, area):
        offset = 2
        start_point = (area.props.x + 5, area.props.y + offset)
        end_point = (area.props.x + area.props.width - offset, area.props.y + area.props.height - offset)
        bounds = goocanvas.Bounds(*(start_point + end_point))
        overlaped_items = self.get_items_in_area(bounds, True, True, True)
        return overlaped_items
    
    def handleOverlapedAreas(self, overlaped_areas):
        for area in overlaped_areas:
            if isinstance(area, goocanvas.Rect) and area != self.currently_created_area and area != self.selected_area:
                area.remove()
                self.emit('removed_box', area)
    
    def keyPressed(self, item, rect, event):
        key_name = gtk.gdk.keyval_name(event.keyval).lower()
        if key_name in ['left', 'up', 'right', 'down']:
            fast_mask = gtk.gdk.SHIFT_MASK
            step = 2
            if event.state == fast_mask:
                step = 10
            if key_name == 'down':
                item.props.y += step
            elif key_name == 'up':
                item.props.y -= step
            elif key_name == 'right':
                item.props.x += step
            elif key_name == 'left':
                item.props.x -= step
            self.handleOverlapedAreas(self.getOverlapedAreas(item))
            self.emit('updated_box', item)
            return True
        if key_name == 'delete':
            item.remove()
            self.emit('removed_box', item)
    
    def pressedKeyOnImage(self, item, rect, event):
        key_name = gtk.gdk.keyval_name(event.keyval).lower()
        if key_name in ['up', 'down'] and event.state == gtk.gdk.CONTROL_MASK:
            if key_name == 'up':
                self.zoom(0.2)
                return True
            if key_name == 'down':
                self.zoom(-0.2)
                return True
    
    def pressedWithinArea(self, item, target, event):
        self.deselectAreas()
        self.selected_area = item
        self.selectArea(item)
        self.emit('selected_box', item)
        item.set_data('distance', (event.x - item.props.x, event.y - item.props.y))
        return True
    
    def releasedWithinArea(self, item, target, event):
        self.handleOverlapedAreas(self.getOverlapedAreas(item))
        item.set_data('distance', None)
        self.emit('updated_box', item)
    
    def dragArea(self, item, target, event):
        if item.get_data('distance'):
            distance_x, distance_y = item.get_data('distance')
            item.props.x = event.x - distance_x
            item.props.y = event.y - distance_y
            self.emit('dragged_box', item)
    
    def setAreaFillRgba(self, rgba):
        self.area_fill_rgba = rgba
    
    def setAreaStrokeRgba(self, rgba):
        self.area_stroke_rgba = rgba
    
    def addArea(self, dimensions):
        x, y, width, height = dimensions
        fill_color = self.__rgbaToInteger(self.area_fill_rgba)
        stroke_color = self.__rgbaToInteger(self.area_stroke_rgba)
        new_area = goocanvas.Rect(fill_color_rgba = fill_color, stroke_color_rgba = stroke_color)
        new_area.props.x = x
        new_area.props.y = y
        new_area.props.width = width
        new_area.props.height = height
        new_area.connect('button_press_event', self.pressedWithinArea)
        new_area.connect('button_release_event', self.releasedWithinArea)
        new_area.connect('motion_notify_event', self.dragArea)
        self.handleOverlapedAreas(self.getOverlapedAreas(new_area))
        self.get_root_item().add_child(new_area, -1)
        return new_area
    
    def clearAreas(self):
        areas = self.getAllAreas()
        for area in areas:
            area.remove()
    
    def getAllAreas(self):
        bounds = goocanvas.Bounds(*self.get_bounds())
        areas = [area for area in self.get_items_in_area(bounds, True, True, True) if isinstance(area, goocanvas.Rect)]
        return areas

class PlainFrame(gtk.Frame):
    
    def __init__(self, label):
        super(PlainFrame, self).__init__()
        label_widget = gtk.Label()
        label_widget.set_markup('<b>' + label + '</b>')
        self.set_label_widget(label_widget)
        self.container = gtk.Alignment(0, 0, 1, 1)
        self.container.set_padding(12, 0, 12, 12)
        super(PlainFrame, self).add(self.container)
        self.set_shadow_type(gtk.SHADOW_NONE)
    
    def add(self, widget):
        self.container.add(widget)

class SimpleStatusBar(gtk.Statusbar):
    
    def __init__(self):
        super(SimpleStatusBar, self).__init__()
        self.context_id = self.get_context_id('OCR Feeder')
    def insert(self, text):
        self.clear()
        self.push(self.context_id, text)
    
    def clear(self):
        self.pop(self.context_id)

class TrippleStatusBar(gtk.HBox):
    
    def __init__(self):
        super(TrippleStatusBar, self).__init__(spacing = 10)
        self.left_statusbar = SimpleStatusBar()
        self.left_statusbar.set_has_resize_grip(False)
        self.center_statusbar = SimpleStatusBar()
        self.center_statusbar.set_has_resize_grip(False)
        self.right_statusbar = SimpleStatusBar()
        self.add(self.left_statusbar)
        self.pack_start(gtk.VSeparator(), False)
        self.add(self.center_statusbar)
        self.pack_start(gtk.VSeparator(), False)
        self.add(self.right_statusbar)
        self.show_all()
    
    def clear(self):
        self.left_statusbar.clear()
        self.center_statusbar.clear()
        self.right_statusbar.clear()
