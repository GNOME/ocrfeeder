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

    MINIMUM_ZOOM_HEIGHT = 50
    IMAGE_FRAME_THICKNESS = 5
    IMAGE_FRAME_COLOR = '#717171'

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
        'deselected_box' : (gobject.SIGNAL_RUN_LAST,
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
        self.frame = []
        self.setBackgroundImage(image_path)
        self.grab_focus(self.image)
        style = gtk.widget_get_default_style()
        self.set_property('background-color', style.bg[gtk.STATE_NORMAL].to_string())
        self.get_root_item().add_child(self.image, -1)
        self.area_fill_rgba = (94, 156, 235, 150)
        self.area_stroke_rgba = (94, 156, 235, 250)
        self.area_selected_stroke_rgba = (255, 255, 0, 255)
        self.image.connect('button_press_event', self.startSelectionArea)
        self.image.connect('button_release_event', self.endSelectionArea)
        self.image.connect('motion_notify_event', self.updateSelectionArea)
        self.image.connect('key_press_event', self.pressedKeyOnImage)
        self.connect('scroll-event', self.scrollEventCb)
        self.selected_areas = []
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
        self.set_bounds(0, 0, self.image.props.width * 2, self.image.props.height * 1.5)
        for line in self.frame:
            line.remove()
        self.__createFrame()
        for line in self.frame:
            self.get_root_item().add_child(line, -1)

    def __createFrame(self):
        line = goocanvas.Rect(fill_color = self.IMAGE_FRAME_COLOR, line_width = 0)
        line.props.x = self.image.props.x + self.image.props.width
        line.props.y = self.image.props.y
        line.props.width = self.IMAGE_FRAME_THICKNESS
        line.props.height = self.image.props.height + self.IMAGE_FRAME_THICKNESS
        self.frame.append(line)

        line = goocanvas.Rect(fill_color = self.IMAGE_FRAME_COLOR,
                              line_width = 0)
        line.props.x = self.image.props.x
        line.props.y = self.image.props.y + self.image.props.height
        line.props.width = self.image.props.width + 1
        line.props.height = self.IMAGE_FRAME_THICKNESS
        self.frame.append(line)

    def setCurrentArea(self, area):
        self.set_data('current_area', area)

    def setSelectedArea(self, area):
        self.selected_areas = [area]

    def getSelectedAreas(self):
        return self.selected_areas

    def selectAllAreas(self):
        areas = self.getAllAreas()
        for area in areas:
            self.selectArea(area)

    def selectArea(self, area):
        if area not in self.selected_areas:
            self.selected_areas.append(area)
        area.set_property('stroke_color_rgba',self.__rgbaToInteger(self.area_selected_stroke_rgba))
        self.grab_focus(area)
        area.connect('key_press_event', self.keyPressed)
        self.emit('selected_box', area)

    def deselectAreas(self):
        for selected_area in self.selected_areas:
            if selected_area != None:
                selected_area.set_property('stroke_color_rgba',
                                           self.__rgbaToInteger(self.area_stroke_rgba))
        # The deselectArea is not used in here for efficiency purposes
        while self.selected_areas:
            selected_area = self.selected_areas.pop(0)
            self.emit('deselected_box', selected_area)
        self.grab_focus(self.image)

    def deselectArea(self, area):
        if not area in self.selected_areas:
            return False
        if area != None:
            area.set_property('stroke_color_rgba',
                              self.__rgbaToInteger(self.area_stroke_rgba))
        self.selected_areas.remove(area)
        self.emit('deselected_box', area)
        return True

    def selectNextArea(self):
        self.__selectSurroundingArea(-1)

    def selectPreviousArea(self):
        self.__selectSurroundingArea(1)

    def deleteSelectedAreas(self):
        areas_to_remove = []
        while self.selected_areas:
            selected_area = self.selected_areas.pop(0)
            selected_area.remove()
            areas_to_remove.append(selected_area)
        self.get_window().set_cursor(None)
        for area in areas_to_remove:
            self.emit('removed_box', area)

    def __selectSurroundingArea(self, area_offset):
        areas = self.getAllAreas()
        if not areas:
            return
        area_index = self.__getCurrentSelectedAreaIndex(areas)
        area_index += area_offset
        if abs(area_index) >= len(areas):
            area_index = 0
        self.deselectAreas()
        self.selectArea(areas[area_index])

    def __getCurrentSelectedAreaIndex(self, areas):
        current_area = areas[0]
        if self.selected_areas:
            current_area = self.selected_areas[-1]
        area_index = areas.index(current_area)
        return area_index

    def zoom(self, zoom_value, add_zoom = True):
        new_zoom = zoom_value
        set_zoom = False
        if add_zoom:
            current_zoom = self.get_scale()
            new_zoom = current_zoom + zoom_value
            if new_zoom * self.image.props.height >= self.MINIMUM_ZOOM_HEIGHT:
                set_zoom = True
        else:
            if new_zoom * self.image.props.height >= self.MINIMUM_ZOOM_HEIGHT:
                set_zoom = True
        if set_zoom:
            self.set_scale(new_zoom)
            self.emit('changed_zoom', self.get_scale())

    def getImageSize(self):
        return self.image.props.height, self.image.props.width

    def startSelectionArea(self, item, target, event):
        if event.type != gtk.gdk.BUTTON_PRESS:
            return False
        self.deselectAreas()
        fill_color = self.__rgbaToInteger(self.area_fill_rgba)
        stroke_color = self.__rgbaToInteger(self.area_stroke_rgba)
        self.currently_created_area = Box(fill_color_rgba = fill_color, stroke_color_rgba = stroke_color)
        self.currently_created_area.props.x = event.x * self.get_scale()
        self.currently_created_area.props.y = event.y * self.get_scale()
        self.currently_created_area.set_data('start_point', (self.currently_created_area.props.x, self.currently_created_area.props.y))
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
            elif event.x < 0:
                end_x = 0
            if event.y > self.image.props.height:
                end_y = self.image.props.height
            elif event.y < 0:
                end_y = 0
            end_point = (end_x, end_y)
            x, y, width, height = self.__getRectangleFromPoints(start_point, end_point)
            self.currently_created_area.props.x = x
            self.currently_created_area.props.y = y
            self.currently_created_area.props.width = width
            self.currently_created_area.props.height = height
            return True

    def endSelectionArea(self, item, target, event):
        self.deselectAreas()
        if self.currently_created_area != None:
            if self.currently_created_area.props.width < 5 or self.currently_created_area.props.height < 5:
                self.currently_created_area.remove()
                self.currently_created_area = None
                return False
            self.handleOverlapedAreas(self.getOverlapedAreas(self.currently_created_area))
            self.deselectAreas()
            self.selectArea(self.currently_created_area)
        self.currently_created_area = None

    def getOverlapedAreas(self, area):
        offset = 2
        start_point = (area.props.x + 5, area.props.y + offset)
        end_point = (area.props.x + area.props.width - offset, area.props.y + area.props.height - offset)
        bounds = goocanvas.Bounds(*(start_point + end_point))
        overlaped_items = self.get_items_in_area(bounds, True, True, True)
        if area in overlaped_items:
            overlaped_items.remove(area)
        return overlaped_items

    def handleOverlapedAreas(self, overlaped_areas):
        for area in overlaped_areas:
            if isinstance(area, Box) and \
               area != self.currently_created_area and \
               not area in self.selected_areas:
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

    def pressedKeyOnImage(self, item, rect, event):
        key_name = gtk.gdk.keyval_name(event.keyval).lower()
        if key_name in ['up', 'down'] and event.state == gtk.gdk.CONTROL_MASK:
            if key_name == 'up':
                self.zoom(0.2)
                return True
            if key_name == 'down':
                self.zoom(-0.2)
                return True

    def releasedWithinArea(self, item, target, event):
        self.handleOverlapedAreas(self.getOverlapedAreas(item))
        self.emit('updated_box', item)

    def dragArea(self, item, target, event):
        self.emit('dragged_box', item)

    def scrollEventCb(self, widget, event):
        # Note: This catches all modifier combinations that use Ctrl. Add
        #       further combinations _before_ for them to take precedence!
        if event.state & gtk.gdk.CONTROL_MASK:
            if event.direction == gtk.gdk.SCROLL_UP or \
               event.direction == gtk.gdk.SCROLL_RIGHT:
                self.zoom(0.05)
                return True # we have handled the event - don't propagate to parent
            elif event.direction == gtk.gdk.SCROLL_DOWN or \
                 event.direction == gtk.gdk.SCROLL_LEFT:
                self.zoom(-0.05)
                return True # we have handled the event - don't propagate to parent
        elif event.state & gtk.gdk.SHIFT_MASK:
            event.state &= ~gtk.gdk.SHIFT_MASK
            if event.direction == gtk.gdk.SCROLL_UP:
                event.direction = gtk.gdk.SCROLL_LEFT
                return False # we have not handled the (new) event - propagate to parent
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                event.direction = gtk.gdk.SCROLL_RIGHT
                return False # we have not handled the (new) event - propagate to parent

    def setAreaFillRgba(self, rgba):
        self.area_fill_rgba = rgba

    def setAreaStrokeRgba(self, rgba):
        self.area_stroke_rgba = rgba

    def addArea(self, dimensions):
        x, y, width, height = dimensions
        fill_color = self.__rgbaToInteger(self.area_fill_rgba)
        stroke_color = self.__rgbaToInteger(self.area_stroke_rgba)
        new_area = Box(fill_color_rgba = fill_color, stroke_color_rgba = stroke_color)
        new_area.props.x = x
        new_area.props.y = y
        new_area.props.width = width
        new_area.props.height = height
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
        areas = [area for area in self.get_items_in_area(bounds, True, True, True) if isinstance(area, Box) and area not in self.frame]
        return areas

class Box(goocanvas.Rect):

    MOUSE_STATE_NORMAL = 0
    MOUSE_STATE_TOP_DRAG = 1 << 0
    MOUSE_STATE_BOTTOM_DRAG = 1 << 1
    MOUSE_STATE_LEFT_DRAG = 1 << 2
    MOUSE_STATE_RIGHT_DRAG = 1 << 3

    CURSOR_CHANGE_MAX_DISTANCE = 5
    __bottom_side_cursor = gtk.gdk.Cursor(gtk.gdk.BOTTOM_SIDE)
    __top_side_cursor = gtk.gdk.Cursor(gtk.gdk.TOP_SIDE)
    __left_side_cursor = gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
    __right_side_cursor = gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE)
    __top_left_cursor = gtk.gdk.Cursor(gtk.gdk.TOP_LEFT_CORNER)
    __top_right_cursor = gtk.gdk.Cursor(gtk.gdk.TOP_RIGHT_CORNER)
    __bottom_left_cursor = gtk.gdk.Cursor(gtk.gdk.BOTTOM_LEFT_CORNER)
    __bottom_right_cursor = gtk.gdk.Cursor(gtk.gdk.BOTTOM_RIGHT_CORNER)
    __drag_cursor = gtk.gdk.Cursor(gtk.gdk.FLEUR)

    def __init__(self, *args, **kwargs):
        super(Box, self).__init__(*args, **kwargs)
        self._state = self.MOUSE_STATE_NORMAL
        self.connect('motion-notify-event', self.__motionNotifyEventCb)
        self.connect('button-release-event', self.__buttonReleaseEventCb)
        self.connect('button-press-event', self.__buttonPressEventCb)
        # Reset the cursor
        self.connect('leave-notify-event', self.__leaveNotifyEventCb)

    def __leaveNotifyEventCb(self, item, target, event):
        if event.state & gtk.gdk.BUTTON1_MASK:
            return True
        self.__setNormalState()

    def __buttonPressEventCb(self, item, target, event):
        deselected = False
        if event.state & gtk.gdk.SHIFT_MASK == 0:
            self.get_canvas().deselectAreas()
        else:
            deselected = self.get_canvas().deselectArea(self)
        if deselected:
            return True
        self.get_canvas().selectArea(self)
        if self._state == self.MOUSE_STATE_NORMAL:
            self.get_canvas().get_window().set_cursor(self.__drag_cursor)
            self.set_data('distance', (event.x - self.props.x, event.y - self.props.y))
        return True

    def __buttonReleaseEventCb(self, item, target, event):
        self.set_data('distance', None)
        self.get_canvas().get_window().set_cursor(None)

    def __motionNotifyEventCb(self, item, target, event):
        if self.get_data('distance'):
            distance_x, distance_y = self.get_data('distance')
            new_x, new_y = event.x - distance_x, event.y - distance_y
        else:
            new_x, new_y = self.props.x, self.props.y
        if event.state & gtk.gdk.BUTTON1_MASK:
            old_y = int(self.props.y)
            old_x = int(self.props.x)
            if self._state & self.MOUSE_STATE_TOP_DRAG:
                new_x = -1
                new_y = self.props.y = max(0, int(event.y))
                new_height = self.props.height + old_y - new_y
                if new_height < 5:
                    self.props.y = old_y + self.props.height - 5
                    self._state &= ~self.MOUSE_STATE_TOP_DRAG
                    self._state |= self.MOUSE_STATE_BOTTOM_DRAG
                    self.__updateMouseCursor()
                else:
                    self.props.height = new_height
            if self._state & self.MOUSE_STATE_BOTTOM_DRAG:
                new_x = -1
                new_y = -1
                new_height = min(self.get_canvas().image.props.height, int(event.y)) \
                             - old_y
                if new_height < 5:
                    self.props.height = 5
                    self._state &= ~self.MOUSE_STATE_BOTTOM_DRAG
                    self._state |= self.MOUSE_STATE_TOP_DRAG
                    self.__updateMouseCursor()
                else:
                    self.props.height = new_height
            if self._state & self.MOUSE_STATE_LEFT_DRAG:
                new_x = max(0, int(event.x))
                new_y = -1
                self.props.x = new_x
                new_width = self.props.width + old_x - new_x
                if new_width < 5:
                    self.props.x = old_x + self.props.width - 5
                    self._state &= ~self.MOUSE_STATE_LEFT_DRAG
                    self._state |= self.MOUSE_STATE_RIGHT_DRAG
                    self.__updateMouseCursor()
                else:
                    self.props.width = new_width
            if self._state & self.MOUSE_STATE_RIGHT_DRAG:
                new_x = -1
                new_y = -1
                new_width = min(self.get_canvas().image.props.width, int(event.x)) \
                            - old_x
                if new_width < 5:
                    self.props.width = 5
                    self._state &= ~self.MOUSE_STATE_RIGHT_DRAG
                    self._state |= self.MOUSE_STATE_LEFT_DRAG
                    self.__updateMouseCursor()
                else:
                    self.props.width = new_width
            if self._state == self.MOUSE_STATE_NORMAL:
                self.props.x = new_x
                self.props.y = new_y
                self.__sanitizeBounds(new_x, new_y)
            return False

        self.__setMouseStateFromEvent(event)
        return True

    def __sanitizeBounds(self, new_x, new_y):
        if new_x != -1 and new_x <= self.get_canvas().image.props.x:
            self.props.x = self.get_canvas().image.props.x
        if new_x != -1 and new_x + self.props.width >= self.get_canvas().image.props.width:
            self.props.x = self.get_canvas().image.props.width - self.props.width
        if new_y != -1 and new_y <= self.get_canvas().image.props.y:
            self.props.y = self.get_canvas().image.props.y
        if new_y != -1 and new_y + self.props.height >= self.get_canvas().image.props.height:
            self.props.y = self.get_canvas().image.props.height - self.props.height

    def __setMouseStateFromEvent(self, event):
        cursor_max_distance = self.__getCursorMaxDistance()
        if abs(event.y - self.props.y) < cursor_max_distance:
            self.__setMouseState(self.MOUSE_STATE_TOP_DRAG, self.__top_side_cursor)
            if abs(event.x - self.props.x) < cursor_max_distance:
                self.__setMouseState(self.MOUSE_STATE_LEFT_DRAG | self.MOUSE_STATE_TOP_DRAG,
                                     self.__top_left_cursor)

            elif abs(event.x - (self.props.x + self.props.width)) < cursor_max_distance:
                self.__setMouseState(self.MOUSE_STATE_RIGHT_DRAG | self.MOUSE_STATE_TOP_DRAG,
                                     self.__top_right_cursor)

        elif abs(event.y - (self.props.y + self.props.height)) < cursor_max_distance:
            self.__setMouseState(self.MOUSE_STATE_BOTTOM_DRAG, self.__bottom_side_cursor)
            if abs(event.x - (self.props.x + self.props.width)) < cursor_max_distance:
                self.__setMouseState(self.MOUSE_STATE_RIGHT_DRAG | self.MOUSE_STATE_BOTTOM_DRAG,
                                     self.__bottom_right_cursor)

            elif abs(event.x - self.props.x) < cursor_max_distance:
                self.__setMouseState(self.MOUSE_STATE_LEFT_DRAG | self.MOUSE_STATE_BOTTOM_DRAG,
                                     self.__bottom_left_cursor)

        elif abs(event.x - self.props.x) < cursor_max_distance:
            self.__setMouseState(self.MOUSE_STATE_LEFT_DRAG, self.__left_side_cursor)
        elif abs(event.x - (self.props.x + self.props.width)) < cursor_max_distance:
            self.__setMouseState(self.MOUSE_STATE_RIGHT_DRAG, self.__right_side_cursor)

        else:
            self.__setNormalState()

    def __getCursorMaxDistance(self):
        return self.CURSOR_CHANGE_MAX_DISTANCE * (1 / self.get_canvas().get_scale())

    def __updateMouseCursor(self):
        window = self.get_canvas().get_window()
        if self._state & self.MOUSE_STATE_TOP_DRAG:
            if self._state & self.MOUSE_STATE_RIGHT_DRAG:
                window.set_cursor(self.__top_right_cursor)
                return
            if self._state & self.MOUSE_STATE_LEFT_DRAG:
                window.set_cursor(self.__top_left_cursor)
                return
            window.set_cursor(self.__top_side_cursor)
        elif self._state & self.MOUSE_STATE_BOTTOM_DRAG:
            if self._state & self.MOUSE_STATE_RIGHT_DRAG:
                window.set_cursor(self.__bottom_right_cursor)
                return
            if self._state & self.MOUSE_STATE_LEFT_DRAG:
                window.set_cursor(self.__bottom_left_cursor)
                return
            window.set_cursor(self.__bottom_side_cursor)
        elif self._state & self.MOUSE_STATE_RIGHT_DRAG:
            window.set_cursor(self.__right_side_cursor)
            return
        elif self._state & self.MOUSE_STATE_LEFT_DRAG:
            window.set_cursor(self.__left_side_cursor)
            return
        else:
            window.set_cursor(None)

    def __setMouseState(self, mouse_state, cursor):
        self._state = mouse_state
        self.get_canvas().get_window().set_cursor(cursor)

    def __setNormalState(self):
        self.__setMouseState(self.MOUSE_STATE_NORMAL, None)

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

class PlainExpander(gtk.Expander):

    def __init__(self, label):
        super(PlainExpander, self).__init__()
        label_widget = gtk.Label()
        label_widget.set_markup('<b>' + label + '</b>')
        self.set_label_widget(label_widget)
        self.container = gtk.Alignment(0, 0, 1, 1)
        self.container.set_padding(12, 0, 12, 12)
        super(PlainExpander, self).add(self.container)
        self.set_expanded(False)

    def add(self, widget):
        self.container.add(widget)
