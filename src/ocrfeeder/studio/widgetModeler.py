###########################################################################
#    OCRFeeder - The complete OCR suite
#    Copyright (C) 2009-2013 Joaquim Rocha
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

from .boxesarea import BoxesArea
from .dataHolder import DataBox, PageData, TEXT_TYPE, IMAGE_TYPE
from ocrfeeder.feeder.documentGeneration import OdtGenerator, HtmlGenerator, PlaintextGenerator, PdfGenerator
from ocrfeeder.feeder.imageManipulation import *
from ocrfeeder.feeder.layoutAnalysis import *
from .project import ProjectSaver, ProjectLoader
from ocrfeeder.util import graphics, ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER, \
     ALIGN_FILL, PAPER_SIZES
from ocrfeeder.util.lib import getNonExistingFileName, unpaperImage
from ocrfeeder.util.log import debug, warning
from ocrfeeder.util.configuration import ConfigurationManager
from ocrfeeder.util import constants
from ocrfeeder.util.asyncworker import AsyncItem
from .widgetPresenter import BoxEditor, PagesToExportDialog, FileDialog, \
    PageSizeDialog, UnpaperDialog, \
    QueuedEventsProgressDialog, SpellCheckerDialog
import gettext
from gi.repository import Gtk, GObject, Gdk, GdkPixbuf, Pango
import math
import os.path
import threading
import sys
_ = gettext.gettext

