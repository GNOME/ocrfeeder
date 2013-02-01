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

from customWidgets import PlainFrame, PlainExpander
from dataHolder import DataBox, TEXT_TYPE, IMAGE_TYPE
from ocrfeeder.util import lib, PAPER_SIZES
from ocrfeeder.util.configuration import ConfigurationManager
from ocrfeeder.util.asyncworker import AsyncWorker
from ocrfeeder.util.constants import *
from ocrfeeder.util.graphics import convertPixbufToImage
from enchant.checker import SpellChecker
import Image
import gettext
import gobject
import goocanvas
import gtk
import os.path
import pygtk
import signal
import subprocess
import sys
import threading
import Queue
import time
import gtkspell
pygtk.require('2.0')
_ = gettext.gettext

class MainWindow:

    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_size_request(800, 600)
        self.window.set_icon_from_file(WINDOW_ICON)
        self.main_box = gtk.VBox()
        self.main_box.show()

        self.statusbar = gtk.Statusbar()
        self.statusbar.show()
        self.main_box.pack_end(self.statusbar, False)

        self.main_area = gtk.HPaned()
        self.main_area.set_position(150)
        self.main_area.show()
        self.main_box.pack_end(self.main_area)

        self.window.add(self.main_box)
        self.main_area_left = gtk.ScrolledWindow()
        self.main_area_left.get_accessible().set_name(_('Pages'))
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
                                  ('SaveProjectAs', gtk.STOCK_SAVE_AS, _(u'_Save As…'), '<control><shift>s', _('Save project with a chosen name'), menu_items['save_project_as']),
                                  ('AddImage', gtk.STOCK_ADD, _('_Add Image'), None, _('Add another image'), menu_items['add_image']),
                                  ('AddFolder', gtk.STOCK_ADD, _('Add _Folder'), None, _('Add all images in a folder'), menu_items['add_folder']),
                                  ('AppendProject', gtk.STOCK_ADD, _('Append Project'), None, _('Load a project and append it to the current one'), menu_items['append_project']),
                                  ('ImportPDF', gtk.STOCK_ADD, _('_Import PDF'), None, _('Import PDF'), menu_items['import_pdf']),
                                  ('Export', None, _(u'_Export…'), '<control><shift>e', _('Export to a chosen format'), menu_items['export_dialog']),
                                  ('Edit', None, _('_Edit')),
                                  ('EditPage', gtk.STOCK_EDIT, _('_Edit Page'), None, _('Edit page settings'), menu_items['edit_page']),
                                  ('Preferences', gtk.STOCK_PREFERENCES, _('_Preferences'), None, _('Configure the application'), menu_items['preferences']),
                                  ('DeletePage', gtk.STOCK_DELETE, _('_Delete Page'), None, _('Delete current page'), menu_items['delete_page']),
                                  ('MovePageDown', gtk.STOCK_GO_DOWN, _('Move Page Do_wn'), '<control><shift>Page_Down', _('Move page down'), menu_items['move_page_down']),
                                  ('MovePageUp', gtk.STOCK_GO_UP, _('Move Page Up'), '<control><shift>Page_Up', _('Move page up'), menu_items['move_page_up']),
                                  ('SelectNextPage', gtk.STOCK_GO_DOWN, _('Select Next Page'), '<control>Page_Down', _('Select next page'), menu_items['select_next_page']),
                                  ('SelectPreviousPage', gtk.STOCK_GO_UP, _('Select Previous Page'), '<control>Page_Up', _('Select previous page'), menu_items['select_previous_page']),
                                  ('ClearProject', gtk.STOCK_DELETE, _('_Clear Project'), None, _('Delete all images'), menu_items['clear']),
                                  ('View', None, _('_View')),
                                  ('ZoomIn', gtk.STOCK_ZOOM_IN, _('Zoom In'), '<control>plus', _("Zoom In"), menu_items['zoom_in']),
                                  ('ZoomOut', gtk.STOCK_ZOOM_OUT, _('Zoom Out'), '<control>minus', _("Zoom Out"), menu_items['zoom_out']),
                                  ('ZoomFit', gtk.STOCK_ZOOM_FIT, _('Best Fit'), '<control>f', _("Best Fit"), menu_items['zoom_fit']),
                                  ('ResetZoom', gtk.STOCK_ZOOM_100, _('Normal Size'), '<control>0', _("Normal Size"), menu_items['reset_zoom']),
                                  ('Document', None, _('_Document')),
                                  ('Tools', None, _('_Tools')),
                                  ('OCREngines', None, _('_OCR Engines'), None, _('Manage OCR engines'), menu_items['ocr_engines']),
                                  ('Unpaper', gtk.STOCK_EXECUTE, _('_Unpaper'), None, _('Process image with unpaper'), menu_items['unpaper']),
                                  ('ImageDeskewer', None, _('Image Des_kewer'),
                                   None, _('Tries to straighten the image'),
                                   menu_items['image_deskewer']),
                                  ('Help', None, _('_Help')),
                                  ('HelpContents', gtk.STOCK_HELP, _('_Help'), 'F1', _('Help contents'), menu_items['help_contents']),
                                  ('About', gtk.STOCK_ABOUT, _('_About'), None, _('About this application'), menu_items['about']),
                                  ('OCRFeederReconDocument', None,
                                   _('_Recognize Document'), '<control><shift>d',
                                   _("Automatically detect and recognize all pages"),
                                   tool_items['recognizeDocument']),
                                  ('OCRFeederReconPage', None,
                                   _('R_ecognize Page'), '<control><shift>g',
                                   _("Automatically detect and recognize the current page"),
                                   tool_items['recognizePage']),
                                  ('RecognizeAreas', None,
                                   _('Recognize _Selected Areas'), '<control><shift>r',
                                   _("Recognize Selected Areas"),
                                   menu_items['recognize_areas']),
                                  ('SelectAllAreas', None,
                                   _('Select _All Areas'), '<control><shift>a',
                                   _("Select all content areas"),
                                   menu_items['select_all_areas']),
                                  ('SelectPreviousArea', gtk.STOCK_GO_BACK,
                                   _('Select _Previous Area'), '<control><shift>p',
                                   _("Select the previous area from the content areas"),
                                   menu_items['select_previous_area']),
                                  ('SelectNextArea', gtk.STOCK_GO_FORWARD,
                                   _('Select _Next Area'), '<control><shift>n',
                                   _("Select the next area from the content areas"),
                                   menu_items['select_next_area']),
                                  ('DeleteSelectedAreas', gtk.STOCK_DELETE,
                                   _('Delete Selected Areas'), '<control><shift>Delete',
                                   _("Deletes all the currently selected content areas"),
                                   menu_items['delete_selected_areas']),
                                  ('GenerateODT', None, _('_Generate ODT'), None, _("Export to ODT"), tool_items['export_to_odt']),
                                  ('ImportFromScanner', None,
                                   _('Import Page From S_canner'),
                                   '<control><shift>i',
                                   _("Import From Scanner"),
                                   menu_items['import_from_scanner']),
                                  ('CopyToClipboard', gtk.STOCK_COPY,
                                   _('_Copy to Clipboard'),
                                   '<control><shift>c',
                                   _('Copy recognized text to clipboard'),
                                   menu_items['copy_to_clipboard']),
                                  ('SpellChecker', None,
                                   _('Spell_checker'),
                                   '<shift>F7',
                                   _("Spell Check Recognized Text"),
                                   menu_items['spell_checker']),
                                  ])
        ui_manager.insert_action_group(action_group, 0)
        ui_manager.add_ui_from_file(OCRFEEDER_MENUBAR_UI)
        menu_bar = ui_manager.get_widget('/MenuBar/')
        self.main_box.pack_start(menu_bar, False)
        tool_bar = ui_manager.get_widget('/ToolBar')

        self.main_box.pack_start(tool_bar, False, False)
        odt_export_button = ui_manager.get_widget('/ToolBar/GenerateODT')
        odt_export_button.set_icon_name('ooo-writer')
        detection_button = ui_manager.get_widget('/ToolBar/OCRFeederReconDocument')
        detection_icon = gtk.image_new_from_file(DETECT_ICON)
        detection_icon.show()
        detection_button.set_icon_widget(detection_icon)
        self.copy_to_clipboard_menu = ui_manager.get_widget('/MenuBar/Edit/CopyToClipboard')
        self.copy_to_clipboard_menu.set_sensitive(False)

        if not lib.getExecPath(UNPAPER_COMMAND):
            unpaper_menu = ui_manager.get_widget('/MenuBar/Tools/Unpaper')
            unpaper_menu.hide()
        if not lib.getExecPath(GHOSTSCRIPT_COMMAND):
            import_pdf_menu = ui_manager.get_widget('/MenuBar/File/ImportPDF')
            import_pdf_menu.hide()

        self.action_group = action_group
        self.spellchecker_menu = ui_manager.get_widget('/MenuBar/Tools/SpellChecker')
        self.spellchecker_menu.set_sensitive(False)

    def setDestroyEvent(self, function):
        self.window.connect('delete-event', function)

    def setNumberOfPages(self, nr_images):
        if not self.action_group:
            return
        actions = ['ZoomIn', 'ZoomOut', 'ResetZoom',
                   'Export', 'GenerateODT', 'Unpaper', 'OCRFeederReconPage',
                   'DeletePage', 'SaveProject', 'SaveProjectAs',
                   'OCRFeederReconDocument', 'EditPage', 'ClearProject',
                   'AppendProject', 'ZoomFit', 'ImageDeskewer']
        self.__setActionsSensitiveness(actions, nr_images > 0)
        if nr_images:
            self.setHasSelectedBoxes(False)
            self.setHasContentBoxes(False)
        self.__setActionsSensitiveness(['SelectNextPage',
                                        'SelectPreviousPage',
                                        'MovePageUp',
                                        'MovePageDown'],
                                        nr_images > 1)

    def setHasSelectedBoxes(self, has_selected_boxes = True):
        if not self.action_group:
            return
        actions = ['RecognizeAreas', 'DeleteSelectedAreas']
        self.__setActionsSensitiveness(actions, has_selected_boxes)

    def setHasContentBoxes(self, has_content_boxes=True):
        actions = ['SelectNextArea', 'SelectPreviousArea',
                   'SelectAllAreas', 'CopyToClipboard',
                   'SpellChecker']
        self.__setActionsSensitiveness(actions, has_content_boxes)

    def __setActionsSensitiveness(self, actions, set_sensitive):
        for gtkaction in [self.action_group.get_action(action) \
                          for action in actions]:
            gtkaction.set_sensitive(set_sensitive)

