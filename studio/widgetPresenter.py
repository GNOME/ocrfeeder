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

from customWidgets import PlainFrame, TrippleStatusBar
from dataHolder import DataBox, TEXT_TYPE, IMAGE_TYPE
from util import lib, PAPER_SIZES
from util.constants import *
from util.graphics import convertPixbufToImage
import Image
import gettext
import gobject
import goocanvas
import gtk
import os.path
import popen2
import pygtk
import signal
import subprocess
import threading
import time
pygtk.require('2.0')
_ = gettext.gettext

class MainWindow:
    
    menubar = '''<ui>
    <menubar name="MenuBar">
        <menu action="File">
            <menuitem action="OpenProject"/>
            <menuitem action="SaveProject"/>
            <menuitem action="SaveProjectAs"/>
            <separator/>
            <menuitem action="AppendProject"/>
            <separator/>
            <menuitem action="AddImage"/>
            <menuitem action="AddFolder"/>
            <separator/>
            <menuitem action="ImportPDF"/>
            <menuitem action="Export"/>
            <separator/>
            <menuitem action="Quit"/>
        </menu>
        <menu action="Edit">
            <menuitem action="EditPage"/>
            <menuitem action="DeletePage"/>
            <separator/>
            <menuitem action="ClearProject"/>
            <separator/>
            <menuitem action="Preferences"/>
        </menu>
        <menu action="View">
            <menuitem action="ZoomIn"/>
            <menuitem action="ZoomOut"/>
            <menuitem action="ResetZoom"/>
        </menu>
        <menu action="Document">
            <menuitem action="OCRFeederDetection"/>
        </menu>
        <menu action="Tools">
            <menuitem action="OCREngines"/>
            <separator/>
            <menuitem action="Unpaper"/>
        </menu>
        <menu action="Help">
            <menuitem action="About"/>
        </menu>
    </menubar>
    <toolbar name="ToolBar">
        <toolitem action="AddImage"/>
        <separator/>
        <toolitem action="OCRFeederDetection"/>
        <toolitem action="GenerateODT"/>
        <separator/>
        <toolitem action="ZoomOut"/>
        <toolitem action="ZoomIn"/>
    </toolbar>
    </ui>'''
    
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_size_request(800, 600)
        self.window.set_icon_from_file(WINDOW_ICON)
        self.main_box = gtk.VBox()
        self.main_box.show()
        
        self.tripple_statusbar = TrippleStatusBar()
        self.main_box.pack_end(self.tripple_statusbar, False)
        
        self.main_area = gtk.HPaned()
        self.main_area.set_position(150)
        self.main_area.show()
        self.main_box.pack_end(self.main_area)
        
        self.window.add(self.main_box)
        self.main_area_left = gtk.ScrolledWindow()
        self.main_area_left.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.main_area_left.show()
        
        self.main_area.pack1(self.main_area_left, False, False)
        self.notebook = gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.notebook.set_show_border(False)
        self.notebook.show()
        self.main_area.pack2(self.notebook, False, False)
        self.action_group = None
        
        self.window.show()
    def setTitle(self, new_title):
        self.window.set_title(new_title)
    
    def setHeader(self, menu_items, tool_items):
        ui_manager = gtk.UIManager()
        accel_group = ui_manager.get_accel_group()
        self.window.add_accel_group(accel_group)
        action_group = gtk.ActionGroup('MainWindow')
        action_group.add_actions([('File', None, _('_File')),
                                  ('Quit', gtk.STOCK_QUIT, _('_Quit'), None, _('Exit the program'), menu_items['exit']),
                                  ('OpenProject', gtk.STOCK_OPEN, _('_Open'), None, _('Open project'), menu_items['open_project']),
                                  ('SaveProject', gtk.STOCK_SAVE, _('_Save'), None, _('Save project'), menu_items['save_project']),
                                  ('SaveProjectAs', gtk.STOCK_SAVE_AS, _('_Save As') + '...', '<control><shift>s', _('Save project with a chosen name'), menu_items['save_project_as']),
                                  ('AddImage', gtk.STOCK_ADD, _('_Add Image'), None, _('Add another image'), menu_items['add_image']),
                                  ('AddFolder', gtk.STOCK_ADD, _('Add _Folder'), None, _('Add all images in a folder'), menu_items['add_folder']),
                                  ('AppendProject', gtk.STOCK_ADD, _('Append Project'), None, _('Load a project and append it to the current one'), menu_items['append_project']),
                                  ('ImportPDF', gtk.STOCK_ADD, _('_Import PDF'), None, _('Import PDF'), menu_items['import_pdf']),
                                  ('Export', None, _('_Export...'), '<control><shift>e', _('Export to a chosen format'), menu_items['export_dialog']),
                                  ('Edit', None, _('_Edit')),
                                  ('EditPage', gtk.STOCK_EDIT, _('_Edit Page'), None, _('Edit page settings'), menu_items['edit_page']),
                                  ('Preferences', gtk.STOCK_PREFERENCES, _('_Preferences'), None, _('Configure the application'), menu_items['preferences']),
                                  ('DeletePage', gtk.STOCK_DELETE, _('_Delete Page'), None, _('Delete current page'), menu_items['delete_page']),
                                  ('ClearProject', gtk.STOCK_DELETE, _('_Clear Project'), None, _('Delete all images'), menu_items['clear']),
                                  ('View', None, _('_View')),
                                  ('ZoomIn', gtk.STOCK_ZOOM_IN, _('Zoom In'), None, _("Zoom In"), menu_items['zoom_in']),
                                  ('ZoomOut', gtk.STOCK_ZOOM_OUT, _('Zoom Out'), None, _("Zoom Out"), menu_items['zoom_out']),
                                  ('ResetZoom', gtk.STOCK_ZOOM_100, _('Normal Size'), None, _("Normal Size"), menu_items['reset_zoom']),
                                  ('Document', None, _('_Document')),
                                  ('Tools', None, _('_Tools')),
                                  ('OCREngines', None, _('_OCR Engines'), None, _('Manage OCR engines'), menu_items['ocr_engines']),
                                  ('Unpaper', gtk.STOCK_EXECUTE, _('_Unpaper'), None, _('Process image with unpaper'), menu_items['unpaper']),
                                  ('Help', None, _('_Help')),
                                  ('About', gtk.STOCK_ABOUT, _('_About'), None, _('About this application'), menu_items['about']),
                                  ('OCRFeederDetection', None, _('_Recognize Document'), None, _("Automatic Detection and Recognition"), tool_items['detection']),
                                  ('GenerateODT', None, _('_Generate ODT'), None, _("Export to ODT"), tool_items['export_to_odt']),
                                  ])
        ui_manager.insert_action_group(action_group, 0)
        ui_manager.add_ui_from_string(self.menubar)
        menu_bar = ui_manager.get_widget('/MenuBar/')
        self.main_box.pack_start(menu_bar, False)
        tool_bar = ui_manager.get_widget('/ToolBar')
        
        self.main_box.pack_start(tool_bar, False, False)
        odt_export_button = ui_manager.get_widget('/ToolBar/GenerateODT')
        odt_export_button.set_icon_name('ooo-writer')
        detection_button = ui_manager.get_widget('/ToolBar/OCRFeederDetection')
        detection_icon = gtk.image_new_from_file(DETECT_ICON)
        detection_icon.show()
        detection_button.set_icon_widget(detection_icon)
        self.action_group = action_group
    
    def setDestroyEvent(self, function):
        self.window.connect('delete-event', function)
    
    def setHasImages(self, has_images = True):
        if not self.action_group:
            return
        actions = ['ZoomIn', 'ZoomOut', 'ResetZoom', 
                   'Export', 'GenerateODT', 'Unpaper', 
                   'DeletePage', 'SaveProject', 'SaveProjectAs',
                   'OCRFeederDetection']
        for gtkaction in [self.action_group.get_action(action) for action in actions]:
            gtkaction.set_sensitive(has_images)
        
