# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
# Copyright (C) 2006 Lukáš Lalinský
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import sys
import traceback
from PyQt4.QtCore import QRunnable, QCoreApplication, QEvent, QThread


class ProxyToMainEvent(QEvent):

    def __init__(self, func, *args, **kwargs):
        QEvent.__init__(self, QEvent.User)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args, **self.kwargs)


class Runnable(QRunnable):

    def __init__(self, func, next, os_priority=0):
        QRunnable.__init__(self)
        self.func = func
        self.next = next
        self.thread_priority = min(QThread.IdlePriority,max(QThread.TimeCriticalPriority,
            QThread.currentThread().priority() + os_priority))

    def run(self):
        QThread.currentThread().setPriority(self.thread_priority)
        try:
            result = self.func()
        except:
            from picard import log
            log.error(traceback.format_exc())
            to_main(self.next, error=sys.exc_info()[1])
        else:
            to_main(self.next, result=result)


def run_task(func, next, priority=0, thread_pool=None, os_priority=0):
    if thread_pool is None:
        thread_pool = QCoreApplication.instance().thread_pool
    thread_pool.start(Runnable(func, next, os_priority=os_priority), priority)


def to_main(func, *args, **kwargs):
    QCoreApplication.postEvent(QCoreApplication.instance(),
                               ProxyToMainEvent(func, *args, **kwargs))
    # If we are in a worker thread, use processEvents to pass control to the
    # main thread to execute the event we just posted. If we don't do this
    # the main thread may not get CPU for a long time.
    # See http://www.dabeaz.com/python/UnderstandingGIL.pdf for details.
    #
    # If we are in the main thread already, we should wait for the event loop to
    # process the event because if we run processEvents we leave this on the stack
    # and after this happens a lot we can get Recursion Level Exceeded errors.
    if QCoreApplication.instance().thread() != QThread.currentThread():
        QCoreApplication.processEvents()