class LanguagesComboBox(gtk.ComboBox):

    _ID_COLUMN = 0
    _LANG_COLUMN = 1
    _CHECK_COLUMN = 2

    def __init__(self, use_icon = False):
        gtk.ComboBox.__init__(self)

        self._cached_iters = {}
        self._model_columns = (str, str)
        if use_icon:
            self._model_columns += (bool,)
        model = gtk.ListStore(*self._model_columns)

        self.set_model(model)

        if use_icon:
            renderer = gtk.CellRendererToggle()
            renderer.set_sensitive(False)
            self.pack_start(renderer, False)
            self.add_attribute(renderer, 'active', self._CHECK_COLUMN)

        renderer = gtk.CellRendererText()
        # setting width so the combo won't be crazy large
        renderer.set_property('width', 50)
        self.pack_start(renderer, False)
        self.add_attribute(renderer, 'text', self._LANG_COLUMN)

        languages = lib.getLanguages()
        sorted_keys = sorted(languages, key = lambda k: languages[k])
        if sorted_keys:
            values = ('', _('No language'))
            if model.get_n_columns() == 3:
                values += (False,)
            model.append(values)
        for key in sorted_keys:
            language = languages[key]
            translation = gettext.dgettext('iso_639', language)
            values = (key, translation)
            if model.get_n_columns() == 3:
                values += (False,)
            model.append(values)

    def _getListStoreTypes(self):
        return (str, str)

    def setAvailableLanguages(self, languages):
        model = self.get_model()
        if model.get_n_columns() != 3:
            return
        cached_languages = self._cached_iters.keys()
        languages_to_unset = [lang for lang in cached_languages
                              if lang not in languages]
        for lang in languages:
            iter = self._cached_iters.get(lang)
            if iter is None:
                iter = model.get_iter_first()
                while iter:
                    if model.get_value(iter, self._ID_COLUMN) == lang:
                        self._cached_iters[lang] = iter
                        break
                    iter = model.iter_next(iter)
            if iter:
                model.set_value(iter, self._CHECK_COLUMN, True)
        for lang in languages_to_unset:
            iter = self._cached_iters.get(lang)
            if iter:
                model.set_value(iter, self._CHECK_COLUMN, False)

    def getLanguage(self):
        iter = self.get_active_iter()
        if iter:
            return self.get_model().get_value(iter, self._ID_COLUMN)

    def setLanguage(self, language):
        iter = self._cached_iters.get(language)
        model = self.get_model()
        if not iter:
            iter = model.get_iter_first()
            while iter:
                if model.get_value(iter, self._ID_COLUMN) == language:
                    break
                iter = model.iter_next(iter)
        if iter:
            self.set_active_iter(iter)