class BoxEditor(gtk.ScrolledWindow):
    
    def __init__(self, image_width = 0, image_height = 0, pixbuf = 0, x = 0, y = 0, width = 0, height = 0, ocr_engines_list = []):
        super(BoxEditor, self).__init__()
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.contents = gtk.VBox()
        self.pixbuf = pixbuf
        self.image_window = gtk.ScrolledWindow()
        self.image_window.set_size_request(200, 200)
        self.image_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.x_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.setX(x)
        self.y_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.setY(y)
        self.width_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.setWidth(width)
        self.height_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.setHeight(height)
        
        self.make_text_button = self.__makeRadioButton(_('Text'), 'gnome-mime-text')
        self.make_image_button = self.__makeRadioButton(_('Image'), 'gnome-mime-image', self.make_text_button)
        box_type_frame = PlainFrame(_('Type'))
        box_type_table = gtk.Table(1, 2, True)
        box_type_table.attach(self.make_text_button, 0, 1, 0, 1)
        box_type_table.attach(self.make_image_button, 1, 2, 0, 1)
        box_type_frame.add(box_type_table)
        self.contents.pack_start(box_type_frame, False, False)
        
        self.image_width = image_width
        self.image_height = image_height
        
        image_frame = PlainFrame(_('Clip'))
        image_frame.add(self.image_window)
        self.contents.pack_start(image_frame, False, False)
        
        dimensions_frame = PlainFrame(_('Bounds'))
        
        dimensions_table = gtk.Table(2, 4, True)
        dimensions_table.attach(gtk.Label(_('X')), 0, 1, 0, 1)
        dimensions_table.attach(self.x_spin_button, 1, 2, 0, 1)
        dimensions_table.attach(gtk.Label(_('Y')), 2, 3, 0, 1)
        dimensions_table.attach(self.y_spin_button, 3, 4, 0, 1)
        
        dimensions_table.attach(gtk.Label(_('Width')), 0, 1, 1, 2)
        dimensions_table.attach(self.width_spin_button, 1, 2, 1, 2)
        dimensions_table.attach(gtk.Label(_('Height')), 2, 3, 1, 2)
        dimensions_table.attach(self.height_spin_button, 3, 4, 1, 2)
        
        dimensions_frame.add(dimensions_table)
        
        self.contents.pack_start(dimensions_frame, False, False)
        
        self.setXRange()
        self.setYRange()
        self.setWidthRange()
        self.setHeightRange()
        
        self.text_properties_frame = self.__makeOcrProperties(ocr_engines_list)        
        self.contents.pack_start(self.text_properties_frame, False, False)
        
        self.contents.set_spacing(10)
        self.add_with_viewport(self.contents)
        self.show_all()
    
    def displayImage(self, pixbuf):
        for child in self.image_window.get_children():
            self.image_window.remove(child)
        self.pixbuf = pixbuf
        image = gtk.image_new_from_pixbuf(self.pixbuf)
        image.show()
        self.image_window
        self.image_window.add_with_viewport(image)
    
    def setX(self, x_value):
        self.x_spin_button.set_value(x_value)
    
    def setY(self, y_value):
        self.y_spin_button.set_value(y_value)
    
    def getX(self):
        return self.x_spin_button.get_value()
    
    def getY(self):
        return self.y_spin_button.get_value()
    
    def setWidth(self, width_value):
        self.width_spin_button.set_value(width_value)
    
    def setHeight(self, height_value):
        self.height_spin_button.set_value(height_value)
    
    def getWidth(self):
        return self.width_spin_button.get_value()
    
    def getHeight(self):
        return self.height_spin_button.get_value()
    
    def setWidthRange(self):
        max = self.image_width - self.getX()
        self.width_spin_button.set_range(5, max)
        
    def setHeightRange(self):
        max = self.image_height - self.getY()
        self.height_spin_button.set_range(5, max)
    
    def setXRange(self):
        max = int(self.getX()) + (self.image_width - int((self.getX() + self.getWidth())))
        self.x_spin_button.set_range(5, max)
        
    def setYRange(self):
        max = self.image_height - (self.getY() + self.getHeight())
        self.y_spin_button.set_range(5, max)
    
    def getImage(self):
        return self.pixbuf
    
    def getSelectedOcrEngine(self):
        return self.ocr_combo_box.get_active()
    
    def selectOcrEngine(self, index):
        if index != -1:
            self.ocr_combo_box.set_active(index)
    
    def checkBoundsEquality(self, x, y, width, height):
        return x == self.x_spin_button.get_value() and \
                y == self.y_spin_button.get_value() and \
                width == self.width_spin_button.get_value() and \
                height == self.height_spin_button.get_value()
    
    def __makeRadioButton(self, label, icon_name, group_button = None):
        new_radio_button = gtk.RadioButton(group_button)
        new_radio_button.set_relief(gtk.RELIEF_NONE)
        new_radio_button.set_focus_on_click(False)
        theme = gtk.icon_theme_get_default()
        if theme.lookup_icon(icon_name, gtk.ICON_SIZE_SMALL_TOOLBAR, gtk.ICON_LOOKUP_USE_BUILTIN):
            new_radio_button.set_image(gtk.image_new_from_icon_name(icon_name, gtk.ICON_SIZE_SMALL_TOOLBAR))
        new_radio_button.set_label(label)
        
        return new_radio_button
    
    def __makeAlignButtons(self):
        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_LEFT, _('Left'))
        self.align_left_button = gtk.RadioToolButton()
        self.align_left_button.set_label(label)
        self.align_left_button.set_icon_widget(icon)
        self.align_left_button.set_tooltip_text(_('Left aligned'))
        
        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_CENTER, _('Center'))
        self.align_center_button = gtk.RadioToolButton()
        self.align_center_button.set_label(label)
        self.align_center_button.set_icon_widget(icon)
        self.align_center_button.set_group(self.align_left_button)
        self.align_center_button.set_tooltip_text(_('Centered'))
        
        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_RIGHT, _('Right'))
        self.align_right_button = gtk.RadioToolButton()
        self.align_right_button.set_label(label)
        self.align_right_button.set_icon_widget(icon)
        self.align_right_button.set_group(self.align_left_button)
        self.align_right_button.set_tooltip_text(_('Right aligned'))
        
        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_FILL, _('Fill'))
        self.align_fill_button = gtk.RadioToolButton()
        self.align_fill_button.set_label(label)
        self.align_fill_button.set_icon_widget(icon)
        self.align_fill_button.set_group(self.align_left_button)
        self.align_fill_button.set_tooltip_text(_('Filled'))
        
        return self.align_left_button, self.align_center_button, self.align_right_button, self.align_fill_button
    
    def __makeOcrProperties(self, engines):
        hbox = gtk.HBox()
        self.perform_ocr_button = gtk.Button(_('OCR'))
        icon = gtk.image_new_from_stock(gtk.STOCK_OK, gtk.ICON_SIZE_BUTTON)
        self.perform_ocr_button.set_image(icon)
        self.ocr_combo_box = gtk.combo_box_new_text()
        self.setOcrEngines(engines)
        self.ocr_combo_box.set_active(0)
        hbox.pack_end(self.perform_ocr_button, False, False)
        hbox.add(self.ocr_combo_box)
        
        # Text Properties
        text_properties_frame = PlainFrame(_('Text Properties'))
        text_properties_notebook = gtk.Notebook()
        text_properties_notebook.set_tab_pos(gtk.POS_TOP)
        # Textview widget
        self.text_widget = gtk.TextView()
        self.text_content = self.text_widget.get_buffer()
        scrolled_text = gtk.ScrolledWindow()
        scrolled_text.add(self.text_widget)
        text_properties_notebook.append_page(scrolled_text, gtk.Label( _('Text')))
        text_properties_notebook.set_tab_reorderable(scrolled_text, True)
        
        # Style widget
        self.font_button = gtk.FontButton()
        vbox = gtk.VBox()
        font_selection_frame = PlainFrame(_('Font'))
        font_selection_frame.add(self.font_button)
        vbox.pack_start(font_selection_frame, False, False)
        
        align_buttons_box = gtk.HBox()
        for button in self.__makeAlignButtons():
            align_buttons_box.pack_start(button, False)
        align_buttons_frame = PlainFrame(_('Align'))
        align_buttons_frame.add(align_buttons_box)
        vbox.pack_start(align_buttons_frame, False)
        
        spacing_frame = PlainFrame(_('Spacing'))
        self.letter_spacing_spin = gtk.SpinButton(gtk.Adjustment(0.0, 0.0, 5000.0, 0.5, 100.0, 0.0), 1.0, 1)
        self.line_spacing_spin = gtk.SpinButton(gtk.Adjustment(0.0, 0.0, 5000.0, 0.5, 100.0, 0.0), 1.0, 1)
        spacing_table = gtk.Table(2,2)
        spacing_table.attach(gtk.Label(_('Line')), 0, 1, 0, 1)
        spacing_table.attach(self.line_spacing_spin, 1, 2, 0, 1)
        spacing_table.attach(gtk.Label(_('Letter')), 0, 1, 1, 2)
        spacing_table.attach(self.letter_spacing_spin, 1, 2, 1, 2)
        spacing_frame.add(spacing_table)
        vbox.pack_start(spacing_frame, False)
        
        text_properties_notebook.append_page(vbox, gtk.Label( _('Style')))
        text_properties_notebook.set_tab_reorderable(vbox, True)
        
        angle_box = self.__makeAngleProperty()
        if OCRFEEDER_ANGLE:
            text_properties_notebook.append_page(angle_box, gtk.Label( _('Angle')))
            text_properties_notebook.set_tab_reorderable(angle_box, True)
        
        vbox = gtk.VBox()
        vbox.pack_start(hbox, False, False)
        vbox.add(text_properties_notebook)
        text_properties_frame.add(vbox)
        return text_properties_frame
    
    def __makeAngleProperty(self):
        self.angle_spin = gtk.SpinButton(gtk.Adjustment(0.0, -360.0, 360.0, 0.1, 100.0, 0.0), 1.0, 1)
        self.detect_angle_button = gtk.Button(_('Detect'))
        hbox = gtk.HBox()
        hbox.add(gtk.Label(_('Angle') + ':'))
        hbox.add(self.angle_spin)
        vbox = gtk.VBox()
        vbox.pack_start(hbox, False)
        vbox.pack_start(self.detect_angle_button, False)
        return vbox
        
    
    def setFontSize(self, size):
        font_name = self.font_button.get_font_name().split(' ')
        font_name[-1] = str(size)
        self.font_button.set_font_name(' '.join(font_name))
    
    def setLineSpacing(self, spacing):
        self.line_spacing_spin.set_value(spacing)
    
    def setOcrEngines(self, engines_list):
        self.ocr_combo_box.get_model().clear()
        for engine in engines_list:
            self.ocr_combo_box.append_text(engine)
        if engines_list:
            self.ocr_combo_box.set_active(0)
    
    def setType(self, new_type):
        if new_type == TEXT_TYPE:
            self.make_text_button.set_active(True)
        elif new_type == IMAGE_TYPE:
            self.make_image_button.set_active(True)
    
    def getType(self):
        if self.make_image_button.get_active():
            return IMAGE_TYPE
        else:
            return TEXT_TYPE
    
    def setOcrPropertiesSensibility(self, status):
        self.text_properties_frame.set_sensitive(status)
    
    def setText(self, text):
        self.text_content.set_text(str(text).strip())
    
    def getText(self):
        start = self.text_content.get_start_iter()
        end = self.text_content.get_end_iter()
        return self.text_content.get_text(start, end)
    
    def setAngle(self, angle):
        self.angle_spin.set_value(angle)
    
    def getAngle(self):
        return self.angle_spin.get_value()
    
    def getFontFace(self):
        return self.font_button.get_font_name()