class ImageReviewer(Gtk.Paned):

    def __init__(self, main_window, page_data, ocr_engines):
        super(ImageReviewer, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_wide_handle(True)
        self.configuration_manager = ConfigurationManager()
        self.main_window = main_window
        self.path_to_image = page_data.image_path
        self.text_box_fill_color = (94, 156, 235, 150)
        self.box_stroke_color = (94, 156, 235, 250)
        self.image_box_fill_color = (0, 183, 0, 150)
        self.selectable_boxes_area = BoxesArea(self.path_to_image)
        self.selectable_boxes_area.connect('selected_box', self.selectedBox)
        self.selectable_boxes_area.connect('removed_box', self.removedBox)
        self.selectable_boxes_area.connect('updated_box', self.updatedBox)
        self.selectable_boxes_area.connect('dragged_box', self.updatedBoxBounds)
        self.selectable_boxes_area.connect('deselected_box',
                                           self.deselectedBoxCb)
        self.image_pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.path_to_image)
        self.show()
        self.ocr_engines = ocr_engines
        self.editor = Editor(self.image_pixbuf, self.ocr_engines, self)
        self.boxes_dict = {}

        selectable_boxes_scrolled_window = Gtk.ScrolledWindow()
        selectable_boxes_scrolled_window.get_accessible().set_name(
                                                         _('Selectable areas'))
        selectable_boxes_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        selectable_boxes_scrolled_window.add(self.selectable_boxes_area)
        self.selectable_boxes_area.show()
        selectable_boxes_scrolled_window.show()

        self.pack1(selectable_boxes_scrolled_window, True, False)
        self.pack2(self.editor.box_editor, False, False)
        self.page = page_data
        self.updatePageData(self.page)
        selectable_boxes_scrolled_window.connect_after("size-allocate", self.zoomFitCb)

    def setTextFillColor(self, color):
        self.text_box_fill_color = color
        self.selectable_boxes_area.setAreaFillRgba(self.text_box_fill_color)

    def setBoxesStrokeColor(self, color):
        self.box_stroke_color = color
        self.selectable_boxes_area.setAreaStrokeRgba(self.box_stroke_color)

    def setImageFillColor(self, color):
        self.image_box_fill_color = color

    def addBoxEditor(self, box, data_box = None):
        if not data_box:
            data_box = DataBox()
            data_box.setLanguage(self.configuration_manager.language)
            data_box.updateBoundsFromBox(box)
        self.boxes_dict[box] = data_box
        self.editor.setBoxes(box, data_box)

    def selectedBox(self, widget, box):
        data_box = self.boxes_dict.get(box)
        if data_box:
            self.editor.setBoxes(box, data_box)
        else:
            self.addBoxEditor(box)
        self.updateMainWindow()

    def deselectedBoxCb(self, widget, box):
        self.updateMainWindow()

    def updatedBox(self, widget, box):
        if self.editor.box == box:
            self.editor.update(box)

    def updatedBoxBounds(self, widget, box):
        if self.editor.box == box:
            self.editor.data_box.updateBoundsFromBox(box)

    def removedBox(self, widget, box):
        self.updateMainWindow()
        if box not in self.boxes_dict:
            return False
        del self.boxes_dict[box]
        if self.editor.box == box:
            self.editor.updateDataBox(None)
            self.editor.box = None
        self.selectable_boxes_area.selectNextArea()
        return False

    def clear(self):
        self.selectable_boxes_area.clearAreas()
        self.editor.updateDataBox(None)
        self.editor.box = None
        self.boxes_dict.clear()

    def applyTextColors(self):
        self.selectable_boxes_area.fill_color_rgba = self.text_box_fill_color
        self.selectable_boxes_area.stroke_color_rgba = self.box_stroke_color

    def applyImageColors(self):
        self.selectable_boxes_area.fill_color_rgba = self.image_box_fill_color
        self.selectable_boxes_area.stroke_color_rgba = self.box_stroke_color

    def addNewEditorsToAllBoxes(self):
        self.editor_list = []
        boxes = self.selectable_boxes_area.getAllAreas()
        for box in boxes:
            self.addBoxEditor(box)

    def performOcrForSelectedBoxes(self):
        selected_boxes = self.selectable_boxes_area.getSelectedAreas()
        configured_engine = None
        for engine, path in self.ocr_engines:
            if engine.name == self.configuration_manager.favorite_engine:
                configured_engine = engine
                break
        if not configured_engine:
            return
        for box in selected_boxes:
            data_box = self.boxes_dict[box]
            self.performOcrForDataBox(data_box, engine)
        self.editor.updateDataBox(self.editor.data_box)
        self.updateMainWindow()

    def performOcrForDataBox(self, data_box, engine):
        if engine.hasLanguages():
            engine.setLanguage(data_box.getLanguage())
        pixbuf_width = self.image_pixbuf.get_width()
        pixbuf_height = self.image_pixbuf.get_height()
        new_pixbuf_width = min(data_box.getWidth(), pixbuf_width)
        new_pixbuf_height = min(data_box.getHeight(), pixbuf_height)
        subpixbuf = self.image_pixbuf.new_subpixbuf(data_box.getX(),
                                                    data_box.getY(),
                                                    new_pixbuf_width,
                                                    new_pixbuf_height)
        subpixbuf.x = data_box.getX()
        subpixbuf.y = data_box.getY()
        subpixbuf.width = pixbuf_width
        image = graphics.convertPixbufToImage(subpixbuf)
        layout_analysis = LayoutAnalysis(engine,
                                         clean_text = self.configuration_manager.clean_text)
        text = layout_analysis.readImage(image)
        data_box.setText(text)
        self.main_window.copy_to_clipboard_menu.set_sensitive(True)
        self.main_window.spellchecker_menu.set_sensitive(True)
        debug('Finished reading')
        text_size = layout_analysis.getTextSizeFromImage(image,
                                                         self.page.resolution[1])
        if text_size:
            data_box.setFontSize(text_size)

    def getTextFromBoxes(self, boxes):
        text = ''
        #@todo: Implement a proper way to get the boxes
        # in reading order
        boxes.reverse()
        self.editor.saveDataBox()
        if boxes:
            text = self.page.getTextFromBoxes(
                [self.boxes_dict.get(box) for box in boxes])
        else:
            if self.editor.box_editor.getType() == TEXT_TYPE:
                text = self.box_editor.getText()
        return text

    def copyTextToClipboard(self):
        selected_boxes = self.selectable_boxes_area.getSelectedAreas()
        text = self.getTextFromBoxes(selected_boxes)
        Gtk.Clipboard.get(Gdk.Atom.intern("CLIPBOARD", True)).set_text(text, -1)

    def getAllText(self):
        boxes = self.selectable_boxes_area.getAllAreas()
        return self.getTextFromBoxes(boxes)

    def __getAllDataBoxes(self):
        boxes = []
        for data_box in self.boxes_dict.values():
            boxes.append((data_box.y, data_box))
            boxes.sort()
        boxes_sorted = []
        for y, box in boxes:
            boxes_sorted.append(box)
        boxes = boxes_sorted
        return boxes

    def savePageData(self):
        self.editor.saveDataBox()
        self.page.data_boxes = self.__getAllDataBoxes()
        return self.page

    def updatePageData(self, page_data):
        self.page = page_data
        for data_box in self.page.data_boxes:
            self.addDataBox(data_box)

    def addDataBox(self, data_box):
        dimensions = (int(data_box.x), int(data_box.y), int(data_box.width), int(data_box.height))
        box = self.selectable_boxes_area.addArea(dimensions)
        self.addBoxEditor(box, data_box)

    def updateBackgroundImage(self, image_path):
        self.path_to_image = self.page.image_path = image_path
        if not os.path.exists(self.path_to_image):
            return
        try:
            self.image_pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.path_to_image)
        except Exception as exception:
            debug(exception.message)
            return
        self.selectable_boxes_area.setBackgroundImage(self.path_to_image)
        self.editor.updateImage(self.image_pixbuf)
        if self.editor.box:
            self.editor.update(self.editor.box)

    def updateBoxesColors(self):
        self.editor.updateBoxColor()

    def zoomFitCb(self, widget, data):
        self.zoomFit()
        widget.disconnect_by_func(self.zoomFitCb)

    def zoomFit(self):
        parent = self.selectable_boxes_area.get_parent()
        allocation = parent.get_allocation()
        parent_height, parent_width = allocation.height, allocation.width
        image_height, image_width = self.selectable_boxes_area.getImageSize()
        changed = False
        if image_height > parent_height:
            image_height = parent_height / image_height
            changed = True
        if image_width > parent_width:
            image_width = parent_width / image_width
            changed = True
        if changed:
            self.selectable_boxes_area.zoom(min(image_height, image_width), False)

    def updateMainWindow(self):
        if self.editor.box_editor.getText():
            self.main_window.copy_to_clipboard_menu.set_sensitive(True)
            self.main_window.spellchecker_menu.set_sensitive(True)
        else:
            self.main_window.copy_to_clipboard_menu.set_sensitive(False)
            self.main_window.spellchecker_menu.set_sensitive(False)
        has_selected_areas = self.selectable_boxes_area.getSelectedAreas()
        has_boxes = self.selectable_boxes_area.getAllAreas()
        self.main_window.setHasSelectedBoxes(bool(has_selected_areas))
        self.main_window.setHasContentBoxes(bool(has_boxes))

    def focusCurrentEditorTextArea(self):
        self.editor.box_editor.text_widget.grab_focus()

    def updateOcrEngines(self, ocr_engines):
        self.ocr_engines = ocr_engines
        self.editor.updateOcrEngines(ocr_engines)

