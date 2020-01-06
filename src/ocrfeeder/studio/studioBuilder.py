###########################################################################
#    OCRFeeder - The complete OCR suite
#    Copyright (C) 2009-2013 Joaquim Rocha
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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GooCanvas', '2.0')
gi.require_version('GtkSpell', '3.0')
from ocrfeeder.util import lib
from ocrfeeder.util.constants import *
import sys
import os.path
import urllib.request, urllib.parse, urllib.error
from . import widgetPresenter
from .widgetModeler import ImageReviewer_Controler
from .dataHolder import DataBox, TextData
from .pagesiconview import PagesIconView
from ocrfeeder.feeder.ocrEngines import Engine, OcrEnginesManager
from ocrfeeder.feeder.documentGeneration import DocumentGeneratorManager
from ocrfeeder.util.configuration import ConfigurationManager
from ocrfeeder.util.asyncworker import AsyncItem
from ocrfeeder.util.log import debug
from argparse import ArgumentParser
import gettext
import locale
from gi.repository import Gdk, Gtk
_ = gettext.gettext

class Studio:

    TARGET_TYPE_URI_LIST = 80

    def __init__(self):

        # i18n
        languages = []
        lc, encoding = locale.getdefaultlocale()
        if lc:
            languages = [lc]
        languages += DEFAULT_LANGUAGES
        gettext.bindtextdomain(OCRFEEDER_COMPACT_NAME, LOCALE_DIR)
        gettext.textdomain(OCRFEEDER_COMPACT_NAME)
        language = gettext.translation(OCRFEEDER_COMPACT_NAME, LOCALE_DIR,
                                       languages = languages, fallback = True)
        _ = language.gettext

        self.EXPORT_FORMATS = {0: ('ODT', _('ODT')),
                               1: ('HTML', _('HTML')),
                               2: ('PDF', _('PDF')),
                               3: ('TXT', _('Plain Text'))}

        self.title = OCRFEEDER_STUDIO_NAME
        self.main_window = widgetPresenter.MainWindow()
        self.main_window.set_title(self.title)
        self.document_generator_manager = DocumentGeneratorManager()
        self.configuration_manager = ConfigurationManager()
        self.ocr_engines_manager = OcrEnginesManager(self.configuration_manager)
        self.configuration_manager.loadConfiguration()
        user_engines_folder = self.configuration_manager.user_engines_folder
        self.engines_needing_update = \
            self.ocr_engines_manager.makeEnginesFromFolder(user_engines_folder)
        self.ocr_engines = self.ocr_engines_manager.ocr_engines
        self.pages_icon_view = PagesIconView()
        self.pages_icon_view.setDeleteCurrentPageFunction(self.deleteCurrentPage)
        self.pages_icon_view.get_model().connect('row-inserted',
                                                 self.__pagesUpdatedCallback)
        self.pages_icon_view.get_model().connect('row-deleted',
                                                 self.__pagesUpdatedCallback)
        self.pages_icon_view.show()
        self.main_window.main_area_left.add_with_viewport(self.pages_icon_view)
        self.images_selectable_area = {}
        self.source_images_controler = ImageReviewer_Controler(self.main_window,
                                                               self.pages_icon_view,
                                                               self.ocr_engines,
                                                               self.configuration_manager)
        self.project_name = None

        toolbar_callback_dict = {'recognizePage': self.__recognizePageAction,
                                 'recognizeDocument': self.__recognizeDocumentAction,
                                 'export_to_odt': self.exportToOdt}

        menubar_callback_dict = {'exit': self.quit, 'add_image': self.addImage, 'export_to_odt': self.exportToOdt, 'edit_page': self.choosePageSize,
                                 'delete_page': self.deleteCurrentPage, 'export_dialog': self.exportDialog, 'add_folder': self.addFolder,
                                 'import_pdf': self.importPdf, 'save_project': self.saveProject, 'save_project_as': self.saveProjectAs,
                                 'open_project': self.openProject, 'append_project': self.appendProject,'clear': self.clear,
                                 'unpaper': self.unpaper, 'preferences': self.preferences, 'about': self.about,
                                 'ocr_engines': self.ocrEngines, 'zoom_in': self.zoomIn, 'zoom_out': self.zoomOut,
                                 'zoom_fit': self.zoomFit, 'reset_zoom': self.resetZoom,
                                 'recognize_areas': self.__recognizeSelectedAreas,
                                 'import_from_scanner': self.importFromScanner,
                                 'select_next_area': self.source_images_controler.selectNextArea,
                                 'select_previous_area': self.source_images_controler.selectPreviousArea,
                                 'select_all_areas': self.source_images_controler.selectAllAreas,
                                 'delete_selected_areas': self.source_images_controler.deleteSelectedAreas,
                                 'image_deskewer': self.source_images_controler.deskewCurrentImage,
                                 'copy_to_clipboard': self.source_images_controler.copyRecognizedTextToClipboard,
                                 'spell_checker': self.spellChecker,
                                 'help_contents': self.showHelpContents,
                                 'move_page_down': self.movePageDown,
                                 'move_page_up': self.movePageUp,
                                 'select_next_page': self.selectNextPage,
                                 'select_previous_page': self.selectPreviousPage,
                                 }

        self.main_window.setHeader(menubar_callback_dict, toolbar_callback_dict)
        self.main_window.setDestroyEvent(self.quit)

        parser = ArgumentParser(description=OCRFEEDER_STUDIO_COMMENTS)
        parser.add_argument('images', metavar='IMAGE',
                            nargs='*', help='images to be automatically added '
                            'on start-up')
        parser.add_argument('-d', '--dir', help='directory with images to be '
                            'added automatically on start-up')
        parser.add_argument('-v', '--version', action='version',
                            version='%(prog)s ' + OCRFEEDER_STUDIO_VERSION)
        args = parser.parse_args()
        imgs = args.images
        if imgs:
            self.__addImagesToReviewer(imgs)
        if args.dir:
            self.__addImagesToReviewer(lib.getImagesFromFolder(args.dir))

        self.main_window.setHasSelectedBoxes(False)
        self.main_window.setHasContentBoxes(False)
        self.main_window.setNumberOfPages(
            self.pages_icon_view.getNumberOfPages())

        # Show dialog to choose system-wide OCR engines when no engine was found
        if not self.ocr_engines:
            engines = self.configuration_manager.getEnginesInSystem()
            if engines:
                add_engines_dialog = widgetPresenter.SystemEnginesDialog(engines)
                response = add_engines_dialog.run()
                if response == Gtk.ResponseType.ACCEPT:
                    for engine in add_engines_dialog.getChosenEngines():
                        self.ocr_engines_manager.addNewEngine(engine)
                add_engines_dialog.destroy()

        else:
            self.__askForEnginesMigration()

        self._last_images_dir = ''

        if not self.ocr_engines:
            self.warnNoOCREngines()

    def run(self):
        Gdk.threads_init()
        Gdk.threads_enter()
        Gtk.main()
        Gdk.threads_leave()

    def addImage(self, widget):
        file_open_dialog = widgetPresenter.FileDialog(self.main_window,
                                'open',
                                file_filters = [(_('Images'), ['image/*'], [])])
        file_open_dialog.set_select_multiple(True)

        if self._last_images_dir:
            file_open_dialog.set_current_folder(self._last_images_dir)

        response = file_open_dialog.run()

        if response == Gtk.ResponseType.OK:
            self.__addImagesToReviewer(file_open_dialog.get_filenames())

        self._last_images_dir = file_open_dialog.get_current_folder()
        file_open_dialog.destroy()

    def importFromScanner(self, widget):
        dialog = widgetPresenter.QueuedEventsProgressDialog(self.main_window)
        item_obtain = AsyncItem(lib.obtainScanners,(),
                                self.__obtainScannersFinishedCb,(dialog,))
        info_obtain = (_('Obtaining scanners'), _('Please wait…'))
        dialog.setItemsList([(info_obtain, item_obtain)])
        dialog.run()

    def __obtainScannersFinishedCb(self, dialog, devices, error):
        dialog.destroy()
        device = None
        if len(devices) > 1:
            scanner_chooser_dialog = widgetPresenter.ScannerChooserDialog(\
                                                    self.main_window,
                                                    devices)
            Gdk.threads_enter()
            response = scanner_chooser_dialog.run()
            Gdk.threads_leave()
            if response == Gtk.ResponseType.ACCEPT:
                device = scanner_chooser_dialog.getSelectedDevice()
            scanner_chooser_dialog.destroy()
            if response != Gtk.ResponseType.ACCEPT:
                return
        elif len(devices) == 1:
            device = devices[0][0]
        if device:
            dialog_scan = widgetPresenter.QueuedEventsProgressDialog(\
                self.main_window)
            item_scan = AsyncItem(lib.scan,(device,),
                                  self.__scanFinishedCb,(dialog_scan,))
            info_scan = (_('Scanning'), _('Please wait…'))
            dialog_scan.setItemsList([(info_scan, item_scan)])
            dialog_scan.run()
        else:
            error = widgetPresenter.SimpleDialog(self.main_window,
                                             _("No scanner devices were found"),
                                             _("Error"),
                                             'warning')
            Gdk.threads_enter()
            error.run()
            Gdk.threads_leave()

    def __scanFinishedCb(self, dialog, image_path, error):
        dialog.destroy()
        if image_path:
            Gdk.threads_enter()
            self.__addImagesToReviewer([image_path])
            Gdk.threads_leave()
        else:
            error = widgetPresenter.SimpleDialog(self.main_window,
                                             _("Error scanning page"),
                                             _("Error"),
                                             'warning')
            Gdk.threads_enter()
            error.run()
            Gdk.threads_leave()

    def importPdf(self, widget):
        file_open_dialog = widgetPresenter.FileDialog(self.main_window,
                        'open',
                        file_filters = [(_('PDF'), ['application/pdf'], [])])
        response = file_open_dialog.run()
        files = []
        if response == Gtk.ResponseType.OK:
            files = file_open_dialog.get_filenames()
        file_open_dialog.destroy()
        for file_name in files:
            dialog = widgetPresenter.QueuedEventsProgressDialog(
                                                 self.main_window)
            item = AsyncItem(lib.convertPdfToImages,
                             (file_name,
                              self.configuration_manager.TEMPORARY_FOLDER),
                             self.__loadPdfFinishedCb,
                             (dialog,))
            info = (_('Loading PDF'), _('Please wait…'))
            dialog.setItemsList([(info, item)])
            dialog.run()

    def __loadPdfFinishedCb(self, dialog, folder, error):
        self.__addImagesToReviewer(lib.getImagesFromFolder(folder))
        dialog.destroy()

    def addFolder(self, widget):
        file_open_dialog = widgetPresenter.FileDialog(self.main_window,
                                                      'select-folder')
        response = file_open_dialog.run()
        if response == Gtk.ResponseType.OK:
            filenames = file_open_dialog.get_filenames()
            file_open_dialog.destroy()
            for folder in filenames:
                self.__addImagesToReviewer(lib.getImagesFromFolder(folder))
        file_open_dialog.destroy()

    def exportToFormat(self, format, name):
        generator = self.document_generator_manager.get(format)
        self.source_images_controler.exportPagesWithGenerator(generator,
                                                              name)

    def exportToOdt(self, widget):
        self.exportToFormat('ODT', 'ODT')

    def exportDialog(self, widget):
        format_names = [format[1] for format in self.EXPORT_FORMATS.values()]
        export_dialog = widgetPresenter.ExportDialog(self.main_window,
                                                     _('Export pages'),
                                                     format_names)
        response = export_dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            format = export_dialog.getSelectedFormat()
            export_dialog.destroy()
            if format != -1:
                # Retrieve and run the exportation function
                self.exportToFormat(self.EXPORT_FORMATS[format][0],
                                    self.EXPORT_FORMATS[format][1])
            return None
        export_dialog.destroy()
        return None

    def choosePageSize(self, widget):
        self.source_images_controler.choosePageSize()

    def deleteCurrentPage(self, widget):
        delete_dialog = widgetPresenter.QuestionDialog(self.main_window,
                                                       _('Are you sure you want to delete the current image?'))
        response = delete_dialog.run()
        if response == Gtk.ResponseType.YES:
            self.source_images_controler.deleteCurrentPage()
            self.pages_icon_view.deleteCurrentSelection()
        delete_dialog.destroy()

    def movePageDown(self, widget):
        self.pages_icon_view.movePage(1)

    def movePageUp(self, widget):
        self.pages_icon_view.movePage(-1)

    def selectNextPage(self, widget):
        self.pages_icon_view.selectPageFromOffset(1)

    def selectPreviousPage(self, widget):
        self.pages_icon_view.selectPageFromOffset(-1)

    def __addImagesToReviewer(self, images):
        if not images:
            return
        self.source_images_controler.addImages(images)

    def __recognizePageAction(self, widget):
        if not self.ocr_engines_manager.ocr_engines:
            self.warnNoOCREngines()
            return
        self.source_images_controler.recognizeCurrentPage()

    def __recognizeDocumentAction(self, widget):
        if not self.ocr_engines_manager.ocr_engines:
            self.warnNoOCREngines()
            return
        self.source_images_controler.recognizeDocument()

    def __recognizeSelectedAreas(self, widget):
        if not self.ocr_engines_manager.ocr_engines:
            self.warnNoOCREngines()
            return
        self.source_images_controler.recognizeSelectedAreas()

    def setProjectName(self, project_name):
        self.project_name = project_name
        project_title = os.path.splitext(os.path.basename(self.project_name))[0]
        self.main_window.set_title('%s - %s' % (self.title, project_title))

    def saveProjectAs(self, widget = None):
        file_name = self.source_images_controler.saveProjectAs()
        if file_name:
            self.setProjectName(file_name)
            self.saveProject()

    def saveProject(self, widget = None):
        if self.project_name:
            self.source_images_controler.saveProject(self.project_name)
        else:
            self.saveProjectAs()

    def appendProject(self, widget = None):
        self.__loadProject(False)

    def openProject(self, widget = None):
        self.__loadProject()

    def __loadProject(self, clear_current = True):
        project_title = self.source_images_controler.openProject(clear_current)
        if project_title:
            self.setProjectName(project_title)

    def clear(self, widget = None):
        dialog = widgetPresenter.QuestionDialog(self.main_window,
                                                _('Are you sure you want '
                                                  'to clear the project?'))
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.source_images_controler.clear()
        dialog.destroy()

    def unpaper(self, widget = None):
        self.source_images_controler.unpaperTool()

    def spellChecker(self, widget = None):
        self.source_images_controler.spellCheck(locale.getdefaultlocale()[0])

    def preferences(self, widget = None):
        parent = self.main_window
        preferences_dialog = widgetPresenter.PreferencesDialog(parent,
                                            self.configuration_manager,
                                            self.ocr_engines_manager.ocr_engines)
        if preferences_dialog.run() == Gtk.ResponseType.ACCEPT:
            preferences_dialog.saveToManager()
            self.source_images_controler.updateFromConfiguration()
        preferences_dialog.destroy()

    def ocrEngines(self, widget = None):
        ocr_dialog = widgetPresenter.OcrManagerDialog(self.main_window,
                                                      self.ocr_engines_manager)
        ocr_dialog.run()
        if ocr_dialog.modified:
            ocr_engines = self.ocr_engines_manager.ocr_engines
            self.source_images_controler.updateOcrEngines(ocr_engines)
        ocr_dialog.destroy()

    def warnNoOCREngines(self):
        debug('No OCR engines found')
        dialog = Gtk.MessageDialog(self.main_window,
                                   Gtk.DialogFlags.MODAL |
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   Gtk.MessageType.INFO)
        dialog.set_title(_('No OCR engines available'))
        dialog.set_markup(_('No OCR engines were found in the system.\n'
                            'Please make sure you have OCR engines installed '
                            'and available.'))
        dialog.add_buttons(_('_Ignore'),
                           Gtk.ResponseType.CANCEL,
                           _('_Open OCR Engines Manager Dialog'),
                           Gtk.ResponseType.OK)

        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.ocrEngines()

    def enginesTool(self, widget = None):
        pass

    def about(self, widget = None):
        about_dialog = widgetPresenter.CustomAboutDialog(self.main_window)
        if about_dialog.run():
            about_dialog.destroy()

    def showHelpContents(self, widget = None):
        Gtk.show_uri(self.main_window.get_screen(),
                     'help:ocrfeeder',
                     Gtk.get_current_event_time())

    def zoomIn(self, widget = None):
        self.source_images_controler.zoomIn()

    def zoomOut(self, widget = None):
        self.source_images_controler.zoomOut()

    def resetZoom(self, widget = None):
        self.source_images_controler.resetZoom()

    def zoomFit(self, widget = None):
        self.source_images_controler.zoomFit()

    def __pagesUpdatedCallback(self, model, path, iter = None):
        self.main_window.setNumberOfPages(
            self.pages_icon_view.getNumberOfPages())

    def __askForEnginesMigration(self):
        auto_update = self.engines_needing_update['auto']
        if auto_update:
            for migration in auto_update:
                self.ocr_engines_manager.migrateEngine(migration['engine'],
                                                       migration['configuration'])

        manual_update = self.engines_needing_update['manual']
        if manual_update:
            names = []
            for migration in manual_update:
                names.append(migration['engine'].name)
            dialog = Gtk.MessageDialog(self.main_window,
                                       Gtk.DialogFlags.MODAL |
                                       Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                       Gtk.MessageType.WARNING)
            dialog.add_buttons(_('_Keep Current Configuration') ,
                               Gtk.ResponseType.CANCEL,
                               _('_Open OCR Engines Manager Dialog'),
                               Gtk.ResponseType.OK)
            message = _('The following OCR engines\' arguments '
                        'might need to be updated but it appears '
                        'you have changed their default configuration so '
                        'they need to be updated manually:\n  '
                        '<b>%(engines)s</b>\n\n'
                        'If you do not want to keep your changes '
                        'you can just remove the current configuration '
                        'and have your OCR engines detected again.') % \
                        {'engines': '\n'.join(names)}
            dialog.set_markup(message)
            response = dialog.run()
            dialog.destroy()
            for migration in manual_update:
                self.ocr_engines_manager.migrateEngine(migration['engine'],
                                                migration['configuration'])
            if response == Gtk.ResponseType.OK:
                self.ocrEngines()

    def quit(self, widget = None, data = None):
        if not self.project_name and not self.pages_icon_view.isEmpty():
            quit_dialog = widgetPresenter.QuestionDialog(self.main_window,
                                                         '<b>' + _("The project hasn't been saved.") + '</b>', Gtk.ButtonsType.NONE)
            quit_dialog.format_secondary_text(_('Do you want to save it before closing?'))
            quit_dialog.add_buttons(_('Close anyway'), Gtk.ResponseType.NO, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE_AS, Gtk.ResponseType.YES)
            response = quit_dialog.run()
            quit_dialog.destroy()
            if response == Gtk.ResponseType.YES:
                self.saveProjectAs()
                self.__main_quit()
            elif response == Gtk.ResponseType.NO:
                quit_dialog.destroy()
                self.__main_quit()
            else:
                return True
        else:
            self.__main_quit()
        return False

    def __main_quit(self):
        self.configuration_manager.configurationToXml()
        self.configuration_manager.removeTemporaryFolder()
        Gtk.main_quit()