class BoxEditor(gtk.ScrolledWindow, gobject.GObject):
    __gtype_name__ = 'BoxEditor'

    __gsignals__ = {
        'text_edited_by_user' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_BOOLEAN,))
        }

    def __init__(self, image_width = 0, image_height = 0, pixbuf = 0, x = 0, y = 0, width = 0, height = 0, ocr_engines_list = []):
        super(BoxEditor, self).__init__()
        self.get_accessible().set_name(_('Area editor'))
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.contents = gtk.VBox()
        self.pixbuf = pixbuf
        self.image_window = gtk.ScrolledWindow()
        self.image_window.set_size_request(200, 200)
        self.image_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.x_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.x_spin_button.set_tooltip_text(_("Sets the content area's upper "
                                              "left corner's X coordinate"))
        self.setX(x)
        self.y_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.y_spin_button.set_tooltip_text(_("Sets the content area's upper "
                                              "left corner's Y coordinate"))
        self.setY(y)
        self.width_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.width_spin_button.set_tooltip_text(_("Sets the content area's width"))
        self.setWidth(width)
        self.height_spin_button = gtk.SpinButton(gtk.Adjustment(0,0,0,1), 1.0, 0)
        self.height_spin_button.set_tooltip_text(_("Sets the content area's height"))
        self.setHeight(height)

        self.make_text_button = self.__makeRadioButton(_('_Text'), 'gnome-mime-text')
        self.make_text_button.set_tooltip_text(_('Set this content area to be the text type'))
        self.make_image_button = self.__makeRadioButton(_('_Image'), 'gnome-mime-image', self.make_text_button)
        self.make_image_button.set_tooltip_text(_('Set this content area to be the image type'))
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

        self.__makeBoundsProperties()

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

    def __makeBoundsProperties(self):
        dimensions_frame = PlainExpander(_('Bounds'))
        box = gtk.VBox(True, 0)
        row = gtk.HBox(False, 12)
        size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        label = gtk.Label(_('_X:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.x_spin_button)
        alignment = gtk.Alignment(0, 0.5, 0, 0)
        alignment.add(label)
        size_group.add_widget(alignment)
        row.pack_start(alignment, False, False, 0)
        row.pack_start(self.x_spin_button, True, True, 0)

        label = gtk.Label(_('_Y:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.y_spin_button)
        alignment = gtk.Alignment(0, 0.5, 0, 0)
        alignment.add(label)
        size_group.add_widget(alignment)
        row.pack_start(alignment, False, False, 0)
        row.pack_start(self.y_spin_button, True, True, 0)

        box.add(row)
        row = gtk.HBox(False, 12)

        label = gtk.Label(_('_Width:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.width_spin_button)
        alignment = gtk.Alignment(0, 0.5, 0, 0)
        alignment.add(label)
        size_group.add_widget(alignment)
        row.pack_start(alignment, False, False, 0)
        row.pack_start(self.width_spin_button, True, True, 0)

        label = gtk.Label(_('Hei_ght:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.height_spin_button)
        alignment = gtk.Alignment(0, 0.5, 0, 0)
        alignment.add(label)
        size_group.add_widget(alignment)
        row.pack_start(alignment, False, False, 0)
        row.pack_start(self.height_spin_button, True, True, 0)

        box.add(row)
        dimensions_frame.add(box)
        self.contents.pack_start(dimensions_frame, False, False)

    def __makeRadioButton(self, label, icon_name, group_button = None):
        new_radio_button = gtk.RadioButton(group_button, label)
        new_radio_button.set_relief(gtk.RELIEF_NONE)
        new_radio_button.set_focus_on_click(False)
        theme = gtk.icon_theme_get_default()
        if theme.lookup_icon(icon_name, gtk.ICON_SIZE_SMALL_TOOLBAR, gtk.ICON_LOOKUP_USE_BUILTIN):
            new_radio_button.set_image(gtk.image_new_from_icon_name(icon_name, gtk.ICON_SIZE_SMALL_TOOLBAR))
        return new_radio_button

    def __makeAlignButtons(self):
        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_LEFT, _('Left'))
        self.align_left_button = gtk.RadioToolButton()
        self.align_left_button.set_label(label)
        self.align_left_button.set_icon_widget(icon)
        self.align_left_button.set_tooltip_text(_('Set text to be left aligned'))

        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_CENTER, _('Center'))
        self.align_center_button = gtk.RadioToolButton()
        self.align_center_button.set_label(label)
        self.align_center_button.set_icon_widget(icon)
        self.align_center_button.set_group(self.align_left_button)
        self.align_center_button.set_tooltip_text(_('Set text to be centered'))

        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_RIGHT, _('Right'))
        self.align_right_button = gtk.RadioToolButton()
        self.align_right_button.set_label(label)
        self.align_right_button.set_icon_widget(icon)
        self.align_right_button.set_group(self.align_left_button)
        self.align_right_button.set_tooltip_text(_('Set text to be right aligned'))

        icon, label = lib.getIconOrLabel(gtk.STOCK_JUSTIFY_FILL, _('Fill'))
        self.align_fill_button = gtk.RadioToolButton()
        self.align_fill_button.set_label(label)
        self.align_fill_button.set_icon_widget(icon)
        self.align_fill_button.set_group(self.align_left_button)
        self.align_fill_button.set_tooltip_text(_('Set text to be fill its area'))

        return self.align_left_button, self.align_center_button, self.align_right_button, self.align_fill_button

    def getLanguage(self):
        return self.languages_combo.getLanguage()

    def __makeOcrProperties(self, engines):
        hbox = gtk.HBox()
        self.perform_ocr_button = gtk.Button(_('OC_R'))
        self.perform_ocr_button.set_tooltip_text(_('Perform OCR on this '
                                                   'content area using the '
                                                   'selected OCR engine.'))
        icon = gtk.image_new_from_stock(gtk.STOCK_OK, gtk.ICON_SIZE_BUTTON)
        self.perform_ocr_button.set_image(icon)
        self.ocr_combo_box = gtk.combo_box_new_text()
        self.ocr_combo_box.set_tooltip_text(_('OCR engine to recognize '
                                              'this content area'))
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
        try:
            gtkspell.Spell(self.text_widget, OCRFEEDER_DEFAULT_LOCALE)
        except:
            pass # The locale was not found by GTKSpell, ignoring...
        self.text_widget.set_wrap_mode(gtk.WRAP_WORD)
        self.text_content = self.text_widget.get_buffer()
        self.text_content.connect('changed', self.editedByUser)
        scrolled_text = gtk.ScrolledWindow()
        scrolled_text.add(self.text_widget)
        label = gtk.Label( _('_Text'))
        label.set_use_underline(True)
        text_properties_notebook.append_page(scrolled_text, label)
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
        self.letter_spacing_spin.set_tooltip_text(_("Set the text's letter spacing"))
        self.line_spacing_spin = gtk.SpinButton(gtk.Adjustment(0.0, 0.0, 5000.0, 0.5, 100.0, 0.0), 1.0, 1)
        self.line_spacing_spin.set_tooltip_text(_("Set the text's line spacing"))

        box = gtk.VBox(True, 0)
        row = gtk.HBox(False, 12)
        size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        label = gtk.Label(_('_Line:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.line_spacing_spin)
        alignment = gtk.Alignment(0, 0.5, 0, 0)
        alignment.add(label)
        size_group.add_widget(alignment)
        row.pack_start(alignment, False, False, 0)
        row.add(self.line_spacing_spin)
        box.pack_start(row, False, False, 0)

        row = gtk.HBox(False, 12)
        label = gtk.Label(_('L_etter:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.letter_spacing_spin)
        alignment = gtk.Alignment(0, 0.5, 0, 0)
        alignment.add(label)
        size_group.add_widget(alignment)
        row.pack_start(alignment, False, False, 0)
        row.add(self.letter_spacing_spin)
        box.pack_start(row, False, False, 0)
        spacing_frame.add(box)
        vbox.pack_start(spacing_frame, False)

        label = gtk.Label( _('Sty_le'))
        label.set_use_underline(True)
        text_properties_notebook.append_page(vbox, label)
        text_properties_notebook.set_tab_reorderable(vbox, True)

        angle_box = self.__makeAngleProperty()
        if OCRFEEDER_ANGLE:
            text_properties_notebook.append_page(angle_box, gtk.Label( _('Angle')))
            text_properties_notebook.set_tab_reorderable(angle_box, True)

        label = gtk.Label( _('Mis_c'))
        label.set_use_underline(True)
        vbox = gtk.VBox()
        language_frame = PlainFrame(_('Language'))
        self.languages_combo = LanguagesComboBox(use_icon = True)
        language_frame.add(self.languages_combo)
        vbox.pack_start(language_frame, False, False, 0)
        text_properties_notebook.append_page(vbox, label)

        vbox = gtk.VBox()
        label = gtk.Label(_('OCR engine to recogni_ze this area:'))
        label.set_mnemonic_widget(self.ocr_combo_box)
        label.set_use_underline(True)
        alignment = gtk.Alignment(0, 0.5, 0, 1)
        alignment.add(label)

        vbox.pack_start(alignment)
        vbox.pack_start(hbox, False, False)
        vbox.add(text_properties_notebook)
        text_properties_frame.add(vbox)
        return text_properties_frame

    def __makeAngleProperty(self):
        self.angle_spin = gtk.SpinButton(gtk.Adjustment(0.0, -360.0, 360.0, 0.1, 100.0, 0.0), 1.0, 1)
        self.detect_angle_button = gtk.Button(_('Detect'))
        hbox = gtk.HBox()
        hbox.add(gtk.Label(_('Angle:')))
        hbox.add(self.angle_spin)
        vbox = gtk.VBox()
        vbox.pack_start(hbox, False)
        vbox.pack_start(self.detect_angle_button, False)
        return vbox

    def setAvailableLanguages(self, languages):
        self.languages_combo.setAvailableLanguages(languages)

    def setLanguage(self, language):
        self.languages_combo.setLanguage(language)

    def setFontSize(self, size):
        font_name = self.font_button.get_font_name().split(' ')
        font_name[-1] = str(size)
        self.font_button.set_font_name(' '.join(font_name))

    def setLineSpacing(self, spacing):
        self.line_spacing_spin.set_value(spacing)

    def setLetterSpacing(self, spacing):
        self.letter_spacing_spin.set_value(spacing)

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

    def editedByUser(self, widget):
        self.emit('text_edited_by_user', self.getText())

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
        return self.format_combo.get_active()

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
        self.paper_sizes.append_text(_(u'Custom…'))
        for paper in papers:
            self.paper_sizes.append_text(paper)
        active_index = self.__checkIfSizeIsStandard(page_size)
        self.paper_sizes.set_active(active_index)
        self.width_entry = gtk.SpinButton(gtk.Adjustment(0.0, 1.0, 100000.0, 0.1, 100.0, 0.0), 1.0, 1)
        self.height_entry = gtk.SpinButton(gtk.Adjustment(0.0, 1.0, 100000.0, 0.1, 100.0, 0.0), 1.0, 1)
        size_box.pack_start(self.paper_sizes, False)
        self.entries_hbox = gtk.HBox(False, 6)
        label = gtk.Label(_('_Width:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.width_entry)
        self.entries_hbox.add(label)
        self.entries_hbox.add(self.width_entry)
        label = gtk.Label(_('_Height:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.height_entry)
        self.entries_hbox.add(label)
        self.entries_hbox.add(self.height_entry)
        size_box.add(self.entries_hbox)
        page_size_frame.add(size_box)
        self.vbox.add(page_size_frame)

        affected_pages_frame = PlainFrame(_('Affected pages'))
        affected_pages_box = gtk.VBox()
        self.current_page_radio = gtk.RadioButton(None, _('C_urrent'),
                                                  True)
        self.all_pages_radio = gtk.RadioButton(self.current_page_radio,
                                               _('_All'), True)
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

class WarningDialog(gtk.MessageDialog):

    def __init__(self, message, buttons = gtk.BUTTONS_OK, parent = None):
        super(WarningDialog, self).__init__(type = gtk.MESSAGE_WARNING,
                                            buttons = buttons,
                                            parent = parent)
        self.set_icon_from_file(WINDOW_ICON)
        self.set_markup(message)

class UnpaperDialog(gtk.Dialog):

    def __init__(self, reviewer , unpaper, temp_dir = '/tmp'):
        super(UnpaperDialog, self).__init__(_('Unpaper Image Processor'), flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.unpaper_preferences = UnpaperPreferences()
        self.reviewer = reviewer
        self.unpaper = unpaper
        self.temp_dir = temp_dir
        self.unpapered_image = None
        self.__makePreviewArea()
        self.set_icon_from_file(WINDOW_ICON)
        self.vbox.show_all()
        self.preview.connect('clicked', self.__getPreview)
        self.set_size_request(500, -1)

    def __makePreviewArea(self):
        preview_frame = PlainFrame(_('Preview'))
        preview_box = gtk.VBox()
        self.preview_area = gtk.ScrolledWindow()
        self.preview_area.set_shadow_type(gtk.SHADOW_IN)
        self.preview_area.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.preview_area.set_size_request(200, 250)
        self.preview = gtk.Button(_('_Preview'))
        preview_box.pack_start(self.preview_area, False)
        preview_box.pack_start(self.preview, False)
        preview_frame.add(preview_box)
        main_area = gtk.HBox()
        main_area.pack_start(preview_frame, False, padding = 10)
        main_area.add(self.unpaper_preferences)
        self.vbox.add(main_area)

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
        command = self.unpaper_preferences.getUnpaperCommand()
        unpapered_image = os.path.splitext(name)[0] + '_unpapered.ppm'
        if os.path.exists(unpapered_image):
            unpapered_image = lib.getNonExistingFileName(unpapered_image)
        command += ' %s %s' % (name, unpapered_image)
        progress_bar = CommandProgressBarDialog(command, _('Performing Unpaper'), _(u'Performing unpaper. Please wait…'))
        progress_bar.run()
        self.unpapered_image = unpapered_image

    def __getPreviewImage(self, image_path):
        name = os.path.splitext(image_path)[0]
        if not os.path.exists(image_path):
            return
        try:
            thumbnail_image = Image.open(image_path)
        except Exception, exception:
            lib.debug(exception.message)
            return
        thumbnail_image.thumbnail((150, 200), Image.ANTIALIAS)
        image_thumbnail_path = lib.getNonExistingFileName(name + '_thumb.png')
        thumbnail_image.save(image_thumbnail_path, format = 'PNG')
        image = gtk.image_new_from_file(image_thumbnail_path)
        image.show()
        for child in self.preview_area.get_children():
            self.preview_area.remove(child)
        self.preview_area.add_with_viewport(image)

    def getUnpaperedImage(self):
        if not self.unpapered_image:
            self.performUnpaper()
        return self.unpapered_image

class UnpaperPreferences(gtk.VBox):

    def __init__(self):
        super(UnpaperPreferences, self).__init__()
        self.configuration_manager = ConfigurationManager()
        self.__makeBlackFilter()
        self.__makeNoiseFilter()
        self.__makeGrayFilter()
        self.__makeExtraOptions()
        self.noise_filter_custom.connect('toggled',
                                         self.__toggleNoiseFilterIntensity)
        self.gray_filter_custom.connect('toggled',
                                        self.__toggleGrayFilterIntensity)
        self.show_all()

    def __makeNoiseFilter(self):

        noise_filter_frame = PlainFrame(_('Noise Filter Intensity'))
        noise_filter_box = gtk.VBox()
        self.noise_filter_default = gtk.RadioButton(None, _('Default'))
        self.noise_filter_custom = gtk.RadioButton(self.noise_filter_default,
                                                   _('Custom'))
        self.noise_filter_none = gtk.RadioButton(self.noise_filter_custom,
                                                 _('None'))
        adjustment = gtk.Adjustment(0, 1, 1000, 1, 100, 0)
        self.noise_filter_intensity = gtk.SpinButton(adjustment, 1, 1)
        configured_noise_filter = \
            self.configuration_manager.unpaper_noise_filter_intensity
        if configured_noise_filter == 'auto':
            self.noise_filter_default.set_active(True)
        elif configured_noise_filter == 'none':
            self.noise_filter_none.set_active(True)
        else:
            self.noise_filter_custom.set_active(True)
            self.noise_filter_intensity.set_value(configured_noise_filter)
        self.noise_filter_intensity.set_sensitive(
            self.noise_filter_custom.get_active())

        noise_filter_custom_box = gtk.HBox()
        noise_filter_custom_box.add(self.noise_filter_custom)
        noise_filter_custom_box.add(self.noise_filter_intensity)
        noise_filter_box.pack_start(self.noise_filter_default, False)
        noise_filter_box.pack_start(noise_filter_custom_box, False)
        noise_filter_box.pack_start(self.noise_filter_none, False)
        noise_filter_frame.add(noise_filter_box)
        self.pack_start(noise_filter_frame, False)

    def __makeGrayFilter(self):

        gray_filter_frame = PlainFrame(_('Gray Filter Size'))
        gray_filter_box = gtk.VBox()
        self.gray_filter_default = gtk.RadioButton(None, _('Default'))
        self.gray_filter_custom = gtk.RadioButton(self.gray_filter_default,
                                                  _('Custom'))
        self.gray_filter_none = gtk.RadioButton(self.gray_filter_custom,
                                                _('None'))
        self.gray_filter_size = gtk.SpinButton(gtk.Adjustment(0, 1, 1000,
                                                              1, 100, 0), 1, 1)
        configured_noise_filter = \
            self.configuration_manager.unpaper_gray_filter_size
        if configured_noise_filter == 'auto':
            self.gray_filter_default.set_active(True)
        elif configured_noise_filter == 'none':
            self.gray_filter_none.set_active(True)
        else:
            self.gray_filter_custom.set_active(True)
            self.gray_filter_size.set_value(configured_noise_filter)
        self.gray_filter_size.set_sensitive(
            self.gray_filter_custom.get_active())

        gray_filter_custom_box = gtk.HBox()
        gray_filter_custom_box.add(self.gray_filter_custom)
        gray_filter_custom_box.add(self.gray_filter_size)
        gray_filter_box.pack_start(self.gray_filter_default, False)
        gray_filter_box.pack_start(gray_filter_custom_box, False)
        gray_filter_box.pack_start(self.gray_filter_none, False)
        gray_filter_frame.add(gray_filter_box)
        self.pack_start(gray_filter_frame, False)

    def __makeBlackFilter(self):

        black_filter_frame = PlainFrame(_('Black Filter'))
        self.black_filter_usage = gtk.CheckButton(_('Use'))
        self.black_filter_usage.set_active(
            self.configuration_manager.unpaper_use_black_filter)
        black_filter_frame.add(self.black_filter_usage)
        self.pack_start(black_filter_frame, False)

    def __makeExtraOptions(self):
        options_frame = PlainFrame(_('Extra Options'))
        self.extra_options = gtk.Entry()
        self.extra_options.set_tooltip_text(_("Unpaper's command "
                                              "line arguments"))
        self.extra_options.set_text(
            self.configuration_manager.unpaper_extra_options)
        options_frame.add(self.extra_options)
        self.pack_start(options_frame, False)

    def __toggleNoiseFilterIntensity(self, widget):
        has_noise_filter = self.noise_filter_custom.get_active()
        self.noise_filter_intensity.set_sensitive(has_noise_filter)

    def __toggleGrayFilterIntensity(self, widget):
        has_gray_filter = self.gray_filter_custom.get_active()
        self.gray_filter_size.set_sensitive(has_gray_filter)

    def getUnpaperCommand(self):
        command = '%s --layout single' % self.configuration_manager.unpaper
        if not self.black_filter_usage.get_active():
            command += ' --no-blackfilter'
        if self.noise_filter_none.get_active():
            command += ' --no-noisefilter'
        elif self.noise_filter_custom.get_active():
            command += ' --noisefilter-intensity %s' % \
                       self.noise_filter_intensity.get_value()
        if self.gray_filter_none.get_active():
            command += ' --no-grayfilter'
        elif self.gray_filter_custom.get_active():
            command += ' --grayfilter-size %s' % \
                       self.gray_filter_size.get_value()
        extra_options_text = self.extra_options.get_text()
        if extra_options_text.strip():
            command += ' %s ' % extra_options_text
        return command

    def save(self):
        self.configuration_manager.unpaper_use_black_filter = \
            self.black_filter_usage.get_active()
        if self.noise_filter_none.get_active():
            self.configuration_manager.unpaper_noise_filter_intensity = 'none'
        elif self.noise_filter_custom.get_active():
            self.configuration_manager.unpaper_noise_filter_intensity = \
                self.noise_filter_intensity.get_value()
        else:
            self.configuration_manager.unpaper_noise_filter_intensity = 'auto'
        if self.gray_filter_none.get_active():
            self.configuration_manager.unpaper_gray_filter_size = 'none'
        elif self.gray_filter_custom.get_active():
            self.configuration_manager.unpaper_gray_filter_size = \
                self.gray_filter_size.get_value()
        else:
            self.configuration_manager.unpaper_gray_filter_size = 'auto'
        self.configuration_manager.unpaper_extra_options = \
            self.extra_options.get_text()

class UnpaperPreferencesDialog(gtk.Dialog):

    def __init__(self, parent):
        super(UnpaperPreferencesDialog, self).__init__(_('Unpaper Preferences'),
                                               parent,
                                               gtk.DIALOG_MODAL |
                                               gtk.DIALOG_DESTROY_WITH_PARENT,
                                               (gtk.STOCK_CLOSE,
                                                gtk.RESPONSE_CLOSE))
        self.preferences = UnpaperPreferences()
        self.vbox.add(self.preferences)
        self.vbox.show_all()
        self.set_size_request(300, -1)

    def save(self):
        self.preferences.save()

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
            warning = SimpleDialog(_('An error occurred!'), _('Error'), 'warning')
            warning.run()
            return False
        self.timer = gobject.timeout_add(100, self.__pulse)
        return True

    def __pulse(self):
        self.progress_bar.pulse()
        exit_value = self.process.poll()
        if exit_value != None:
            if exit_value != 0:
                warning = SimpleDialog(_('An error occurred!'), _('Error'), 'warning')
                warning.run()
            self.destroy()
            return False
        return True

class QueuedEventsProgressDialog(gtk.Dialog):

    def __init__(self, parent, items_list = []):
        super(QueuedEventsProgressDialog, self).__init__(parent = parent,
                                                       flags = gtk.DIALOG_MODAL)
        self.set_icon_from_file(WINDOW_ICON)
        self.info_list = []
        self.worker = AsyncWorker()
        self.setItemsList(items_list)
        self.label = gtk.Label()
        self.__makeProgressBar()
        self.vbox.show_all()
        self.set_size_request(300, -1)
        self.pulse_id = 0
        self.item_number = self.worker.item_number
        self.connect('delete-event', self._deleteEventCb)

    def setItemsList(self, items_list):
        for item in items_list:
            info, async_item = item
            self.info_list.append(info)
            self.worker.queue.put(async_item)

    def __makeProgressBar(self):
        self.vbox.add(self.label)
        self.progress_bar = gtk.ProgressBar()
        progress_bar_container = gtk.Alignment(0, 0.5, 1, 0)
        progress_bar_container.add(self.progress_bar)

        hbox = gtk.HBox()
        hbox.add(progress_bar_container)

        cancel_button = gtk.Button(stock = gtk.STOCK_CANCEL)
        cancel_button.connect('clicked', self._cancelButtonClickedCb)
        hbox.pack_end(cancel_button, False, False, 0)

        self.vbox.pack_start(hbox, False)

    def run(self):
        self.worker.start()
        self.pulse_id = gobject.timeout_add(100, self._pulse)
        self.show_all()

    def cancel(self):
        self.worker.stop()
        if self.pulse_id:
            gobject.source_remove(self.pulse_id)
        self.destroy()

    def _pulse(self):
        self.progress_bar.pulse()
        if self.item_number != self.worker.item_number:
            self.item_number = self.worker.item_number
            if self.item_number != -1 and \
               self.item_number < len(self.info_list):
                title, message = self.info_list[self.item_number]
                self.set_title(title)
                self.message = message
        return True

    def _deleteEventCb(self, dialog, event):
        self.worker.stop()
        return True

    def _cancelButtonClickedCb(self, button):
        self.message = _('Cancelled')
        self.cancel()

    def __getMessage(self):
        return self.label.get_text()

    def __setMessage(self, message):
        self.label.set_text(message)

    message = property(__getMessage, __setMessage)

class PreferencesDialog(gtk.Dialog):

    def __init__(self, configuration_manager, ocr_engines):
        super(PreferencesDialog, self).__init__(_('Preferences'), flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.configuration_manager = configuration_manager
        self.ocr_engines = ocr_engines
        self.notebook = gtk.Notebook()
        self.__makeGeneralPreferences(self.__makeColors())
        self.__makeToolsPreferences(self.__makeUnpaper(),
                                    self.__makeEngines(),
                                    self.__makePreProcessorPreferences())
        self.__makeRecognitionPreferences(self.__makeLanguagePreferences(),
                                      self.__makeTextPreferences(),
                                      self.__makeWindowSize(),
                                      self.__makeColumnDetectionPreferences(),
                                      self.__makeBoundsAdjustmentsPreferences())
        self.unpaper_select.connect('clicked', self.__unpaperSelectDialog)
        self.custom_window_size.connect('toggled', self.__toggledCustomWindowSize)
        self.vbox.add(self.notebook)
        self.set_icon_from_file(WINDOW_ICON)
        self.vbox.show_all()

    def __getWindowSize(self):
        if self.custom_window_size.get_active():
            return self.custom_window_size_entry.get_value()
        return 'auto'

    def __getColor(self, color_button):
        red, green, blue, alpha = color_button.get_color().red, color_button.get_color().green, color_button.get_color().blue, color_button.get_alpha()
        return (red >> 8, green >> 8, blue >> 8, alpha >> 8)

    def saveToManager(self):
        self.configuration_manager.setWindowSize(self.__getWindowSize())
        self.configuration_manager.setTextFill(self.__getColor(self.text_fill_color))
        self.configuration_manager.setBoxesStroke(
            self.__getColor(self.boxes_stroke_color))
        self.configuration_manager.setImageFill(self.__getColor(self.image_fill_color))
        self.configuration_manager.setUnpaper(self.unpaper_entry.get_text())
        self.configuration_manager.improve_column_detection = \
            self.improve_column_detection.get_active()
        self.configuration_manager.column_min_width = self.__getColumnMinWidth()
        self.configuration_manager.clean_text = self.clean_text.get_active()
        self.configuration_manager.adjust_boxes_bounds = \
            self.adjust_boxes_bounds.get_active()
        self.configuration_manager.bounds_adjustment_size = \
            self.__getBoundsAdjustmentSize()
        self.configuration_manager.deskew_images_after_addition = \
            self.deskew_images.get_active()
        self.configuration_manager.language = self.language_combo.getLanguage()
        if self.configuration_manager.has_unpaper:
            self.configuration_manager.unpaper_images_after_addition = \
                self.unpaper_images.get_active()
        index = self.engines_combo.get_active()
        if index != -1:
            lib.debug('ACTIVE INDEX: ', index, self.ocr_engines[index][0].name)
            self.configuration_manager.setFavoriteEngine(self.ocr_engines[index][0].name)

    def __makeGeneralPreferences(self, *args):
        general_box = gtk.VBox(spacing = 10)
        for arg in args:
            general_box.pack_start(arg, False)
        label = gtk.Label(_('_General'))
        label.set_use_underline(True)
        self.notebook.append_page(general_box, label)

    def __makeRecognitionPreferences(self, *args):
        general_box = gtk.VBox(spacing = 10)
        for arg in args:
            general_box.pack_start(arg, False)
        label = gtk.Label(_('_Recognition'))
        label.set_use_underline(True)
        self.notebook.append_page(general_box, label)

    def __makeColors(self):
        colors_frame = PlainFrame(_('Select boxes\' colors'))
        self.text_fill_color = self.__getColorButton(self.configuration_manager.text_fill)
        self.boxes_stroke_color = self.__getColorButton(self.configuration_manager.boxes_stroke)
        self.image_fill_color = self.__getColorButton(self.configuration_manager.image_fill)
        text_fill_color_box = gtk.HBox(spacing = 10)
        text_fill_color_box.pack_start(self.text_fill_color, False)
        label = gtk.Label(_("Te_xt areas' fill color"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.text_fill_color)
        text_fill_color_box.pack_start(label, False)
        boxes_stroke_color_box = gtk.HBox(spacing = 10)
        boxes_stroke_color_box.pack_start(self.boxes_stroke_color, False)
        label = gtk.Label(_("Text areas' _stroke color"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.boxes_stroke_color)
        boxes_stroke_color_box.pack_start(label, False)
        image_fill_color_box = gtk.HBox(spacing = 10)
        image_fill_color_box.pack_start(self.image_fill_color, False)
        label = gtk.Label(_("_Image areas' fill color"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.image_fill_color)
        image_fill_color_box.pack_start(label, False)
        colors_box = gtk.VBox()
        colors_box.pack_start(text_fill_color_box, False)
        colors_box.pack_start(boxes_stroke_color_box, False)
        colors_box.pack_start(image_fill_color_box, False)
        colors_frame.add(colors_box)
        return colors_frame

    def __makeToolsPreferences(self, *args):
        general_box = gtk.VBox(spacing = 10)
        for arg in args:
            general_box.pack_start(arg, False)
        label = gtk.Label(_('_Tools'))
        label.set_use_underline(True)
        self.notebook.append_page(general_box, label)

    def __makeUnpaper(self):
        unpaper_frame = PlainFrame(_('Path to unpaper'))
        self.unpaper_entry = gtk.Entry()
        self.unpaper_entry.set_width_chars(30)
        self.unpaper_entry.set_text(self.configuration_manager.unpaper)
        self.unpaper_select = gtk.Button(_('Choose'), gtk.STOCK_OPEN)
        unpaper_hbox = gtk.HBox()
        unpaper_hbox.pack_start(self.unpaper_entry, False)
        unpaper_hbox.pack_start(self.unpaper_select, False)
        unpaper_frame.add(unpaper_hbox)
        return unpaper_frame

    def __makeEngines(self):
        engines_frame = PlainFrame(_('OCR Engines'))
        self.engines_combo = gtk.combo_box_new_text()
        self.engines_combo.set_tooltip_text(_('The engine that should be used '
                                              'when performing the automatic '
                                              'recognition.'))
        for engine in self.ocr_engines:
            self.engines_combo.append_text(engine[0].name)
        try:
            index = [engine.name for engine, path in self.ocr_engines].index(self.configuration_manager.favorite_engine)
        except ValueError:
            index = 0
        self.engines_combo.set_active(index)
        engines_box = gtk.HBox(spacing = 10)
        label = gtk.Label(_("Favorite _engine:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.engines_combo)
        engines_box.pack_start(label, False)
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
        self.auto_window_size = gtk.RadioButton(None, _('A_utomatic'))
        self.custom_window_size = gtk.RadioButton(self.auto_window_size, _('Cu_stom'))
        self.custom_window_size_entry = gtk.SpinButton(gtk.Adjustment(0, 1, 1000, 1, 100, 0), 1, 0)
        if str(self.configuration_manager.window_size).lower() != 'auto':
            self.custom_window_size.set_active(True)
            self.custom_window_size_entry.set_value(float(self.configuration_manager.window_size))
        else:
            self.auto_window_size.set_active(True)
            self.custom_window_size_entry.set_sensitive(False)
        window_size_box = gtk.VBox()
        label = gtk.Label(_("The window size is the detection algorithm's "
                            "subdivision areas' size."))
        window_size_box.pack_start(label, False)
        window_size_box.pack_start(self.auto_window_size, False)
        custom_size_box = gtk.HBox(spacing = 10)
        custom_size_box.pack_start(self.custom_window_size, False)
        custom_size_box.pack_start(self.custom_window_size_entry, False)
        window_size_box.pack_start(custom_size_box, False)
        window_size_frame.add(window_size_box)
        return window_size_frame

    def __makeColumnDetectionPreferences(self):
        frame = PlainFrame(_('Columns Detection'))
        main_box = gtk.VBox()
        column_detection_details = gtk.VBox()

        self.improve_column_detection = gtk.CheckButton(
                                            _('_Improve columns detection'),
                                            use_underline = True)
        tooltip_label = _('Use a post-detection algorithm to improve '
                          'the detection of columns')
        self.improve_column_detection.set_tooltip_text(tooltip_label)
        self.improve_column_detection.connect('toggled',
                                  lambda widget, main_box:
                                    main_box.set_sensitive(widget.get_active()),
                                              column_detection_details)
        self.improve_column_detection.set_active(
            self.configuration_manager.improve_column_detection)
        main_box.pack_start(self.improve_column_detection, False)

        self.auto_column_width = gtk.RadioButton(None, _('_Automatic'))
        self.custom_column_width = gtk.RadioButton(self.auto_column_width,
                                                   _('Custo_m'))

        adjustment = gtk.Adjustment(0, 1, 1000, 1, 100, 0)
        self.custom_column_width_spin = gtk.SpinButton(adjustment, 1, 0)
        tooltip_label = _("The columns' minimum width in pixels")
        self.custom_column_width_spin.set_tooltip_text(tooltip_label)
        self.custom_column_width.connect('toggled',
                             lambda widget, spin_button:
                                 spin_button.set_sensitive(widget.get_active()),
                                         self.custom_column_width_spin)

        column_min_width = self.configuration_manager.column_min_width
        if str(column_min_width).lower() != 'auto':
            self.custom_column_width.set_active(True)
            self.custom_column_width_spin.set_sensitive(True)
            self.custom_column_width_spin.set_value(column_min_width)
        else:
            self.auto_column_width.set_active(True)
            self.custom_column_width_spin.set_sensitive(False)

        label = gtk.Label(_("Minimum width that a column should have:"))
        alignment = gtk.Alignment(0, 0.5, 0, 1)
        alignment.add(label)
        column_detection_details.pack_start(alignment, True, True)

        hbox = gtk.HBox(spacing = 10)
        column_detection_details.pack_start(self.auto_column_width, False)
        hbox.pack_start(self.custom_column_width, False)
        hbox.pack_start(self.custom_column_width_spin, False)
        column_detection_details.pack_start(hbox, False)
        column_detection_details.set_sensitive(
                               self.improve_column_detection.get_active())
        alignment = gtk.Alignment(0.1, 0.5, 0, 1)
        alignment.add(column_detection_details)

        main_box.pack_start(alignment, True, True, 6)
        frame.add(main_box)

        return frame

    def __makeTextPreferences(self):
        unpaper_frame = PlainFrame(_('Recognized Text'))
        self.clean_text = gtk.CheckButton(_('_Fix line breaks and hyphenization'),
                                          use_underline = True)
        self.clean_text.set_tooltip_text(_('Removes single line breaks and '
                                           'hyphenization from text generated '
                                           'by OCR engines'))
        self.clean_text.set_active(self.configuration_manager.clean_text)
        box = gtk.HBox()
        box.pack_start(self.clean_text, False)
        unpaper_frame.add(box)
        return unpaper_frame

    def __makeBoundsAdjustmentsPreferences(self):
        frame = PlainFrame(_("Content Areas"))
        main_box = gtk.VBox()
        column_detection_details = gtk.VBox()

        self.adjust_boxes_bounds = gtk.CheckButton(
                                            _("A_djust content areas' bounds"),
                                            use_underline = True)
        tooltip_label = _('Use a post-detection algorithm to shorten '
                          "the contents areas' margins")
        self.adjust_boxes_bounds.set_tooltip_text(tooltip_label)
        self.adjust_boxes_bounds.connect('toggled',
                                  lambda widget, main_box:
                                    main_box.set_sensitive(widget.get_active()),
                                              column_detection_details)
        self.adjust_boxes_bounds.set_active(
            self.configuration_manager.adjust_boxes_bounds)
        main_box.pack_start(self.adjust_boxes_bounds, False)

        self.auto_margins_size = gtk.RadioButton(None, _('_Automatic'))
        self.custom_margins_size = gtk.RadioButton(self.auto_margins_size,
                                                   _('Custo_m'))

        adjustment = gtk.Adjustment(0, 1, 1000, 1, 100, 0)
        self.custom_margins_size_spin = gtk.SpinButton(adjustment, 1, 0)
        tooltip_label = _("The maximum size for the content areas' "
                          "margins in pixels")
        self.custom_margins_size_spin.set_tooltip_text(tooltip_label)
        self.custom_margins_size.connect('toggled',
                             lambda widget, spin_button:
                                 spin_button.set_sensitive(widget.get_active()),
                                         self.custom_margins_size_spin)

        bounds_adjustment_size = self.configuration_manager.bounds_adjustment_size
        if str(bounds_adjustment_size).lower() != 'auto':
            self.custom_margins_size.set_active(True)
            self.custom_margins_size_spin.set_sensitive(True)
            self.custom_margins_size_spin.set_value(bounds_adjustment_size)
        else:
            self.auto_margins_size.set_active(True)
            self.custom_margins_size_spin.set_sensitive(False)

        label = gtk.Label(_("Maximum size that the content areas' "
                            "margins should have:"))
        alignment = gtk.Alignment(0, 0.5, 0, 1)
        alignment.add(label)
        column_detection_details.pack_start(alignment, True, True)

        hbox = gtk.HBox(spacing = 10)
        column_detection_details.pack_start(self.auto_margins_size, False)
        hbox.pack_start(self.custom_margins_size, False)
        hbox.pack_start(self.custom_margins_size_spin, False)
        column_detection_details.pack_start(hbox, False)
        column_detection_details.set_sensitive(
                               self.adjust_boxes_bounds.get_active())
        alignment = gtk.Alignment(0.1, 0.5, 0, 1)
        alignment.add(column_detection_details)

        main_box.pack_start(alignment, True, True, 6)
        frame.add(main_box)

        return frame

    def __getBoundsAdjustmentSize(self):
        if self.auto_margins_size.get_active():
            return 'auto'
        return int(self.custom_margins_size_spin.get_value())

    def __getColumnMinWidth(self):
        if self.auto_column_width.get_active():
            return 'auto'
        return int(self.custom_column_width_spin.get_value())

    def __toggledCustomWindowSize(self, widget):
        if self.custom_window_size.get_active():
            self.custom_window_size_entry.set_sensitive(True)
        else:
            self.custom_window_size_entry.set_sensitive(False)

    def __getColorButton(self, color):
        color_button = gtk.ColorButton(gtk.gdk.Color(color[0] << 8,
                                                     color[1] << 8,
                                                     color[2] << 8))
        color_button.set_use_alpha(True)
        color_button.set_alpha(color[3] << 8)
        return color_button

    def __makePreProcessorPreferences(self):
        preprocessing_frame = PlainFrame(_('Image Pre-processing'))
        self.deskew_images = gtk.CheckButton(_('Des_kew images'),
                                             use_underline = True)
        self.deskew_images.set_tooltip_text(_('Tries to straighten the images '
                                              'before they are added'))
        self.deskew_images.set_active(
            self.configuration_manager.deskew_images_after_addition)

        box = gtk.VBox()
        box.pack_start(self.deskew_images, False)

        if self.configuration_manager.has_unpaper:
            self.unpaper_images = gtk.CheckButton(_('_Unpaper images'),
                                                  use_underline = True)
            self.unpaper_images.set_tooltip_text(_('Cleans the image using the '
                                                   'Unpaper pre-processor'))
            self.unpaper_images.set_active(
                self.configuration_manager.unpaper_images_after_addition)
            unpaper_preferences_button = gtk.Button(_('Unpaper _Preferences'),
                                                    use_underline = True)
            unpaper_preferences_button.connect('clicked',
                                       self.__unpaperPreferencesButtonClickedCb)
            hbox = gtk.HBox()
            hbox.pack_start(self.unpaper_images, False)
            hbox.pack_start(unpaper_preferences_button, False, False, 6)
            box.pack_start(hbox, False)
        preprocessing_frame.add(box)
        return preprocessing_frame

    def __unpaperPreferencesButtonClickedCb(self, button):
        unpaper_preferences = UnpaperPreferencesDialog(self)
        unpaper_preferences.run()
        unpaper_preferences.save()
        unpaper_preferences.destroy()

    def __makeLanguagePreferences(self):
        frame = PlainFrame(_('Language'))
        self.language_combo = LanguagesComboBox(use_icon = False)
        self.language_combo.setLanguage(self.configuration_manager.language)
        vbox = gtk.VBox()
        label = gtk.Label(_('The language may affect how the OCR engines work.\n'
                        'If an engine is set to support languages but does not '
                        'support the one chosen, it may result in blank text.\n'
                        'You can choose "No Language" to prevent this.'))
        alignment = gtk.Alignment(0, 0, 1, 0)
        alignment.add(label)
        vbox.pack_start(alignment, False, False, 12)
        label = gtk.Label(_('Default _language:'))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.language_combo)
        hbox = gtk.HBox()
        hbox.pack_start(label, False, False, 12)
        self.language_combo.set_size_request(250, -1)
        hbox.pack_start(self.language_combo, False, True, 12)
        vbox.pack_start(hbox, False, False, 0)
        frame.add(vbox)
        return frame

class SystemEnginesDialog(gtk.Dialog):

    def __init__(self, engines):
        super(SystemEnginesDialog, self).__init__(_('OCR Engines'),
                                                  flags = gtk.DIALOG_MODAL |
                                                          gtk.DIALOG_DESTROY_WITH_PARENT,
                                                  buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                             gtk.STOCK_ADD, gtk.RESPONSE_ACCEPT))
        self.set_size_request(300, -1)
        self.set_icon_from_file(WINDOW_ICON)
        self.list_store = gtk.ListStore(bool, str, gobject.TYPE_PYOBJECT)
        for engine in engines:
            self.list_store.append((True, engine.name, engine))
        self.vbox.pack_start(self.__makeMainArea(), True, True, 0)
        self.vbox.show_all()

    def __makeMainArea(self):
        frame = PlainFrame(_('Engines to be added'))
        self.tree_view = gtk.TreeView(self.list_store)
        renderer = gtk.CellRendererToggle()
        renderer.set_property('activatable', True)
        renderer.connect('toggled', self.__includeEngineToggledCb, 0)
        column = gtk.TreeViewColumn(_('Include'), renderer)
        column.add_attribute(renderer, "active", 0)
        self.tree_view.append_column(column)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Engine'), renderer, text = 1)
        self.tree_view.append_column(column)
        self.tree_view.set_search_column(1)
        frame.add(self.tree_view)
        return frame

    def __includeEngineToggledCb(self, renderer, path, column):
        self.list_store[path][column] = not self.list_store[path][column]

    def getChosenEngines(self):
        return [engine for include, name, engine in self.list_store if include]

class OcrManagerDialog(gtk.Dialog):

    def __init__(self, engines_manager):
        super(OcrManagerDialog, self).__init__(_('OCR Engines'), flags = gtk.DIALOG_MODAL, buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.engines_manager = engines_manager
        self.set_size_request(400, -1)
        self.list_store = gtk.ListStore(str)
        self.vbox.add(self.__makeMainArea())
        self.__getEngines()
        first_iter = self.list_store.get_iter_first()
        if first_iter:
            selection = self.tree_view.get_selection()
            selection.select_iter(first_iter)
        self.set_icon_from_file(WINDOW_ICON)
        self.vbox.show_all()
        self.delete_engine.connect('clicked', self.__delete)
        self.new_engine.connect('clicked', self.__engine_settings)
        self.edit_engine.connect('clicked', self.__edit)
        self.detect_engines.connect('clicked', self.__detectEnginesCb)

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
        self.detect_engines = gtk.Button(_('De_tect'))
        buttons_box = gtk.VBox()
        buttons_box.pack_start(self.new_engine, False)
        buttons_box.pack_start(self.edit_engine, False)
        buttons_box.pack_start(self.delete_engine, False)
        buttons_box.pack_start(self.detect_engines, False, False, 10)
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
            engine = self.engines_manager.ocr_engines[index][0]
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

    def __detectEnginesCb(self, button):
        engines = self.engines_manager.configuration_manager.getEnginesInSystem()
        if not engines:
            info = gtk.MessageDialog(self, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                                     gtk.BUTTONS_OK)
            info.set_title(_('No OCR engines available'))
            info.set_markup(_('No OCR engines were found in the system.\n'
                              'Please make sure you have OCR engines installed '
                              'and available.'))
            info.run()
            info.destroy()
            return
        engines_dialog = SystemEnginesDialog(engines)
        response = engines_dialog.run()
        if response == gtk.RESPONSE_ACCEPT:
            for engine in engines_dialog.getChosenEngines():
                self.engines_manager.addNewEngine(engine)
        engines_dialog.destroy()
        self.__getEngines()

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
        self.configuration_manager = ConfigurationManager()
        self.vbox.show_all()

    def __makeMainArea(self):
        name = ''
        image_format = 'PGM'
        engine_path = ''
        failure_string = ''
        arguments = '$IMAGE'
        language_argument = ''
        languages = ''
        if self.engine:
            name = self.engine.name
            image_format = self.engine.image_format
            failure_string = self.engine.failure_string
            engine_path = self.engine.engine_path
            arguments = self.engine.arguments
            language_argument = self.engine.language_argument
            languages = self.engine.serializeLanguages(self.engine.languages)
        box = gtk.VBox(True, 0)
        size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self.name_entry = gtk.Entry()
        self.__packSettingInFrame(box, size_group, _('_Name:'),
                                  self.name_entry, name, _('Engine name'))
        self.image_format_entry = gtk.Entry()
        self.__packSettingInFrame(box, size_group, _('_Image format:'),
                                  self.image_format_entry, image_format,
                                  _('The required image format'))
        self.failure_string_entry = gtk.Entry()
        self.__packSettingInFrame(box, size_group, _('_Failure string:'),
                                  self.failure_string_entry, failure_string,
                                  _('The failure string or character that '
                                    'this engine uses'))
        self.engine_path_entry = gtk.Entry()
        self.__packSettingInFrame(box, size_group, _('Engine _path:'),
                                  self.engine_path_entry, engine_path,
                                  _('The path to the engine program'))
        self.arguments_entry = gtk.Entry()
        self.__packSettingInFrame(box, size_group, _('Engine _arguments:'),
                                  self.arguments_entry, arguments,
                                  _('Arguments: use $IMAGE for image '
                                    'and $FILE if it writes to a file'))
        self.language_argument_entry = gtk.Entry()
        self.__packSettingInFrame(box, size_group,
                                  _('Engine _language argument:'),
                                  self.language_argument_entry, language_argument,
                                  _('The language argument in case this engine '
                                    'uses it (for example "-l"). In order for '
                                    'it to work, the engine\'s arguments should '
                                    'have the $LANG keyword.'))
        self.languages_entry = gtk.Entry()
        self.__packSettingInFrame(box, size_group,
                                  _('Engine lan_guages:'),
                                  self.languages_entry, languages,
                                  _('The languages this engine supports. '
                                    'This should be given as pairs of the '
                                    'language in the ISO 639-1 and the '
                                    'engine\'s corresponding language '
                                    '(for example "en:eng,pt:por,es:esp"). '
                                    'In order for it to work, the engine\'s '
                                    'arguments should have the $LANG keyword.'))
        return box

    def setEngine(self):
        try:
            path = self.engine_path_entry.get_text()
            if self.engine:
                version = self.engine.version
            else:
                configuration = \
                  self.configuration_manager.getEngineDefaultConfiguration(path)
                if configuration:
                    version = configuration['version']
                else:
                    version = 0.0
            arguments = self.arguments_entry.get_text()
            image_format = self.image_format_entry.get_text()
            failure_string = self.failure_string_entry.get_text()
            languages = self.languages_entry.get_text()
            language_argument = self.language_argument_entry.get_text()
            engine = self.engine_manager.newEngine(self.name_entry.get_text(),
                                                   path,
                                                   arguments,
                                                   image_format,
                                                   failure_string,
                                                   languages,
                                                   language_argument,
                                                   version)
            if self.engine:
                self.engine_manager.replaceEngine(self.engine, engine)
                self.engine = engine
            else:
                self.engine_manager.addNewEngine(engine)
            return True
        except:
            SimpleDialog(_('Error setting the new engine; please check your engine settings.'), _('Warning'), 'warning').run()
            print sys.exc_info()
            return False

    def __packSettingInFrame(self, box, size_group, entry_name, entry,
                             entry_text, aditional_info = None):
        label = gtk.Label(entry_name)
        label.set_use_underline(True)
        label.set_mnemonic_widget(entry)
        label_alignment = gtk.Alignment(0, 0.5, 0, 1)
        label_alignment.add(label)
        size_group.add_widget(label_alignment)
        entry.set_text(entry_text)
        if aditional_info:
            entry.set_tooltip_text(aditional_info)
        row = gtk.HBox(False, 12)
        row.pack_start(label_alignment, False, False, 0)
        row.add(entry)
        box.add(row)

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
        self.set_comments(_(OCRFEEDER_STUDIO_COMMENTS))
        self.set_translator_credits(_('translator-credits'))
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

class ScannerChooserDialog(gtk.Dialog):

    def __init__(self, parent, devices):
        super(ScannerChooserDialog, self).__init__(parent = parent,
                                                   title = "Devices selector",
                                                   flags = gtk.DIALOG_MODAL,
                                                   buttons = (gtk.STOCK_CANCEL,
                                                           gtk.RESPONSE_REJECT,
                                                           gtk.STOCK_OK,
                                                           gtk.RESPONSE_ACCEPT))

        self.devices = devices
        self.label = gtk.Label('_Select one of the scanner devices found:')
        self.label.set_use_underline(True)
        self.vbox.pack_start(self.label, padding = 5)

        self.selected_device = None
        self.__combo_box = gtk.combo_box_new_text()
        self.label.set_mnemonic_widget(self.__combo_box)

        for device in self.devices:
            self.__combo_box.append_text(device[2])

        self.__combo_box.set_active(0)

        self.vbox.pack_start(self.__combo_box)

        self.vbox.show_all()


    def getSelectedDevice(self):
        index = self.__combo_box.get_active()
        if index < 0:
            return None
        return self.devices[index][0]

class SpellCheckerDialog():

    def __init__(self, parent, current_reviewer, language):
        self.builder = gtk.Builder()
        self.builder.add_from_file(OCRFEEDER_SPELLCHECKER_UI)
        self.window = self.builder.get_object('check_spelling_window')
        self.window.set_transient_for(parent)
        self.builder.connect_signals(self)
        self.window.present()
        self.reviewer = current_reviewer
        self.text = self.reviewer.boxeditor_notebook.get_nth_page(self.reviewer.boxeditor_notebook.get_current_page()).getText()
        self.dictButtons = {'change_button':self.builder.get_object('change_button'),
               'change_all_button':self.builder.get_object('change_all_button'),
               'ignore_button':self.builder.get_object('ignore_button'),
               'ignore_all_button':self.builder.get_object('ignore_all_button')
               }
        self.label_language = self.builder.get_object('language_label')
        self.label_language.set_label(language)
        self.text_view = self.builder.get_object('textview_context')
        self.text_view.set_wrap_mode(gtk.WRAP_WORD)
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.misspelled_word = self.text_view.get_buffer()
        text_buffer = self.text_view.get_buffer()
        text_buffer.create_tag("fg_black", foreground="black")
        text_buffer.create_tag("fg_red", foreground="red")
        self.word_entry = self.builder.get_object('word_entry')
        self.suggestions_list = self.builder.get_object('liststore1')
        self.renderer_text = gtk.CellRendererText()
        self.column = gtk.TreeViewColumn(None,self.renderer_text, text=0)
        self.treeview = self.builder.get_object('suggestions_list')
        self.treeview.append_column(self.column)
        self._checker = SpellChecker(language)
        self._numchars = 40

        if self.text:
            self._checker.set_text(self.text.decode('utf-8'))
            try:
                self.__next()
            except AttributeError:
                self.__set_no_more()
        else:
            self.__set_no_more()

    def word_entry_changed_cb(self, widget):
        self.__checkHasAlternative()

    def __checkHasAlternative(self):
        if not self.word_entry.get_text():
            [self.dictButtons[button].set_sensitive(False) for button in self.dictButtons.keys() if not button.find('change')]
        else:
            [self.dictButtons[button].set_sensitive(True) for button in self.dictButtons.keys() if not button.find('change')]

    def suggestions_list_row_activated_cb(self, widget, x, y):
        self.word_entry.set_text(widget.get_model().get_value(widget.get_model().get_iter(x), 0))

    def suggestions_list_cursor_changed_cb(self, widget):
        model, iter = widget.get_selection().get_selected()
        self.word_entry.set_text(model[iter][0])


    def ignore_button_clicked_cb(self, widget):
        self.__next()

    def ignore_all_button_clicked_cb(self, widget):
        self._checker.ignore_always()
        self.__next()

    def change_button_clicked_cb(self, widget):
        self.__replaceText(self.word_entry.get_text())
        self.__next()

    def change_all_button_clicked_cb(self, widget):
        self.__replaceAllText(self.word_entry.get_text())
        self.__next()

    def close_button_clicked_cb(self, widget):
        self.window.destroy()

    def check_spelling_window_delete_event_cb(self, widget, data):
        self.window.destroy()

    def __set_no_more(self):
        self.misspelled_word.set_text('')
        iter = self.misspelled_word.get_iter_at_offset(0)
        append = self.misspelled_word.insert_with_tags_by_name
        append(iter, "No misspelled words", 'fg_red')
        self.word_entry.set_sensitive(False)
        [self.dictButtons[button].set_sensitive(False) for button in self.dictButtons.keys()]

    def __next(self):
        self.word_entry.set_text('')
        self.__checkHasAlternative()
        self.suggestions_list.clear()

        try:
            self._checker.next()
        except StopIteration:
            self.__set_no_more()
            return False

        self.misspelled_word.set_text('')
        iter = self.misspelled_word.get_iter_at_offset(0)
        append = self.misspelled_word.insert_with_tags_by_name
        lContext = self._checker.leading_context(self._numchars)
        tContext = self._checker.trailing_context(self._numchars)
        append(iter, lContext, 'fg_black')
        append(iter, self._checker.word, 'fg_red')
        append(iter, tContext, 'fg_black')

        self.__fillSuggest(self._checker.suggest())

    def __replaceText(self, replace_text):
        self._checker.replace(replace_text)
        newtext = self._checker.get_text()
        self.reviewer.boxeditor_notebook.get_nth_page(self.reviewer.boxeditor_notebook.get_current_page()).setText(newtext)

    def __replaceAllText(self, replace_text):
        self._checker.replace_always(replace_text)
        newtext = self._checker.get_text().replace(self._checker.word, replace_text)
        self.reviewer.boxeditor_notebook.get_nth_page(self.reviewer.boxeditor_notebook.get_current_page()).setText(newtext)

    def __fillSuggest(self, suggests):
        for suggest in suggests:
            self.suggestions_list.append([suggest])