class ImageReviewer_Controler:

    REVIEWER_CACHE_LENGTH = 5

    def __init__(self, main_window, pages_icon_view,
                 ocr_engines, configuration_manager):
        self.main_window = main_window
        self.notebook = self.main_window.notebook
        self.pages_icon_view = pages_icon_view
        self.ocr_engines = ocr_engines
        self.configuration_manager = configuration_manager
        self.statusbar = self.main_window.statusbar
        self._page_info_message_id = self.statusbar.get_context_id('page_info_message')
        self.pages_icon_view.connect('selection-changed', self.selectImageReviewer)
        self.__updateStatusBar()

    def __createdImageReviewer(self, page_data):
        image_reviewer = ImageReviewer(self.main_window, page_data, self.ocr_engines)
        image_reviewer.selectable_boxes_area.connect('changed_zoom', self.__setZoomStatus)
        image_reviewer.setTextFillColor(self.configuration_manager.text_fill)
        image_reviewer.setBoxesStrokeColor(self.configuration_manager.boxes_stroke)
        image_reviewer.setImageFillColor(self.configuration_manager.image_fill)
        return image_reviewer

    def addImages(self, image_path_list):
        paths = []
        for path in image_path_list:
            if os.path.exists(path):
                paths.append(path)
            else:
                warning('Could not load image "%s": does not exist' % path)

        if not paths:
            return

        image_path_list = paths
        item_list = []
        temp_dir = self.configuration_manager.TEMPORARY_FOLDER
        image_path_list = graphics.convertMultiImagesInList(image_path_list,
                                                            temp_dir)
        item_list_length = len(image_path_list)
        if not self.configuration_manager.deskew_images_after_addition and \
           not self.configuration_manager.unpaper_images_after_addition:
            for index in range(0, len(image_path_list)):
                if not self.__addImage(image_path_list[index], index == 0):
                    debug('Failed to load image "%s"', image_path_list[index])
            return
        dialog = QueuedEventsProgressDialog(self.main_window)
        for index in range(0, item_list_length):
            image_path = image_path_list[index]
            item = AsyncItem(self.__imagePreProcessing,
                             (image_path,),
                             self.__imagePreProcessingFinishedCb,
                             (dialog,
                              index == item_list_length - 1,
                              index == 0))
            if item_list_length == 1:
                item_info = (_('Preparing image'), _('Please wait…'))
            else:
                item_info = (_('Preparing image %(current_index)s/%(total)s') % \
                             {'current_index': index + 1,
                              'total': item_list_length},
                             _('Please wait…'))
            item_list.append((item_info,item))
        dialog.setItemsList(item_list)
        dialog.run()

    def __imagePreProcessing(self, image_path):
        processed_image = None
        if self.configuration_manager.unpaper_images_after_addition and \
           self.configuration_manager.has_unpaper:
            processed_image = unpaperImage(self.configuration_manager,
                                           image_path)
        if self.configuration_manager.deskew_images_after_addition:
            processed_image = self.__deskewImage(processed_image or image_path,
                                                 processed_image)
        return processed_image or image_path

    def __imagePreProcessingFinishedCb(self, dialog, finished,
                                       select_image, image_path, error):
        self.__addImage(image_path, select_image)
        if finished:
            dialog.cancel()

    def __addImage(self, image_path, select_image = True, page_data = None):
        image_path = os.path.abspath(os.path.expanduser(image_path))
        if not os.path.isfile(image_path):
            return None
        if page_data is None:
            page_data = PageData(image_path)
        iter = self.pages_icon_view.get_model().addImage(page_data)
        if select_image:
            path = \
                self.pages_icon_view.get_model().get_path(iter)
            self.pages_icon_view.select_path(path)
        return page_data

    def __deskewImage(self, image_path, target_image_path = None):
        if not target_image_path:
            tmp_dir = self.configuration_manager.TEMPORARY_FOLDER
            target_image_path = os.path.join(tmp_dir,
                                             os.path.basename(image_path))
            if os.path.exists(target_image_path):
                target_image_path = getNonExistingFileName(target_image_path)
        image_deskewer = ImageDeskewer()
        if image_deskewer.deskew(image_path, target_image_path):
            return target_image_path
        return image_path

    def deskewCurrentImage(self, widget):
        reviewer = self.__getCurrentReviewer()
        dialog = QueuedEventsProgressDialog(self.main_window)
        item = AsyncItem(self.__deskewImage,
                         (reviewer.path_to_image,),
                         self.__deskewCurrentImageFinishedCb,
                         (dialog, reviewer))
        item_info = (_('Deskewing image'), _('Please wait…'))
        dialog.setItemsList([(item_info, item)])
        dialog.run()

    def __deskewCurrentImageFinishedCb(self, dialog, reviewer,
                                       image_path, error):
        if error:
            return
        reviewer.updateBackgroundImage(image_path)
        dialog.cancel()

    def selectImageReviewer(self, widget):
        page_data = self.pages_icon_view.getSelectedPageData()
        if not page_data:
            return
        reviewer = self.__setImageReviewerFromPageData(page_data)
        self.__setZoomStatus(None, reviewer.selectable_boxes_area.get_scale())
        self.__updateStatusBar(reviewer)
        reviewer.updateMainWindow()

    def __setZoomStatus(self, widget, zoom):
        self.__updateStatusBar()

    def __updateStatusBar(self, reviewer = None):
        reviewer = reviewer or self.__getCurrentReviewer()

        if not reviewer:
            status_message = _('No images added')
        else:
            zoom = int(reviewer.selectable_boxes_area.get_scale() * 100)
            status_message = _('Zoom: %s %%') % zoom
            page_data = reviewer.savePageData()
            status_message += ' ' + _('Resolution: %.2f x %.2f') % (page_data.resolution[0],
                                                                    page_data.resolution[1])
            status_message += ' ' + _('Page size: %i x %i') % (page_data.width,
                                                               page_data.height)

        self.statusbar.pop(self._page_info_message_id)
        self.statusbar.push(self._page_info_message_id, status_message)

    def __setImageReviewerFromPageData(self, page_data):
        n_pages = self.notebook.get_n_pages()
        index = 0
        while index < n_pages:
            reviewer = self.notebook.get_nth_page(index)
            if reviewer.savePageData() == page_data:
                self.notebook.set_current_page(index)
                return reviewer
            index += 1
        if n_pages == self.REVIEWER_CACHE_LENGTH:
            self.notebook.remove_page(0)
        reviewer = self.__createdImageReviewer(page_data)
        index = self.notebook.append_page(reviewer, None)
        self.notebook.set_current_page(index)
        return reviewer

    def __updateImageReviewers(self):
        n_pages = self.notebook.get_n_pages()
        index = 0
        while index < n_pages:
            reviewer = self.notebook.get_nth_page(index)
            reviewer.clear()
            reviewer.updatePageData(reviewer.page)
            index += 1

    def recognizeSelectedAreas(self):
        image_reviewer = self.__getCurrentReviewer()
        image_reviewer.performOcrForSelectedBoxes()

    def __confirmOveritePossibilityByRecognition(self):
        confirm_recognition = Gtk.MessageDialog(self.main_window,
                                                message_type = Gtk.MessageType.QUESTION,
                                                buttons = Gtk.ButtonsType.YES_NO,
                                                flags = Gtk.DialogFlags.MODAL |
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT)
        message = _('There are changes that may be overwritten '
                    'by the new recognition.\n\n'
                    'Do you want to continue?')
        confirm_recognition.set_markup(message)
        response = confirm_recognition.run()
        confirm_recognition.destroy()
        return response

    def recognizeCurrentPage(self):
        if not self.ocr_engines:
            self.main_window._warnNoOCREngines()
            return
        image_reviewer = self.__getCurrentReviewer()
        if image_reviewer.selectable_boxes_area.getAllAreas() and \
           self.__confirmOveritePossibilityByRecognition() != Gtk.ResponseType.YES:
                return
        page = image_reviewer.page
        dialog = QueuedEventsProgressDialog(self.main_window)
        item = AsyncItem(self.__performRecognitionForPage,
                         (page,),
                         self.__performRecognitionForPageFinishedCb,
                         (dialog, page, [page]))
        info = (_('Recognizing Page'), _('Please wait…'))
        dialog.setItemsList([(info, item)])
        dialog.run()

    def recognizeDocument(self):
        pages = self.pages_icon_view.getAllPages()
        dialog = QueuedEventsProgressDialog(self.main_window)
        items = []
        i = 1
        total = len(pages)
        has_changes = False
        for page in pages:
            has_changes = has_changes or bool(page.data_boxes)
            item = AsyncItem(self.__performRecognitionForPage,
                             (page,),
                             self.__performRecognitionForPageFinishedCb,
                             (dialog, page, pages))
            info = (_('Recognizing Document'),
                    _('Recognizing page %(page_number)s/%(total_pages)s. Please wait…') % {'page_number': i,
                                                                                            'total_pages': total})
            items.append((info, item))
            i += 1
        if has_changes and \
           self.__confirmOveritePossibilityByRecognition() != Gtk.ResponseType.YES:
                return
        dialog.setItemsList(items)
        dialog.run()

    def __performRecognitionForPage(self, page):
        window_size = self.configuration_manager.window_size
        if window_size == 'auto':
            window_size = None
        else:
            window_size = float(window_size)
        improve_column_detection = \
            self.configuration_manager.improve_column_detection
        column_min_width = self.configuration_manager.column_min_width
        if column_min_width == 'auto':
            column_min_width = None
        adjust_boxes_bounds = \
            self.configuration_manager.adjust_boxes_bounds
        adjustment_size = self.configuration_manager.bounds_adjustment_size
        if adjustment_size == 'auto':
            adjustment_size = None
        clean_text = self.configuration_manager.clean_text

        engine = self.__getConfiguredOcrEngine()
        if engine.hasLanguages():
            engine.setLanguage(self.configuration_manager.language)
        layout_analysis = LayoutAnalysis(engine,
                                         window_size,
                                         improve_column_detection,
                                         column_min_width,
                                         clean_text,
                                         adjust_boxes_bounds,
                                         adjustment_size)
        return layout_analysis.recognize(page.image_path,
                                         page.resolution[1])

    def __getConfiguredOcrEngine(self):
        for engine, path in self.ocr_engines:
            if engine.name == self.configuration_manager.favorite_engine:
                return engine
        return None

    def __performRecognitionForPageFinishedCb(self, dialog, page,
                                              pages_to_process,
                                              data_boxes, error):
        page.data_boxes = data_boxes
        if page == pages_to_process[-1]:
            dialog.cancel()
            self.__updateImageReviewers()

    def copyRecognizedTextToClipboard(self, widget):
        image_reviewer = self.__getCurrentReviewer()
        image_reviewer.copyTextToClipboard()

    def setDataBox(self, widget):
        image_reviewer = self.__getCurrentReviewer()
        document_generator = OdtGenerator()
        page_data = image_reviewer.savePageData()
        document_generator.addPage(page_data)
        document_generator.save()

    def exportPagesWithGenerator(self, generator, format_name):
        extra_args = {}
        if format_name == 'PDF':
            from_scratch, cancelled = self.__askPdfFromScratch()
            if cancelled:
                return
            extra_args['from_scratch'] = from_scratch

        pages = self.__askForNumberOfPages(_('Export to %(format_name)s') %
                                           {'format_name': format_name})
        if not pages:
            return
        file_name = self.__askForFileName()
        if file_name:
            if os.path.exists(file_name):
                os.remove(file_name)
            document_generator = generator(file_name, **extra_args)
            reviewer = self.__getCurrentReviewer()
            for page in pages:
                # if the page is not the current reviewer, we need to
                # update the box's image before exporting it
                if page != reviewer.page:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(page.image_path)
                    for box in page.data_boxes:
                        box.updateImage(pixbuf)
                document_generator.addPage(page)
            document_generator.save()

    def __askPdfFromScratch(self):
        ask_pdf_type_dialog = Gtk.MessageDialog(self.main_window,
                    Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                      buttons = Gtk.ButtonsType.OK_CANCEL)
        ask_pdf_type_dialog.set_markup(_('What kind of PDF document do you '
                                         'wish?'))
        pdf_from_scratch_radio = Gtk.RadioButton(label= _('From scratch'))
        pdf_from_scratch_radio.set_tooltip_text(
                                    _('Creates a new PDF from scratch.'))
        searchable_pdf_radio = \
                         Gtk.RadioButton.new_from_widget(pdf_from_scratch_radio)
        searchable_pdf_radio.set_label(_('Searchable PDF'))
        searchable_pdf_radio.set_tooltip_text(_('Creates a PDF based on '
                                                'the images but with searchable '
                                                'text.'))
        vbox = Gtk.VBox(True)
        vbox.add(pdf_from_scratch_radio)
        vbox.add(searchable_pdf_radio)
        content_area = ask_pdf_type_dialog.get_content_area()
        content_area.add(vbox)
        content_area.show_all()

        response = ask_pdf_type_dialog.run()
        ask_pdf_type_dialog.destroy()
        if response == Gtk.ResponseType.CANCEL:
            return (False, True)

        pdf_from_scratch = True
        if searchable_pdf_radio.get_active():
            pdf_from_scratch = False
        return (pdf_from_scratch, False)

    def saveProjectAs(self):
        return self.__askForFileName(extension = '.ocrf')

    def saveProject(self, project_name):
        image_reviewer = self.__getCurrentReviewer()
        image_reviewer.savePageData()
        if not project_name.endswith('.ocrf'):
            project_name += '.ocrf'
        pages_data = self.pages_icon_view.getAllPages()
        project_saver = ProjectSaver(pages_data)
        project_saver.serialize(project_name)

    def openProject(self, clear_current = True):
        open_dialog = FileDialog(self.main_window, 'open',
                                 file_filters = [(_('OCRFeeder Projects'), [], ['*.ocrf'])])
        response = open_dialog.run()
        project_file = None
        if response == Gtk.ResponseType.OK:
            project_file = open_dialog.get_filename()
            project_loader = ProjectLoader(project_file)
            pages = project_loader.loadConfiguration()
            if pages and clear_current:
                self.clear()
            for index in range(0, len(pages)):
                page = pages[index]
                self.__addImage(page.image_path,
                                select_image = index == 0,
                                page_data = page)
        open_dialog.destroy()
        return project_file

    def __askForNumberOfPages(self, title):
        # Sync the current reviewer's page with its data
        self.__getCurrentReviewer().savePageData()
        export_dialog = PagesToExportDialog(self.main_window,
                                            title)
        pages = self.pages_icon_view.getAllPages()
        # When there's only one document loaded or none,
        # we don't ask for the number of pages to export
        if len(pages) < 2:
            return pages
        response = export_dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            if export_dialog.current_page_button.get_active():
                pages = [self.__getCurrentReviewer().page]
            export_dialog.destroy()
            return pages
        else:
            export_dialog.destroy()
            return None

    def __askForFileName(self, extension = ''):
        save_dialog = FileDialog(self.main_window, 'save')
        response = save_dialog.run()
        if response == Gtk.ResponseType.OK:
            file_name = save_dialog.get_filename()
            if extension:
                if not file_name.endswith(extension):
                    file_name += extension
            if os.path.isfile(file_name):
                confirm_overwrite = Gtk.MessageDialog(message_type = Gtk.MessageType.QUESTION)
                message = _('<b>A file named "%(name)s" already exists. Do you want '
                            'to replace it?</b>\n\nThe file exists in "%(dir)s". '
                            'Replacing it will overwrite its contents.') % {
                             'name': os.path.basename(file_name),
                             'dir': os.path.dirname(file_name)}
                confirm_overwrite.set_markup(message)
                confirm_overwrite.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
                confirm_overwrite.add_button(_('Replace'), Gtk.ResponseType.OK)
                if confirm_overwrite.run() != Gtk.ResponseType.OK:
                    file_name = None
                confirm_overwrite.destroy()
            save_dialog.destroy()
            return file_name
        save_dialog.destroy()
        return None

    def choosePageSize(self):
        current_reviewer = self.__getCurrentReviewer()
        current_page = current_reviewer.page
        page_size_dialog = PageSizeDialog(self.main_window,
                                          (current_page.width, current_page.height))
        response = page_size_dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            size = page_size_dialog.getSize()
            if page_size_dialog.all_pages_radio.get_active():
                for page in self.pages_icon_view.getAllPages():
                    page.setSize(size)
            else:
                current_reviewer.page.setSize(size)
            debug('Page size: %s', size)
        page_size_dialog.destroy()
        self.__updateStatusBar(current_reviewer)

    def __getCurrentReviewer(self):
        return self.notebook.get_nth_page(self.notebook.get_current_page())

    def deleteCurrentPage(self):
        current_reviewer = self.__getCurrentReviewer()
        if not current_reviewer:
            return
        index = self.notebook.page_num(current_reviewer)
        self.notebook.remove_page(index)

    def unpaperTool(self):
        current_reviewer = self.__getCurrentReviewer()
        unpaper_dialog = UnpaperDialog(self.main_window,
                                       current_reviewer,
                                    self.configuration_manager.unpaper,
                                    self.configuration_manager.TEMPORARY_FOLDER)
        if unpaper_dialog.run() == Gtk.ResponseType.ACCEPT:
            unpapered_image = unpaper_dialog.getUnpaperedImage()
            current_reviewer.updateBackgroundImage(unpapered_image)
            unpaper_dialog.destroy()
        else:
            unpaper_dialog.destroy()

    def clear(self):
        # remove all pages from notebook
        for index in range(self.notebook.get_n_pages()):
            self.notebook.remove_page(0)
        self.pages_icon_view.clear()
        self.__updateStatusBar()

    def getPixbufsSorted(self):
        return self.pages_icon_view.source_images_selector.getPixbufsSorted()

    def updateFromConfiguration(self):
        for index in range(self.notebook.get_n_pages()):
            reviewer = self.notebook.get_nth_page(index)
            reviewer.setTextFillColor(self.configuration_manager.text_fill)
            reviewer.setBoxesStrokeColor(self.configuration_manager.boxes_stroke)
            reviewer.setImageFillColor(self.configuration_manager.image_fill)
            reviewer.updateBoxesColors()

    def zoomIn(self, zoom_value = 0.05):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.selectable_boxes_area.zoom(zoom_value)

    def zoomOut(self, zoom_value = -0.05):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.selectable_boxes_area.zoom(-abs(zoom_value))

    def zoomFit(self):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.zoomFit()

    def resetZoom(self):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.selectable_boxes_area.zoom(1, False)

    def selectPreviousArea(self, widget):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.selectable_boxes_area.selectPreviousArea()
        current_reviewer.focusCurrentEditorTextArea()

    def selectNextArea(self, widget):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.selectable_boxes_area.selectNextArea()
        current_reviewer.focusCurrentEditorTextArea()

    def selectAllAreas(self, widget):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.selectable_boxes_area.selectAllAreas()

    def deleteSelectedAreas(self, widget):
        current_reviewer = self.__getCurrentReviewer()
        current_reviewer.selectable_boxes_area.deleteSelectedAreas()

    def spellCheck(self, locale):
        current_reviewer = self.__getCurrentReviewer()
        SpellCheckerDialog(self.main_window, current_reviewer, locale)

    def updateOcrEngines(self, ocr_engines):
        n_pages = self.notebook.get_n_pages()
        index = 0
        while index < n_pages:
            reviewer = self.notebook.get_nth_page(index)
            reviewer.updateOcrEngines(ocr_engines)
            index += 1

