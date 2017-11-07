"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2014 Laurent Champagnac
#
#
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
# ===============================================================================
"""
import logging
import inspect
# noinspection PyUnresolvedReferences
import win32evtlog
# noinspection PyUnresolvedReferences
import win32api
# noinspection PyUnresolvedReferences
import win32security
from greenlet import GreenletExit
# noinspection PyUnresolvedReferences
import win32con
# noinspection PyUnresolvedReferences
import win32evtlogutil
from pythonsol.SolBase import SolBase
from pythonsol.meter.MeterManager import MeterManager

from knockdaemon.Core.KnockStat import KnockStat

logger = logging.getLogger(__name__)


class KnockDaemonEvent(object):
    """
    Knock daemon service event log wrappers
    """

    LOG_FILE = "undef"
    APP_NAME = "undef"

    @classmethod
    def write_manager_status(cls, k):
        """
        Write manager status to event log (windows implementation of transport lifecycle_run()
        :param k: KnockManager
        :type k: KnockManager
        """

        try:
            logger.info("Writing manager status")
            # Flush stuff
            ks = MeterManager.get(KnockStat)
            if not ks:
                logger.warning("ks none, potential race condition")
                return

            # Caller
            # noinspection PyBroadException
            try:
                caller = inspect.stack()[1][3]
            except:
                caller = ""

            # Get transport
            # noinspection PyProtectedMember
            for t in k._ar_knock_transport:
                # noinspection PyProtectedMember
                http_buf = \
                    "Running, HTTP, " \
                    "q.cur/max/di=%s/%s/%s, " \
                    "pbuf.pend/limit=%s/%s, " \
                    "pbuf.last/max=%s/%s, " \
                    "wbuf.last/max=%s/%s, " \
                    "wms.last/max=%s/%s, " \
                    "http.count:ok/ex/fail=%s:%s/%s/%s, " \
                    "s.ok/ko=%s/%s, " \
                    "self=%s" % \
                    (
                        t._queue_to_send.qsize(),
                        ks.transport_queue_max_size.get(),
                        ks.transport_queue_discard.get(),

                        ks.transport_buffer_pending_length.get(),
                        t._http_send_max_bytes,

                        ks.transport_buffer_last_length.get(),
                        ks.transport_buffer_max_length.get(),

                        ks.transport_wire_last_length.get(),
                        ks.transport_wire_max_length.get(),

                        ks.transport_wire_last_ms.get(),
                        ks.transport_wire_max_ms.get(),

                        ks.transport_call_count.get(),
                        ks.transport_ok_count.get(),
                        ks.transport_exception_count.get(),
                        ks.transport_failed_count.get(),

                        ks.transport_client_spv_processed.get(),
                        ks.transport_client_spv_failed.get(),
                        id(t),
                    )

                # Report
                cls._report_event(win32evtlog.EVENTLOG_INFORMATION_TYPE, "Lifecycle", "", caller, [http_buf, ])

            # Integrate UDP here, dirty but easier
            # We don't have access to KnockManager, and so don't have access to UDP server to flush out "_dict*" members #TODO : Additional UDP status logs
            udp_buf = \
                "Running, UDP, " \
                "recv.count:C/G/DTC=%s:%s/%s/%s, " \
                "recv.unk/ex=%s/%s, " \
                "notif.count/ex=%s/%s, " % \
                (
                    ks.udp_recv.get(),
                    ks.udp_recv_counter.get(),
                    ks.udp_recv_gauge.get(),
                    ks.udp_recv_dtc.get(),
                    ks.udp_recv_unknown.get(),
                    ks.udp_recv_ex.get(),
                    ks.udp_notify_run.get(),
                    ks.udp_notify_run_ex.get(),
                )

            # Report
            cls._report_event(win32evtlog.EVENTLOG_INFORMATION_TYPE, "Lifecycle", "", caller, [udp_buf])

        except GreenletExit:
            logger.debug("GreenletExit")
            return
        except Exception as e:
            logger.warning("Exception=%s", SolBase.extostr(e))

    @classmethod
    def report_info(cls, msg, data=None):
        """
        Report
        :param msg: str,unicode
        :type msg: str,unicode
        :param data: str,unicode,None
        :type data: str,unicode
        """
        # noinspection PyBroadException
        try:
            caller = inspect.stack()[1][3]
        except:
            caller = ""
        cls._report_event(win32evtlog.EVENTLOG_INFORMATION_TYPE, msg, data, caller)

    @classmethod
    def report_warn(cls, msg, data=None):
        """
        Report
        :param msg: str,unicode
        :type msg: str,unicode
        :param data: str,unicode,None
        :type data: str,unicode
        """
        # noinspection PyBroadException
        try:
            caller = inspect.stack()[1][3]
        except:
            caller = ""
        cls._report_event(win32evtlog.EVENTLOG_WARNING_TYPE, msg, data, caller)

    @classmethod
    def report_error(cls, msg, data=None):
        """
        Report
        :param msg: str,unicode
        :type msg: str,unicode
        :param data: str,unicode,None
        :type data: str,unicode
        """
        # noinspection PyBroadException
        try:
            caller = inspect.stack()[1][3]
        except:
            caller = ""
        cls._report_event(win32evtlog.EVENTLOG_ERROR_TYPE, msg, data, caller)

    @classmethod
    def _report_event(cls, event_type, msg, data, caller, ar_msg_add=None):
        """
        Report an event
        :param event_type: int
        :type event_type: int
        :param msg: str,unicode
        :type msg: str,unicode
        :param data: str,unicode,None
        :type data: str,unicode,None
        :param caller: str,None
        :type caller: str,None
        :param ar_msg_add: Additional messages list
        :param ar_msg_add: None, list
        """

        # Need some stuff
        ph = win32api.GetCurrentProcess()
        th = win32security.OpenProcessToken(ph, win32con.TOKEN_READ)
        my_sid = win32security.GetTokenInformation(th, win32security.TokenUser)[0]

        # Check
        if ar_msg_add is None:
            ar_msg_add = list()

        # Caller
        if not caller or len(caller) == 0:
            caller = "und"

        # Data
        if not data:
            data = ""

        # Data is binary, no readable, this is pure bullshit. Whatever, windows event log is broken by design.
        # SO :

        # List of stuff to push
        ar_msg = list()

        # Caller at top
        ar_msg.append("From " + caller)
        ar_msg.append(" ")

        # Message and data
        # A) TRY to push everything in msg (limited to 31,839 bytes, lets take margin)
        if len(msg) + len(data) <= 4096:
            # Push everything in message
            ar_msg.append(msg)
            ar_msg.append(" ")
            ar_msg.append(data)
            data = ""
        else:
            # data too big
            ar_msg.append(msg)

        # Additional
        if len(ar_msg_add) > 0:
            ar_msg.append(" ")
            for m in ar_msg_add:
                ar_msg.append(m)

        # Append
        ar_msg.append(" ")
        ar_msg.append("You may check log file=" + str(KnockDaemonEvent.LOG_FILE) + " for details")

        # Prepend by full message
        ar_temp = list()
        for m in ar_msg:
            if len(m.strip()) == 0:
                continue
            ar_temp.append(m)

        full_msg = " # ".join(ar_temp)
        ar_msg.insert(0, " ")
        ar_msg.insert(0, "--- Details below ---")
        ar_msg.insert(0, " ")
        ar_msg.insert(0, full_msg)

        # Report
        win32evtlogutil.ReportEvent(
            # Application name
            appName=KnockDaemonEvent.APP_NAME,
            # EventID, we provide eventType (zzz)
            eventID=1,
            # EventCategory, source specific, provide 0
            eventCategory=0,
            # EventType, aka win32evtlog.EVENTLOG_xxx
            eventType=event_type,
            # String
            strings=ar_msg,
            # Data
            data=data.encode("ascii"),
            # SID
            sid=my_sid
        )
