###########################################################################
#    OCRFeeder - The complete OCR suite
#    Copyright (C) 2009-2013 Joaquim Rocha <me@joaquimrocha.com>
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

import os
import gettext
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango
_ = gettext.gettext

class PagesListStore(Gtk.ListStore):

    def __init__(self, list_of_images = []):
        super(PagesListStore, self).__init__(str, GdkPixbuf.Pixbuf, object)
        if len(list_of_images):
            for path in list_of_images:
                self.__renderImage(path, self.__generateImageName(path))

    def addImage(self, page_data):
        image_name = self.__generateImageName(page_data.image_path)
        return self.__renderImage(image_name, page_data)

    def __renderImage(self, image_name, page_data):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(page_data.image_path,
                                                        150, 100)
        return self.append([image_name, pixbuf, page_data])

    def __countEqualPathsStored(self, path):
        iter = self.get_iter_first()
        counter = 0
        while iter != None:
            page_data = self.get_value(iter, 2)
            image_path = page_data.image_path
            if image_path == path:
                counter += 1
            iter = self.iter_next(iter)
        return counter

    def __generateImageName(self, path):
        image_name = os.path.basename(path)
        number_of_equal_paths = self.__countEqualPathsStored(path)
        if number_of_equal_paths:
            image_name += ' ('+ str(number_of_equal_paths + 1) + ')'
        return image_name

    def getPixbufsSorted(self):
        pixbufs = []
        iter = self.get_iter_first()
        while iter != None:
            pixbufs.append(self.get_value(iter, 2))
            iter = self.iter_next(iter)
        return pixbufs

    def removeIter(self, path):
        iter = self.get_iter(path)
        self.remove(iter)

class PagesIconView(Gtk.IconView):

    MAX_WIDTH_CHARS = 50

    def __init__(self):
        Gtk.IconView.__init__(self)
        self.set_model(PagesListStore())
        self.get_accessible().set_name(_('Pages'))
        self.set_pixbuf_column(1)
        self.set_item_orientation(Gtk.Orientation.VERTICAL)
        self.set_columns(1)
        self.set_reorderable(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.set_selection_mode(Gtk.SelectionMode.BROWSE)
        text_renderer = Gtk.CellRendererText.new()
        text_renderer.set_property('ellipsize-set', True)
        text_renderer.set_property('max-width-chars', self.MAX_WIDTH_CHARS)
        text_renderer.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        self.pack_start(text_renderer, False)
        self.add_attribute(text_renderer, 'text', 0)
        area = self.get_area()

    def getSelectedPageData(self):
        selected_items = self.get_selected_items()
        if len(selected_items):
            selected_item_path = selected_items[0]
            model = self.get_model()
            iter = model.get_iter(selected_item_path)
            return self.get_model().get_value(iter, 2)
        return None

    def getAllPages(self):
        model = self.get_model()
        pages = []
        iter = model.get_iter_first()
        while iter:
            pages.append(model.get_value(iter, 2))
            iter = model.iter_next(iter)
        return pages

    def setDeleteCurrentPageFunction(self, function):
        self.delete_current_page_function = function

    def deleteCurrentSelection(self):
        selected_items = self.get_selected_items()
        if len(selected_items):
            selected_item_path = selected_items[0]
            self.get_model().removeIter(selected_item_path)
            first_iter = self.get_model().get_iter_first()
            if first_iter:
                self.select_path(self.get_model().get_path(first_iter))

    def clear(self):
        self.get_model().clear()

    def _getIndexFromOffset(self, offset):
        selected_items = self.get_selected_items()
        if not len(selected_items):
            return
        selected_item_path = selected_items[0]
        model = self.get_model()
        iter = model.get_iter(selected_item_path)
        index = model.get_path(iter)[0] + offset
        number_of_items = model.iter_n_children(None)
        if index < 0:
            index = number_of_items + offset
        elif index == number_of_items:
            index = 0
        return index

    def movePage(self, offset):
        selected_items = self.get_selected_items()
        if not len(selected_items):
            return
        selected_item_path = selected_items[0]
        model = self.get_model()
        index = self._getIndexFromOffset(offset)
        if index != selected_item_path[0] + offset:
            return
        model.swap(model.get_iter((index,)),
                   model.get_iter(selected_item_path))
        self.select_path(Gtk.TreePath(index))

    def selectPageFromOffset(self, offset):
        selected_items = self.get_selected_items()
        if not len(selected_items):
            return
        selected_item_path = selected_items[0]
        model = self.get_model()
        index = self._getIndexFromOffset(offset)
        self.select_path(Gtk.TreePath(index))

    def getNumberOfPages(self):
        return self.get_model().iter_n_children(None)

    def isEmpty(self):
        return self.get_model().get_iter_first() is None