class Editor:

    def __init__(self, pixbuf, ocr_engines, reviewer):
        self.configuration_manager = ConfigurationManager()
        self.pixbuf = pixbuf
        self.data_box = None
        self.box = None
        self.__connected_signal_handles_list = []
        self.box_editor = BoxEditor(pixbuf.get_width(), pixbuf.get_height())
        self.box_editor.connect('text-edited-by-user', self.checkHasText)
        self.reviewer = reviewer
        self.ocr_engines = ocr_engines
        self.updateOcrEngines(self.ocr_engines)
        self.box_editor.x_spin_button.connect('value-changed', self.__updateBoxX)
        self.box_editor.y_spin_button.connect('value-changed', self.__updateBoxY)
        self.box_editor.width_spin_button.connect('value-changed', self.__updateBoxWidth)
        self.box_editor.height_spin_button.connect('value-changed', self.__updateBoxHeight)
        self.box_editor.make_text_button.connect('toggled', self.__pressedTextContextButton)
        self.box_editor.make_image_button.connect('toggled', self.__pressedImageContextButton)
        self.box_editor.perform_ocr_button.connect('clicked', self.__pressedPerformOcrButton)
        self.box_editor.detect_angle_button.connect('clicked', self.__pressedAngleDetectionButton)
        self.box_editor.font_button.connect('font-set', self.__setDataBoxFont)
        self.box_editor.align_left_button.connect('toggled', self.__setDataBoxAlign, ALIGN_LEFT)
        self.box_editor.align_right_button.connect('toggled', self.__setDataBoxAlign, ALIGN_RIGHT)
        self.box_editor.align_center_button.connect('toggled', self.__setDataBoxAlign, ALIGN_CENTER)
        self.box_editor.align_fill_button.connect('toggled', self.__setDataBoxAlign, ALIGN_FILL)
        self.box_editor.letter_spacing_spin.connect('value-changed', self.__setDataBoxLetterSpacing)
        self.box_editor.line_spacing_spin.connect('value-changed', self.__setDataBoxLineSpacing)
        self.box_editor.ocr_combo_box.connect('changed', self._onOCREngineChanged)
        self.box_editor.languages_combo.connect('changed', self._onLanguageChanged)
        self.box_editor.hide()

    def __updateBoxX(self, spin_button):
        if self.__updating_data_box:
            return
        self.box.set_property('x', self.box_editor.getX())
        if spin_button.is_focus():
            self.update(self.box)

    def __updateBoxY(self, spin_button):
        if self.__updating_data_box:
            return
        self.box.set_property('y', self.box_editor.getY())
        if spin_button.is_focus():
            self.update(self.box)

    def __updateBoxWidth(self, spin_button):
        if self.__updating_data_box:
            return
        self.box.set_property('width', self.box_editor.getWidth())
        if spin_button.is_focus():
            self.update(self.box)

    def __updateBoxHeight(self, spin_button):
        if self.__updating_data_box:
            return
        self.box.set_property('height', self.box_editor.getHeight())
        if spin_button.is_focus():
            self.update(self.box)

    def __updateEditorX(self, widget, new_x):
        self.box_editor.setXRange()
        self.box_editor.setX(new_x)

    def __updateEditorY(self, widget, new_y):
        self.box_editor.setY(new_y)

    def __updateEditorWidth(self, widget, new_width):
        self.box_editor.setWidth(new_width)

    def __updateEditorHeight(self, widget, new_height):
        self.box_editor.setHeight(new_height)

    def __updateEditorImage(self, widget, new_image):
        self.box_editor.displayImage(new_image)

    def __updateBoxColor(self, widget, type):
        self.updateBoxColor(type)

    def updateBoxColor(self, type = None):
        if not self.box:
            return
        type = type or self.data_box.getType()
        fill_color = graphics.rgbaToInteger(self.reviewer.image_box_fill_color)
        if type == TEXT_TYPE:
            fill_color = graphics.rgbaToInteger(self.reviewer.text_box_fill_color)
        self.box.set_property('fill-color-rgba', fill_color)

    def __setDataBoxFont(self, font_button = None):
        font_button = font_button or self.box_editor.font_button
        font_description = Pango.FontDescription(font_button.get_font_name())
        self.data_box.setFontFace(font_description.get_family())
        self.data_box.setFontSize(font_description.get_size() / Pango.SCALE)
        self.data_box.setFontStyle(font_description.get_style())
        self.data_box.setFontWeight(font_description.get_weight())

    def __setDataBoxAlign(self, align_button, align_option):
        if align_button.get_active():
            self.data_box.setTextAlign(align_option)

    def __setDataBoxLetterSpacing(self, letter_spacing_button = None):
        letter_spacing_button = letter_spacing_button or self.box_editor.letter_spacing_spin
        self.data_box.setLetterSpacing(letter_spacing_button.get_value())

    def __setDataBoxLineSpacing(self, line_spacing_button = None):
        line_spacing_button = line_spacing_button or self.box_editor.line_spacing_spin
        self.data_box.setLineSpacing(line_spacing_button.get_value())

    def __setDataBoxLanguage(self, language = ''):
        language = language or self.box_editor.getLanguage()
        self.data_box.setLanguage(language)

    def _resetLanguages(self):
        index = self.box_editor.getSelectedOcrEngine()
        if index == -1:
            return
        engine = self.ocr_engines[index][0]
        self.box_editor.setAvailableLanguages(list(engine.getLanguages().keys()))

    def _onOCREngineChanged(self, combobox):
        self._resetLanguages()

    def _onLanguageChanged(self, combobox):
        if self.data_box:
            self.data_box.setLanguage(self.box_editor.getLanguage())

    def update(self, box):
        self.data_box.updateBoundsFromBox(self.box)
        self.data_box.updateImage(self.pixbuf)

    def updateOcrEngines(self, engines_list):
        engines_names = [engine.name for engine, path in engines_list]
        self.box_editor.setOcrEngines(engines_names)
        self._resetLanguages()

    def __pressedImageContextButton(self, toggle_button):
        self.data_box.setType(IMAGE_TYPE)
        self.box_editor.setOcrPropertiesSensibility(False)

    def __pressedTextContextButton(self, toggle_button):
        self.data_box.setType(TEXT_TYPE)
        self.box_editor.setOcrPropertiesSensibility(True)

    def __pressedPerformOcrButton(self, button):
        self.performOcr()

    def performOcr(self, engine_name = None):
        selected_engine_index = self.box_editor.getSelectedOcrEngine()
        if engine_name:
            for i in range(len(self.ocr_engines)):
                if self.ocr_engines[i][0].name == engine_name:
                    selected_engine_index = i
                    break
        self.box_editor.selectOcrEngine(selected_engine_index)
        image = graphics.convertPixbufToImage(self.box_editor.getImage())
        angle = self.box_editor.getAngle()
        if angle:
            image = graphics.getImageRotated(image, angle)
        engine = None
        if selected_engine_index != -1:
            engine = self.ocr_engines[selected_engine_index][0]
        self.reviewer.performOcrForDataBox(self.data_box, engine)
        self.updateDataBox(self.data_box)

    def performClassification(self, engine_name = None):
        selected_engine_index = self.box_editor.getSelectedOcrEngine()
        if engine_name:
            for i in range(len(self.ocr_engines)):
                if self.ocr_engines[i][0].name == engine_name:
                    selected_engine_index = i
                    break
        if selected_engine_index != None:
            engine = self.ocr_engines[selected_engine_index][0]
            type = engine.classify(self.box_editor.getText())
            self.box_editor.setType(type)

    def __pressedAngleDetectionButton(self, widget):
        image = graphics.convertPixbufToImage(self.box_editor.getImage())
        angle = graphics.getHorizontalAngleForText(image)
        debug('ANGLE: %s', angle)
        self.box_editor.setAngle(angle)

    def saveDataBox(self):
        if not self.data_box:
            return
        text = self.box_editor.getText()
        self.data_box.setText(text)
        angle = self.box_editor.getAngle()
        self.data_box.setAngle(angle)
        self.__setDataBoxFont()
        self.__setDataBoxLetterSpacing()
        self.__setDataBoxLineSpacing()
        self.__setDataBoxLanguage()

    def updateDataBox(self, data_box):
        self.__updating_data_box = True
        self.__disconnectDataBoxSignals()
        self.data_box = data_box
        if data_box is None:
            self.box_editor.hide()
            return
        self.box_editor.setX(self.data_box.x)
        self.box_editor.setY(self.data_box.y)
        self.box_editor.setWidth(self.data_box.width)
        self.box_editor.setHeight(self.data_box.height)
        self.box_editor.setType(self.data_box.type)
        self.box_editor.setText(self.data_box.text)
        self.box_editor.setFontSize(self.data_box.text_data.size)
        self.box_editor.setLineSpacing(self.data_box.getLineSpacing())
        self.box_editor.setLetterSpacing(self.data_box.getLetterSpacing())
        self.box_editor.setLanguage(self.data_box.getLanguage())
        self.__updating_data_box = False
        self.__connectDataBoxSignals()
        self.__updateBoxColor(None, self.data_box.type)

    def updateImage(self, pixbuf):
        self.pixbuf = pixbuf

    def __connectDataBoxSignals(self):
        handler_id = self.data_box.connect('changed_x', self.__updateEditorX)
        self.__connected_signal_handles_list.append(handler_id)
        handler_id = self.data_box.connect('changed_y', self.__updateEditorY)
        self.__connected_signal_handles_list.append(handler_id)
        handler_id = self.data_box.connect('changed_width',
                                           self.__updateEditorWidth)
        self.__connected_signal_handles_list.append(handler_id)
        handler_id = self.data_box.connect('changed_height',
                                           self.__updateEditorHeight)
        self.__connected_signal_handles_list.append(handler_id)
        handler_id = self.data_box.connect('changed_image',
                                           self.__updateEditorImage)
        self.__connected_signal_handles_list.append(handler_id)
        handler_id = self.data_box.connect('changed_type',
                                           self.__updateBoxColor)

    def setBoxes(self, box, data_box):
        self.saveDataBox()
        self.box = box
        self.updateDataBox(data_box)
        self.update(box)
        self.box_editor.show()

    def __disconnectDataBoxSignals(self):
        if not self.data_box:
            return
        for handle_id in self.__connected_signal_handles_list:
            self.data_box.disconnect(handle_id)
        self.__connected_signal_handles_list = []

    def checkHasText(self, widget, text):
        if not text:
            self.reviewer.main_window.copy_to_clipboard_menu.set_sensitive(False)
            self.reviewer.main_window.spellchecker_menu.set_sensitive(False)
        else:
            self.reviewer.main_window.copy_to_clipboard_menu.set_sensitive(True)
            self.reviewer.main_window.spellchecker_menu.set_sensitive(True)