class BoxEditor_DataBox_Controller:
    
    def __init__(self, notebook):
        self.notebook = notebook
        self.boxes_list = []
    
    def addEditor(self, pixbuf, box):
        x, y, width, height = box.props.x, box.props.y, box.props.width, box.props.height
        sub_pixbuf = pixbuf.subpixbuf(x, y, width, height)
        box_editor = BoxEditor(sub_pixbuf, x, y, width, height)
        data_box = DataBox(x, y, width, height, sub_pixbuf)
        self.boxes_list.append((box, box_editor, data_box))
        self.notebook.append_page(box_editor, None)
    
    def removeEditor(self, box):
        for i in xrange(len(self.boxes_list)):
            editor_data = self.boxes_list[i]
            if editor_data[0] == box:
                box.remove()
                page_num = self.notebook.page_num(editor_data[1])
                self.notebook.remove_page(page_num)
                del self.boxes_list[i]

class FileDialog(gtk.FileChooserDialog):
    
    def __init__(self, type = 'open', current_folder = '~', filename = None, file_filters = []):
        dialog_type = gtk.FILE_CHOOSER_ACTION_SAVE
        title = _('Save File')
        button = gtk.STOCK_SAVE
        if type == 'open':
            title = _('Open File')
            dialog_type = gtk.FILE_CHOOSER_ACTION_OPEN
            button = gtk.STOCK_OPEN
        elif type == 'select-folder':
            title = _('Open Folder')
            dialog_type = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
            button = gtk.STOCK_OPEN
        super(FileDialog, self).__init__(title = title, action = dialog_type, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, 
                                                                                        button, gtk.RESPONSE_OK))
        self.set_current_folder(os.path.expanduser(current_folder))
        if filename:
            self.set_filename(filename)
        for file_filter in file_filters:
            filter = gtk.FileFilter()
            filter.set_name(file_filter[0])
            for mimetype in file_filter[1]:
                filter.add_mime_type(mimetype)
            for pattern in file_filter[2]:
                filter.add_pattern(pattern)
            self.add_filter(filter)
        self.set_icon_from_file(WINDOW_ICON)

