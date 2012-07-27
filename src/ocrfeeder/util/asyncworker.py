# -*- coding: utf-8 -*-

###########################################################################
#    OCRFeeder
#    Copyright (C) 2010 Igalia, S.L.
#
#    Author: Joaquim Rocha <jrocha@igalia.com>
#
#    This file was adapted from the SeriesFinale project.
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

from threading import Thread, BoundedSemaphore, RLock
import Queue
import gobject
from lib import debug
from multiprocessing import Pool


class AsyncItem(object):

    def __init__(self, target_method, target_method_args, finish_callback = None, finish_callback_args = (), process_pool=None):
        self.target_method = target_method
        self.target_method_args = target_method_args
        self.finish_callback = finish_callback
        self.finish_callback_args = finish_callback_args
        self.canceled = False
        self.process_pool = process_pool

    def run(self):
        if self.canceled:
            return
        results = error = None
        try:
            if self.process_pool is None:
                results = self.target_method(*self.target_method_args)
            else:
                results = self.process_pool.apply(self.target_method, self.target_method_args)

        except Exception, exception:
            debug(str(exception))
            error = exception
        if self.canceled or not self.finish_callback:
            return
        self.finish_callback_args += (results,)
        self.finish_callback_args += (error,)
        gobject.idle_add(self.finish_callback, *self.finish_callback_args)

    def cancel(self):
        self.canceled = True


ready_lock = RLock()


class AsyncWorker(Thread):

    def __init__(self, parallel=1):
        Thread.__init__(self)
        self.queue = Queue.Queue(0)
        self.daemon = True
        self.stopped = False
        self.item_number = -1

        self.parallel = parallel
        self.running_items = []
        self.worker_threads = []
        self.thread_sem = BoundedSemaphore(value=parallel)

        self.process_pool = None
        if parallel > 1:
            self.process_pool = Pool(parallel)


    def run(self):
        try:
            while not self.stopped and not self.queue.empty():
                try:
                    async_item = self.queue.get(False)

                    thread = Thread(target=self._run_item, args=(async_item, ))
                    self.running_items.append(async_item)
                    self.thread_sem.acquire()
                    async_item.process_pool = self.process_pool
                    self.worker_threads.append(thread)
                    self.item_number += 1
                    thread.start()

                except Queue.Empty:
                    if self.process_pool is not None:
                        self.process_pool.close()
                    break

                except Exception, exception:
                    debug(str(exception))
                    self.stop()
        finally:
            with ready_lock:
                self.queue_processing = False
            for thread in self.worker_threads:
                thread.join()
            self.stopped = True
            if self.process_pool is not None:
                self.process_pool.terminate()


    def stop(self):
        self.stopped = True
        if len(self.running_items):
            for async_item in self.running_items:
                async_item.cancel()
        if self.process_pool is not None:
            self.process_pool.close()


    def _run_item(self, async_item):
        try:
            async_item.run()
            self.queue.task_done()
            self.running_items.remove(async_item)
        finally:
            self.thread_sem.release()