class PagesToExportDialog(gtk.Dialog):
    
    def __init__(self, title = None):
        super(PagesToExportDialog, self).__init__(title, flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.__makePageSelectionArea()
        self.set_icon_from_file(WINDOW_ICON)
    
    def __makePageSelectionArea(self):
        page_selection_frame = PlainFrame(_('Pages to export'))
        vbox = gtk.VBox()
        self.all_pages_button = gtk.RadioButton(None, _('All'))
        self.current_page_button = gtk.RadioButton(self.all_pages_button, _('Current'))
        vbox.pack_start(self.all_pages_button)
        vbox.pack_start(self.current_page_button)
        page_selection_frame.add(vbox)
        page_selection_frame.show_all()
        self.vbox.add(page_selection_frame)

class ExportDialog(gtk.Dialog):

    def __init__(self, title = None, format_choices = []):
        super(ExportDialog, self).__init__(title, flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.__makeFormatSelectionArea(format_choices)
        self.set_icon_from_file(WINDOW_ICON)
    
    def __makeFormatSelectionArea(self, format_choices):
        page_selection_frame = PlainFrame(_('Choose the format'))
        vbox = gtk.VBox()
        self.format_combo = gtk.combo_box_new_text()
        for format in format_choices:
            self.format_combo.append_text(format)
        self.format_combo.set_active(0)
        vbox.pack_start(self.format_combo, False)
        page_selection_frame.add(vbox)
        page_selection_frame.show_all()
        self.vbox.add(page_selection_frame)
    
    def getSelectedFormat(self):
        return self.format_combo.get_active_text()

class PageSizeDialog(gtk.Dialog):
    
    def __init__(self, current_page_size):
        super(PageSizeDialog, self).__init__(_('Page size'), flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.__makePageSizeArea(current_page_size)
        self.paper_sizes.connect('changed', self.__changedPageSize, current_page_size)
        self.set_icon_from_file(WINDOW_ICON)
    
    def __makePageSizeArea(self, page_size):
        page_size_frame = PlainFrame(_('Page size'))
        size_box = gtk.VBox(spacing = 12)
        self.paper_sizes = gtk.combo_box_new_text()
        papers = PAPER_SIZES.keys()
        papers.sort()
        self.paper_sizes.append_text(_('Custom') + '...')
        for paper in papers:
            self.paper_sizes.append_text(paper)
        active_index = self.__checkIfSizeIsStandard(page_size)
        self.paper_sizes.set_active(active_index)
        self.width_entry = gtk.SpinButton(gtk.Adjustment(0.0, 1.0, 100000.0, 0.1, 100.0, 0.0), 1.0, 1)
        self.height_entry = gtk.SpinButton(gtk.Adjustment(0.0, 1.0, 100000.0, 0.1, 100.0, 0.0), 1.0, 1)
        size_box.pack_start(self.paper_sizes, False)
        self.entries_hbox = gtk.HBox()
        self.entries_hbox.add(gtk.Label(_('Width')))
        self.entries_hbox.add(self.width_entry)
        self.entries_hbox.add(gtk.Label(_('Height')))
        self.entries_hbox.add(self.height_entry)
        size_box.add(self.entries_hbox)
        page_size_frame.add(size_box)
        self.vbox.add(page_size_frame)
        
        affected_pages_frame = PlainFrame(_('Affected pages'))
        affected_pages_box = gtk.VBox()
        self.current_page_radio = gtk.RadioButton(None, _('Current'))
        self.all_pages_radio = gtk.RadioButton(self.current_page_radio, _('All'))
        affected_pages_box.pack_start(self.current_page_radio, False)
        affected_pages_box.pack_start(self.all_pages_radio, False)
        affected_pages_frame.add(affected_pages_box)
        self.vbox.add(affected_pages_frame)
        
        self.vbox.show_all()
        if active_index == 0:
            self.__setPageSize(page_size)
        else:
            self.__setPageSize(PAPER_SIZES[self.paper_sizes.get_active_text()])
            self.entries_hbox.set_sensitive(False)
    
    def __setPageSize(self, page_size):
        width, height = page_size
        self.width_entry.set_value(width)
        self.height_entry.set_value(height)
    
    def getSize(self):
        return self.width_entry.get_value(), self.height_entry.get_value()
    
    def __changedPageSize(self, widget, current_page_size):
        active_index = self.paper_sizes.get_active()
        self.entries_hbox.set_sensitive(not active_index)
        if active_index:
            width, height = PAPER_SIZES[self.paper_sizes.get_active_text()]
            self.__setPageSize((width, height))
    
    def __checkIfSizeIsStandard(self, page_size):
        width, height = page_size
        i = 1
        names = PAPER_SIZES.keys()
        names.sort()
        for name in names:
            size = PAPER_SIZES[name]
            standard_width, standard_height = size
            if abs(standard_width - width) < 0.2 > abs(standard_height - height):
                return i
            i += 1
        return 0

class QuestionDialog(gtk.MessageDialog):
    
    def __init__(self, message, buttons = gtk.BUTTONS_YES_NO):
        super(QuestionDialog, self).__init__(type = gtk.MESSAGE_QUESTION, buttons = buttons)
        self.set_icon_from_file(WINDOW_ICON)
        self.set_markup(message)

class UnpaperDialog(gtk.Dialog):
    
    def __init__(self, reviewer , unpaper, temp_dir = '/tmp'):
        super(UnpaperDialog, self).__init__(_('Unpaper Image Processor'), flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.options_box = gtk.VBox()
        self.reviewer = reviewer
        self.unpaper = unpaper
        self.temp_dir = temp_dir
        self.unpapered_image = None
        self.__makeBlackFilter()
        self.__makeNoiseFilter()
        self.__makeGrayFilter()
        self.__makeExtraOptions()
        self.noise_filter_custom.connect('toggled', self.__toggleNoiseFilterIntensity)
        self.gray_filter_custom.connect('toggled', self.__toggleGrayFilterIntensity)
        self.__makePreviewArea()
        self.set_icon_from_file(WINDOW_ICON)
        self.vbox.show_all()
        self.preview.connect('clicked', self.__getPreview)
        self.set_size_request(500, -1)
    
    def __makeNoiseFilter(self):
        
        noise_filter_frame = PlainFrame(_('Noise Filter Intensity'))
        noise_filter_box = gtk.VBox()
        self.noise_filter_default = gtk.RadioButton(None, _('Default'))
        self.noise_filter_custom = gtk.RadioButton(self.noise_filter_default, _('Custom'))
        self.noise_filter_none = gtk.RadioButton(self.noise_filter_custom, _('None'))
        self.noise_filter_intensity = gtk.SpinButton(gtk.Adjustment(0, 1, 1000, 1, 100, 0), 1, 1)
        self.noise_filter_intensity.set_sensitive(False)
        noise_filter_custom_box = gtk.HBox()
        noise_filter_custom_box.add(self.noise_filter_custom)
        noise_filter_custom_box.add(self.noise_filter_intensity)
        noise_filter_box.pack_start(self.noise_filter_default, False)
        noise_filter_box.pack_start(noise_filter_custom_box, False)
        noise_filter_box.pack_start(self.noise_filter_none, False)
        noise_filter_frame.add(noise_filter_box)
        self.options_box.pack_start(noise_filter_frame, False)
    
    def __makeGrayFilter(self):
        
        gray_filter_frame = PlainFrame(_('Gray Filter Size'))
        gray_filter_box = gtk.VBox()
        self.gray_filter_default = gtk.RadioButton(None, _('Default'))
        self.gray_filter_custom = gtk.RadioButton(self.gray_filter_default, _('Custom'))
        self.gray_filter_none = gtk.RadioButton(self.gray_filter_custom, _('None'))
        self.gray_filter_size = gtk.SpinButton(gtk.Adjustment(0, 1, 1000, 1, 100, 0), 1, 1)
        self.gray_filter_size.set_sensitive(False)
        gray_filter_custom_box = gtk.HBox()
        gray_filter_custom_box.add(self.gray_filter_custom)
        gray_filter_custom_box.add(self.gray_filter_size)
        gray_filter_box.pack_start(self.gray_filter_default, False)
        gray_filter_box.pack_start(gray_filter_custom_box, False)
        gray_filter_box.pack_start(self.gray_filter_none, False)
        gray_filter_frame.add(gray_filter_box)
        self.options_box.pack_start(gray_filter_frame, False)
    
    def __makeBlackFilter(self):
        
        black_filter_frame = PlainFrame(_('Black Filter'))
        self.black_filter_usage = gtk.CheckButton(_('Use'))
        self.black_filter_usage.set_active(True)
        black_filter_frame.add(self.black_filter_usage)
        self.options_box.pack_start(black_filter_frame, False)
    
    def __makePreviewArea(self):
        preview_frame = PlainFrame(_('Preview'))
        preview_box = gtk.VBox()
        self.preview_area = gtk.ScrolledWindow()
        self.preview_area.set_shadow_type(gtk.SHADOW_IN)
        self.preview_area.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.preview_area.set_size_request(200, 250)
        self.preview = gtk.Button(_('Preview'))
        preview_box.pack_start(self.preview_area, False)
        preview_box.pack_start(self.preview, False)
        preview_frame.add(preview_box)
        main_area = gtk.HBox()
        main_area.pack_start(preview_frame, False, padding = 10)
        main_area.add(self.options_box)
        self.vbox.add(main_area)
    
    def __makeExtraOptions(self):
        options_frame = PlainFrame(_('Extra Options'))
        self.extra_options = gtk.Entry()
        options_frame.add(self.extra_options)
        self.options_box.pack_start(options_frame, False)
    
    def __getPreview(self, widget):
        self.performUnpaper()
        self.__getPreviewImage(self.unpapered_image)
    
    def performUnpaper(self):
        image = convertPixbufToImage(self.reviewer.image_pixbuf)
        image_name = os.path.basename(self.reviewer.path_to_image)
        name, ext = os.path.splitext(image_name)
        name = os.path.join(self.temp_dir, name) + '.ppm'
        if os.path.exists(name):
            os.remove(name)
        image.save(name, format = 'PPM')
        command = '%s --layout single' % self.unpaper
        if not self.black_filter_usage.get_active():
            command += ' --no-blackfilter'
        if self.noise_filter_none.get_active():
            command += ' --no-noisefilter'
        elif self.noise_filter_custom.get_active():
            command += ' --noisefilter-intensity %s' % self.noise_filter_intensity.get_value()
        if self.gray_filter_none.get_active():
            command += ' --no-grayfilter'
        elif self.gray_filter_custom.get_active():
            command += ' --grayfilter-size %s' % self.gray_filter_size.get_value()
        extra_options_text = self.extra_options.get_text()
        if extra_options_text.strip():
            command += ' %s ' % extra_options_text
        unpapered_image = os.path.splitext(name)[0] + '_unpapered.ppm'
        unpapered_image = lib.getNonExistingFileName(unpapered_image)
        command += ' %s %s' % (name, unpapered_image)
        progress_bar = CommandProgressBarDialog(command, _('Performing Unpaper'), _('Performing unpaper. Please wait...'))
        progress_bar.run()
        self.unpapered_image = unpapered_image
    
    def __getPreviewImage(self, image_path):
        name = os.path.splitext(image_path)[0]
        thumbnail_image = Image.open(image_path)
        thumbnail_image.thumbnail((150, 200), Image.ANTIALIAS)
        image_thumbnail_path = lib.getNonExistingFileName(name + '_thumb.png')
        thumbnail_image.save(image_thumbnail_path, format = 'PNG')
        image = gtk.image_new_from_file(image_thumbnail_path)
        image.show()
        for child in self.preview_area.get_children():
            self.preview_area.remove(child)
        self.preview_area.add_with_viewport(image)
    
    def __toggleNoiseFilterIntensity(self, widget):
        self.noise_filter_intensity.set_sensitive(self.noise_filter_custom.get_active())
    
    def __toggleGrayFilterIntensity(self, widget):
        self.gray_filter_size.set_sensitive(self.gray_filter_custom.get_active())
    
    def getUnpaperedImage(self):
        if not self.unpapered_image:
            self.performUnpaper()
        return self.unpapered_image

class SimpleDialog(gtk.MessageDialog):
    
    def __init__(self, message, title = '', type = 'info'):
        message_type = gtk.MESSAGE_INFO
        if type == 'warning':
            message_type = gtk.MESSAGE_WARNING
        super(SimpleDialog, self).__init__(type = message_type, buttons = gtk.BUTTONS_OK)
        self.set_title(title)
        self.set_markup(message)
        self.set_icon_from_file(WINDOW_ICON)
    
    def run(self):
        super(SimpleDialog, self).run()
        self.destroy()

class CommandProgressBarDialog(gtk.Dialog):
    
    def __init__(self, command, title = '', label = ''):
        super(CommandProgressBarDialog, self).__init__(_(title), flags = gtk.DIALOG_MODAL)
        self.__makeProgressBar(label)
        self.vbox.show_all()
        self.command = command
        self.process = None
        self.set_size_request(300, -1)
    
    def __makeProgressBar(self, label):
        self.vbox.add(gtk.Label(label))
        self.progress_bar = gtk.ProgressBar()
        self.vbox.pack_start(self.progress_bar, False)
    
    def run(self):
        if self.__startPulse():
            super(CommandProgressBarDialog, self).run()
    
    def cancel(self):
        if self.process:
            os.kill(self.process.pid, signal.SIGKILL)
        self.destroy()
    
    def __startPulse(self):
        try:
            self.process = subprocess.Popen(self.command.split(), stdout = subprocess.PIPE, stderr = subprocess.STDOUT, bufsize=1)
        except:
            warning = SimpleDialog(_('An error occured!'), _('Error'), 'warning')
            warning.run()
            return False
        self.timer = gobject.timeout_add(100, self.__pulse)
        return True
    
    def __pulse(self):
        self.progress_bar.pulse()
        exit_value = self.process.poll()
        if exit_value != None:
            if exit_value != 0:
                warning = SimpleDialog(_('An error occured!'), _('Error'), 'warning')
                warning.run()
            self.destroy()
            return False
        return True

class PreferencesDialog(gtk.Dialog):
    
    def __init__(self, configuration_manager, ocr_engines):
        super(PreferencesDialog, self).__init__(_('Preferences'), flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.configuration_manager = configuration_manager
        self.ocr_engines = ocr_engines
        self.notebook = gtk.Notebook()
        self.__makeGeneralPreferences(self.__makeTemporaryFolder(), 
                                      self.__makeWindowSize())
        self.__makeAppearancePreferences(self.__makeColors())
        self.__makeToolsPreferences(self.__makeUnpaper(),
                                    self.__makeEngines())
        self.temporary_folder_button.connect('clicked', self.__folderSelectDialog)
        self.unpaper_select.connect('clicked', self.__unpaperSelectDialog)
        self.custom_window_size.connect('toggled', self.__toggledCustomWindowSize)
        self.vbox.add(self.notebook)
        self.set_icon_from_file(WINDOW_ICON)
        self.vbox.show_all()
    
    def __getTemporaryDir(self):
        temp_dir = self.temporary_folder.get_text()
        if not os.path.isdir(temp_dir):
            return self.configuration_manager.getDefault('temporary_dir')
        return temp_dir
    
    def __getWindowSize(self):
        if self.custom_window_size.get_active():
            return self.custom_window_size_entry.get_value()
        return 'auto'
    
    def __getColor(self, color_button):
        red, green, blue, alpha = color_button.get_color().red, color_button.get_color().green, color_button.get_color().blue, color_button.get_alpha()
        return (red >> 8, green >> 8, blue >> 8, alpha >> 8)
    
    def saveToManager(self):
        self.configuration_manager.setTemporaryDir(self.__getTemporaryDir())
        self.configuration_manager.setWindowSize(self.__getWindowSize())
        self.configuration_manager.setTextFill(self.__getColor(self.text_fill_color))
        self.configuration_manager.setTextStroke(self.__getColor(self.text_stroke_color))
        self.configuration_manager.setImageFill(self.__getColor(self.image_fill_color))
        self.configuration_manager.setImageStroke(self.__getColor(self.image_stroke_color))
        self.configuration_manager.setUnpaper(self.unpaper_entry.get_text())
        index = self.engines_combo.get_active()
        if index != -1:
            lib.debug('ACTIVE INDEX: ', index, self.ocr_engines[index].name)
            self.configuration_manager.setFavoriteEngine(self.ocr_engines[index].name)
    
    def __makeGeneralPreferences(self, *args):
        general_box = gtk.VBox(spacing = 10)
        for arg in args:
            general_box.pack_start(arg, False)
        self.notebook.append_page(general_box, gtk.Label(_('General')))
    
    def __makeTemporaryFolder(self):
        temporary_dir_frame = PlainFrame(_('Temporary folder'))
        self.temporary_folder = gtk.Entry()
        self.temporary_folder.set_text(self.configuration_manager.temporary_dir)
        self.temporary_folder.set_width_chars(30)
        self.temporary_folder_button = gtk.Button(_('Choose'), gtk.STOCK_OPEN)
        temporary_folder_hbox = gtk.HBox()
        temporary_folder_hbox.pack_start(self.temporary_folder, False)
        temporary_folder_hbox.pack_start(self.temporary_folder_button, False)
        temporary_dir_frame.add(temporary_folder_hbox)
        return temporary_dir_frame
    
    def __folderSelectDialog(self, widget):
        folder_select_dialog = FileDialog('select-folder')
        if folder_select_dialog.run() == gtk.RESPONSE_OK:
            self.temporary_folder.set_text(folder_select_dialog.get_filename())
        folder_select_dialog.destroy()
    
    def __makeAppearancePreferences(self, *args):
        general_box = gtk.VBox(spacing = 10)
        for arg in args:
            general_box.pack_start(arg, False)
        self.notebook.append_page(general_box, gtk.Label(_('Appearance')))
    
    def __makeColors(self):
        colors_frame = PlainFrame(_('Select boxes colors'))
        self.text_fill_color = self.__getColorButton(self.configuration_manager.text_fill)
        self.text_stroke_color = self.__getColorButton(self.configuration_manager.text_stroke)
        self.image_fill_color = self.__getColorButton(self.configuration_manager.image_fill)
        self.image_stroke_color = self.__getColorButton(self.configuration_manager.image_stroke)
        text_fill_color_box = gtk.HBox(spacing = 10)
        text_fill_color_box.pack_start(self.text_fill_color, False)
        text_fill_color_box.pack_start(gtk.Label(_('Text fill color')), False)
        text_stroke_color_box = gtk.HBox(spacing = 10)
        text_stroke_color_box.pack_start(self.text_stroke_color, False)
        text_stroke_color_box.pack_start(gtk.Label(_('Text stroke color')), False)
        image_fill_color_box = gtk.HBox(spacing = 10)
        image_fill_color_box.pack_start(self.image_fill_color, False)
        image_fill_color_box.pack_start(gtk.Label(_('Image fill color')), False)
        image_stroke_color_box = gtk.HBox(spacing = 10)
        image_stroke_color_box.pack_start(self.image_stroke_color, False)
        image_stroke_color_box.pack_start(gtk.Label(_('Image stroke color')), False)
        colors_box = gtk.VBox()
        colors_box.pack_start(text_fill_color_box, False)
        colors_box.pack_start(text_stroke_color_box, False)
        colors_box.pack_start(image_fill_color_box, False)
        colors_box.pack_start(image_stroke_color_box, False)
        colors_frame.add(colors_box)
        return colors_frame
    
    def __makeToolsPreferences(self, *args):
        general_box = gtk.VBox(spacing = 10)
        for arg in args:
            general_box.pack_start(arg, False)
        self.notebook.append_page(general_box, gtk.Label(_('Tools')))
    
    def __makeUnpaper(self):
        unpaper_frame = PlainFrame(_('Path to unpaper'))
        self.unpaper_entry = gtk.Entry()
        self.unpaper_entry.set_width_chars(30)
        self.unpaper_entry.set_text(self.configuration_manager.getUnpaper())
        self.unpaper_select = gtk.Button(_('Choose'), gtk.STOCK_OPEN)
        unpaper_hbox = gtk.HBox()
        unpaper_hbox.pack_start(self.unpaper_entry, False)
        unpaper_hbox.pack_start(self.unpaper_select, False)
        unpaper_frame.add(unpaper_hbox)
        return unpaper_frame
    
    def __makeEngines(self):
        engines_frame = PlainFrame(_('OCR Engines'))
        self.engines_combo = gtk.combo_box_new_text()
        for engine in self.ocr_engines:
            self.engines_combo.append_text(engine.name)
        try:
            index = [engine.name for engine in self.ocr_engines].index(self.configuration_manager.favorite_engine)
        except ValueError:
            index = 0
        self.engines_combo.set_active(index)
        engines_box = gtk.HBox(spacing = 10)
        engines_box.pack_start(gtk.Label(_('Favorite engine:')), False)
        engines_box.pack_start(self.engines_combo, False)
        engines_frame.add(engines_box)
        return engines_frame
    
    def __unpaperSelectDialog(self, widget):
        unpaper_select_dialog = FileDialog('open')
        if unpaper_select_dialog.run() == gtk.RESPONSE_OK:
            self.unpaper_entry.set_text(unpaper_select_dialog.get_filename())
        unpaper_select_dialog.destroy()
    
    def __makeWindowSize(self):
        window_size_frame = PlainFrame(_('Window size'))
        self.auto_window_size = gtk.RadioButton(None, _('Automatic'))
        self.custom_window_size = gtk.RadioButton(self.auto_window_size, _('Custom'))
        self.custom_window_size_entry = gtk.SpinButton(gtk.Adjustment(0, 1, 1000, 1, 100, 0), 1, 0)
        if str(self.configuration_manager.window_size).lower() != 'auto':
            self.custom_window_size.set_active(True)
            self.custom_window_size_entry.set_value(float(self.configuration_manager.window_size))
        else:
            self.auto_window_size.set_active(True)
            self.custom_window_size_entry.set_sensitive(False)
        window_size_box = gtk.VBox()
        window_size_box.pack_start(self.auto_window_size, False)
        custom_size_box = gtk.HBox(spacing = 10)
        custom_size_box.pack_start(self.custom_window_size, False)
        custom_size_box.pack_start(self.custom_window_size_entry, False)
        window_size_box.pack_start(custom_size_box, False)
        window_size_frame.add(window_size_box)
        return window_size_frame
    
    def __toggledCustomWindowSize(self, widget):
        if self.custom_window_size.get_active():
            self.custom_window_size_entry.set_sensitive(True)
        else:
            self.custom_window_size_entry.set_sensitive(False)
    
    def __getColorButton(self, color_string):
        values = [int(value.strip()) for value in color_string.split(',')]
        color_button = gtk.ColorButton(gtk.gdk.Color(values[0] << 8, 
                                                     values[1] << 8, 
                                                     values[2] << 8))
        color_button.set_use_alpha(True)
        color_button.set_alpha(values[3] << 8)
        return color_button
        
class OcrManagerDialog(gtk.Dialog):
    
    def __init__(self, engines_manager):
        super(OcrManagerDialog, self).__init__(_('OCR Engines'), flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.engines_manager = engines_manager
        self.set_size_request(400, -1)
        self.list_store = gtk.ListStore(str)
        self.vbox.add(self.__makeMainArea())
        self.__getEngines()
        self.set_icon_from_file(WINDOW_ICON)
        self.vbox.show_all()
        self.delete_engine.connect('clicked', self.__delete)
        self.new_engine.connect('clicked', self.__engine_settings)
        self.edit_engine.connect('clicked', self.__edit)
    
    def __makeMainArea(self):
        frame = PlainFrame(_('OCR Engines'))
        engines_box = gtk.HBox(spacing = 10)
        self.tree_view = gtk.TreeView(self.list_store)
        text_cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Engine'), text_cell, text = 0)
        self.tree_view.append_column(column)
        self.tree_view.set_search_column(0)
        engines_box.add(self.tree_view)
        self.new_engine = gtk.Button(_('Add'), gtk.STOCK_ADD)
        self.delete_engine = gtk.Button(_('Delete'), gtk.STOCK_DELETE)
        self.edit_engine = gtk.Button(_('Edit'), gtk.STOCK_EDIT)
        buttons_box = gtk.VBox()
        buttons_box.pack_start(self.new_engine, False)
        buttons_box.pack_start(self.edit_engine, False)
        buttons_box.pack_start(self.delete_engine, False)
        engines_box.pack_end(buttons_box, False)
        frame.add(engines_box)
        return frame
    
    def __delete(self, widget):
        selection = self.tree_view.get_selection()
        model, iter = selection.get_selected()
        if iter:
            delete_dialog = QuestionDialog(_('Are you sure you want to delete this engine?'))
            response = delete_dialog.run()
            if response == gtk.RESPONSE_YES:
                index = model.get_path(iter)[0]
                self.engines_manager.delete(index)
                model.remove(iter)
                root_iter = model.get_iter_root()
                if root_iter:
                    selection.select_iter(root_iter)
            delete_dialog.destroy()
    
    def __edit(self, widget):
        index = self.__getSelectedIndex()
        if index != None:
            engine = self.engines_manager.ocr_engines[index]
            if engine:
                self.__engine_settings(widget, engine)
    
    def __engine_settings(self, widget, engine = None):
        new_ocr_dialog = OcrSettingsDialog(self.engines_manager, engine)
        quit = False
        while not quit:
            if new_ocr_dialog.run() == gtk.RESPONSE_ACCEPT:
                quit = new_ocr_dialog.setEngine()
                if quit:
                    self.__getEngines()
            else:
                quit = True
        new_ocr_dialog.destroy()
    
    def __getSelectedIndex(self):
        selection = self.tree_view.get_selection()
        model, iter = selection.get_selected()
        if iter:
            index = model.get_path(iter)[0]
            return index
        return None
    
    def __getEngines(self):
        self.list_store.clear()
        for engine in self.engines_manager.getEnginesNames():
            self.list_store.append((engine,))

class OcrSettingsDialog(gtk.Dialog):
    
    def __init__(self, engine_manager, engine = None):
        label = _('OCR Engines')
        if engine:
            label = _('%s engine' % engine.name)
        super(OcrSettingsDialog, self).__init__(label, flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, 
                                                                     gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.engine_manager = engine_manager
        self.engine = engine
        self.vbox.add(self.__makeMainArea())
        self.set_icon_from_file(WINDOW_ICON)
        self.vbox.show_all()
    
    def __makeMainArea(self):
        name = ''
        image_format = 'PGM'
        engine_path = ''
        failure_string = ''
        arguments = '$IMAGE'
        if self.engine:
            name = self.engine.name
            image_format = self.engine.image_format
            failure_string = self.engine.failure_string
            engine_path = self.engine.engine_path
            arguments = self.engine.arguments
        table = gtk.Table(5, 2)
        self.name_entry = gtk.Entry()
        self.__packSettingInFrame(table, 0, _('Name'), self.name_entry, name, _('Engine name'))
        self.image_format_entry = gtk.Entry()
        self.__packSettingInFrame(table, 1, _('Image format'), self.image_format_entry, image_format, _('The required image format'))
        self.failure_string_entry = gtk.Entry()
        self.__packSettingInFrame(table, 2, _('Failure string'), self.failure_string_entry, failure_string, _('The failure string or character that this engine uses'))
        self.engine_path_entry = gtk.Entry()
        self.__packSettingInFrame(table, 3, _('Engine Path'), self.engine_path_entry, engine_path, _('The path to the engine program'))
        self.arguments_entry = gtk.Entry()
        self.__packSettingInFrame(table, 4, _('Engine arguments'), self.arguments_entry, arguments, _('Arguments, use $IMAGE for image and $FILE if it writes to a file'))
        return table
    
    def setEngine(self):
        try:
            engine = self.engine_manager.newEngine(self.name_entry.get_text(), self.engine_path_entry.get_text(),
                                             self.arguments_entry.get_text(), self.image_format_entry.get_text(),
                                             self.failure_string_entry.get_text()
                                             )
            if self.engine:
                self.engine = engine
            else:
                self.engine_manager.addNewEngine(engine)
            return True
        except:
            SimpleDialog(_('Error setting the new engine, please check your engine settings.'), _('Warning'), 'warning').run()
            return False
    
    def __packSettingInFrame(self, table, position, entry_name, entry, entry_text, aditional_info = None):
        label = gtk.Label(entry_name)
        entry.set_text(entry_text)
        table.attach(label, 0, 1, position, position + 1)
        table.attach(entry, 1, 2, position, position + 1)
        if aditional_info:
            entry.set_tooltip_text(aditional_info)
            label.set_tooltip_text(aditional_info)

class CustomAboutDialog(gtk.AboutDialog):
    
    def __init__(self):
        super(CustomAboutDialog, self).__init__()
        self.set_size_request(350, -1)
        self.set_name(OCRFEEDER_STUDIO_NAME)
        self.set_program_name(OCRFEEDER_STUDIO_NAME)
        self.set_version(OCRFEEDER_STUDIO_VERSION)
        self.set_authors(OCRFEEDER_STUDIO_AUTHORS)
        self.set_logo(gtk.gdk.pixbuf_new_from_file(OCRFEEDER_ICON))
        self.set_copyright(OCRFEEDER_COPYRIGHT)
        self.set_website(OCRFEEDER_WEBSITE)
        self.set_website_label(OCRFEEDER_WEBSITE)
        self.set_license(GPL_STATEMENT)
        self.set_artists(OCRFEEDER_STUDIO_ARTISTS)
        self.set_comments(OCRFEEDER_STUDIO_COMMENTS)
        translator_credits = ''
        for translator in OCRFEEDER_STUDIO_TRANSLATORS:
            translator_credits += translator[0] + ': ' + translator[1] + '\n'
        self.set_translator_credits(translator_credits)
        self.set_icon_from_file(WINDOW_ICON)

def getPopupMenu(menus_info):
    menu = gtk.Menu()
    for menu_info in menus_info:
        image, name, callback = menu_info
        if image:
            menu_item = gtk.ImageMenuItem(image, name)
        else:
            menu_item = gtk.MenuItem(name)
        menu.append(menu_item)
        menu_item.connect("activate", callback)
        menu_item.show()
    return menu