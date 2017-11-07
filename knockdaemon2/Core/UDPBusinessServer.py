"""
-*- coding: utf-8 -*-
===============================================================================

Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac



 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2
 of the License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 ===============================================================================
"""
import _socket
import logging
import socket
import sys
import ujson
from collections import OrderedDict
from errno import EWOULDBLOCK

import gevent
import os
from gevent.lock import RLock
from gevent.server import DatagramServer
from gevent.threading import Lock
from pysolbase.SolBase import SolBase
from pysolmeters.AtomicFloat import AtomicFloatSafe
from pysolmeters.DelayToCount import DelayToCount
from pysolmeters.Meters import Meters
from pysoltcp.tcpbase.TcpSocketManager import TcpSocketManager

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)


class BusinessServer(DatagramServer):
    """
    Business server
    """

    COUNTER = 'C'
    GAUGE = 'G'
    DTC = 'DTC'
    KNOCK_PREFIX_KEY = 'k.business.'

    def __init__(self, manager, socket_name, windows_host, windows_port, send_back_udp, notify_interval_ms, *args, **kwargs):
        """
        Init
        :param manager: KnockManager
        :type manager: KnockManager
        :param send_back_udp: bool
        :type send_back_udp: bool
        :param notify_interval_ms: int
        :param notify_interval_ms: int
        :param socket_name: str
        :type socket_name: str
        :param windows_host: str
        :type windows_host: str
        :param windows_port: int
        :type windows_port: int
        :param args:
        :param kwargs:
        """

        # Udp
        self._send_back_udp = send_back_udp

        # Windows
        self._windows_host = windows_host
        self._windows_port = windows_port

        # Lock
        self._increment_lock = Lock()
        self._gauge_lock = Lock()
        self._dtc_lock = Lock()

        # Dict
        self._dict_increment = dict()
        self._dict_gauge = dict()
        self._dict_dtc = dict()

        # PROBES
        self._probe_inc = KnockProbe()
        self._probe_inc.category = "/business/increment"
        self._probe_inc.set_manager(manager)

        self._probe_gauge = KnockProbe()
        self._probe_gauge.set_manager(manager)
        self._probe_gauge.category = "/business/gauge"

        self._probe_dtc = KnockProbe()
        self._probe_dtc.set_manager(manager)
        self._probe_dtc.category = "/business/dtc"

        # Set manager
        self._manager = manager

        # Notify
        self._notify_greenlet = None

        # Notify interval ms
        self._notify_interval_ms = notify_interval_ms

        # Notify lock
        self._notify_lock = RLock()

        # Server greenlet
        self._server_greenlet = None

        # Our started flag
        self._is_started = False

        # Socket
        self._socket_name = socket_name
        self._soc = None

        # Allocate socket and bind it
        self._create_socket_and_bind()

        # Call base
        super(BusinessServer, self).__init__(self._soc, *args, **kwargs)

    def _create_socket_and_bind(self):
        """
        Create socket
        """

        if self._soc:
            logger.info("Bypass, _soc set")
            return

        # Listen
        logger.info("Binding")

        # Alloc
        if PTools.get_distribution_type() == "windows":
            # ==========================
            # Ahah, no support for domain socket on Windows
            # ==========================
            # Will not go for pipes
            # So we target local host (dirty)
            logger.warn("Windows detected, using UDP toward %s:%s (lacks of domain socket support)", self._windows_host, self._windows_port)
            logger.warn("You may (will) experience performance issues over the UDP channel (possible lost of packets)")
            logger.warn("If you are using client library, please be sure to NOT target the unix domain socket on this machine.")
            self._soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Switch to non blocking
            self._soc.setblocking(0)

            # Bind
            self._soc.bind((self._windows_host, self._windows_port))
        else:
            # ==========================
            # Linux rocks (and debian rocks more)
            # ==========================

            # noinspection PyUnresolvedReferences
            self._soc = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            if os.path.exists(self._socket_name):
                os.remove(self._socket_name)

            # Switch to non blocking
            self._soc.setblocking(0)

            # Bind
            self._soc.bind(self._socket_name)

        # Buffer
        logger.info("Recv buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
        logger.info("Send buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))

        # Increase recv
        try:
            self._soc.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 1024)
        except Exception as e:
            logger.info("SO_RCVBUF increased failed, ex=%s", SolBase.extostr(e))

        # Buffer
        logger.info("Recv buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
        logger.info("Send buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))

    # ------------------------------
    # START / STOP OVERRIDE
    # ------------------------------

    def start(self):
        """
        Start server
        """

        if self._is_started:
            logger.warn("Already started, bypass")
            return

        # Base start
        logger.info("Starting")

        # Spawn async
        self._server_greenlet = gevent.spawn(super(BusinessServer, self).start)
        logger.info("Started")

        # Signal started
        self._is_started = True

        # Notify schedule
        self._notify_schedule_next()

    def stop(self, timeout=None):
        """
        Stop server
        :param timeout: None,Timeout
        """

        if not self._is_started:
            logger.warn("Not started, bypass")
            return

        # Base stop
        logger.info("Stopping")
        super(BusinessServer, self).stop(timeout=timeout)
        logger.info("Stopped")

        # Greenlet stop
        if self._server_greenlet:
            logger.info("Killing _server_greenlet")
            self._server_greenlet.kill()
            self._server_greenlet = None

        # Notify cancel
        # We may lost some stuff (in memory, not yet notified), dont care at this stage
        self._notify_schedule_cancel()

        # Close socket
        TcpSocketManager.safe_close_socket(self._soc)

        # Remove socket
        try:
            if os.path.exists(self._socket_name):
                os.remove(self._socket_name)
        except Exception as e:
            logger.warn("Socket file remove ex=%s", SolBase.extostr(e))

        # Signal stopped
        self._is_started = False

    # -------------------------
    # WE OVERRIDE THE do_read of gevent.server.DatagramServer#do_read
    # in order to bypass recvfrom 8192
    # for UDP over AF_UNIX
    # -------------------------

    def do_read(self):
        try:
            # Override
            data, address = self._socket.recvfrom(61440)
        except _socket.error as err:
            if err.args[0] == EWOULDBLOCK:
                return
            raise
        return data, address

    # ------------------------------
    # HANDLE INCOMING STUFF
    # ------------------------------

    def handle(self, data, address):  # pylint:disable=method-hidden
        """
        Handle one udp message
        reply:
            KO-NR : KO but do not retry
            KO-R : KO and retry
            OK : Treated
        :param data: data
        :param address: address
        """

        ms_start = SolBase.mscurrent()
        try:

            # logger.info('Incoming, addr=%s, data=%s', address[0], repr(data))

            # Load json
            data_json = ujson.loads(data.strip())

            # Process
            for item, cur_type, value in data_json:
                try:
                    if cur_type == BusinessServer.COUNTER:
                        Meters.aii("knock_stat_udp_recv_counter")
                        self._process_increment(item, value)
                    elif cur_type == BusinessServer.GAUGE:
                        Meters.aii("knock_stat_udp_recv_gauge")
                        self._process_gauge(item, value)
                    elif cur_type == BusinessServer.DTC:
                        Meters.aii("knock_stat_udp_recv_dtc")
                        self._process_dtc(item, value)
                    else:
                        Meters.aii("knock_stat_udp_recv_unknown")
                        logger.warn("Unknown item type, item=%s, cur_type=s%, value=%s", item, cur_type, value)
                except Exception as e:
                    logger.warn("Item exception, item=%s, cur_type=s%, value=%s, ex=%s", item, cur_type, value, SolBase.extostr(e))

            # Send back udp
            if self._send_back_udp:
                self.socket.sendto(('Received %s bytes' % len(data)).encode('utf-8'), address)

            # Stats
            Meters.aii("knock_stat_udp_recv")
        except Exception as e:
            # Log
            logger.warn('Cant decode, data_len=%s, data=%s, ex=%s', len(data), repr(data), SolBase.extostr(e))

            # Send back udp
            if self._send_back_udp:
                self.socket.sendto(('KO-NR: Received %s bytes - cant decode' % len(data)).encode('utf-8'), address)

            # Stat
            Meters.aii("knock_stat_udp_recv_ex")
        finally:
            elapsed_ms = SolBase.msdiff(ms_start)
            Meters.dtci("knock_stat_udp_recv_dtc_dtc", elapsed_ms)

    # ------------------------------
    # UTILITIES / STATIC
    # ------------------------------

    @classmethod
    def _clean_value(cls, item, value):
        """
        Clean item and value, returning them
        :param item: item
        :type item: unicode
        :param value: int,float
        :type value:int,float
        :return tuple (item as str, value as float)
        :rtype tuple
        """

        # Float
        value = float(value)

        # Binary
        # TODO Check : item (unicode) to binary (utf8 encoded) ?
        item = SolBase.unicode_to_binary(item)
        return item, value

    @classmethod
    def _dtc_to_dict(cls, dtc):
        """
        To dict
        :param dtc: dtc
        :type dtc: DelayToCount, DelayToCountSafe
        :return: dict
        :rtype dict
        """
        d = OrderedDict()
        # noinspection PyProtectedMember
        ar = dtc._sorted_dict.keys()
        for i in range(0, len(ar) - 1):
            ms1 = ar[i]
            ms2 = ar[i + 1]
            # noinspection PyProtectedMember
            ai = dtc._sorted_dict[ms1]

            # Pad
            ms1 = str(ms1).zfill(5)
            if ms2 == sys.maxint:
                ms2 = "MAX"
            else:
                ms2 = str(ms2).zfill(5)

            out_k = "{0}-{1}".format(ms1, ms2)
            out_v = ai.get()
            d[out_k] = float(out_v)
        return d

    # ------------------------------
    # UTILITIES
    # ------------------------------

    def _process_increment(self, item, value):
        """
        Increment process
        :param item: item
        :type item: unicode
        :param value: value
        :type value: int|float
        """
        item, value = self._clean_value(item, value)

        if item not in self._dict_increment:
            with self._increment_lock:
                if item not in self._dict_increment:
                    self._dict_increment[item] = AtomicFloatSafe()
        self._dict_increment[item].increment(value)

    def _process_gauge(self, item, value):
        """
        Process gauge
        :param item: item
        :type item: unicode
        :param value: value
        :type value: int|float
        """
        item, value = self._clean_value(item, value)
        self._dict_gauge[item] = value

    def _process_dtc(self, item, value):
        """
        Process dtc
        :param item: item
        :type item: unicode
        :param value: value
        :type value: int|float
        """
        item, value = self._clean_value(item, value)
        if item not in self._dict_dtc:
            with self._dtc_lock:
                if item not in self._dict_dtc:
                    self._dict_dtc[item] = DelayToCount(item)
        self._dict_dtc[item].put(value)

    # ------------------------------
    # NOTIFY MANAGEMENT
    # ------------------------------

    def _notify_schedule_next(self):
        """
        Schedule next notify
        """

        with self._notify_lock:
            # Check
            if not self._is_started:
                logger.info("Not started, bypass")
                self._notify_greenlet = None
                return

            # Spawn
            logger.debug("Reschedule, ms=%s", self._notify_interval_ms)
            self._notify_greenlet = gevent.spawn_later(self._notify_interval_ms / 1000.0, self._notify_run)
            logger.debug("Rescheduled ok")

    def _notify_schedule_cancel(self):
        """
        Cancel next schedule
        """
        with self._notify_lock:
            if self._notify_greenlet:
                logger.info("Killing notify greenlet")
                self._notify_greenlet.kill()
                self._notify_greenlet = None
                logger.info("Kill done")

    def _notify_run(self):
        """
        Log and notify
        :return:
        """

        # TODO : Send only _dict item updated since last run

        ms_start = SolBase.mscurrent()
        try:
            # Go in lock to avoid interactions with stop() mainly & reschedule races
            with self._notify_lock:
                logger.info("Entering")
                Meters.aii("knock_stat_udp_notify_run")

                # Dtc
                with self._dtc_lock:
                    if len(self._dict_dtc) > 0:

                        for item, value in self._dict_dtc.iteritems():
                            # Disco
                            self._probe_dtc.notify_discovery_n("k.business.dtc.discovery", {"ITEM": item})

                            # Data
                            d = self._dtc_to_dict(value)
                            for k, v in d.iteritems():
                                # k : 0xxxx-0xxxx
                                logger.debug('item=%s k=%s v=%s', item, k, v)
                                k_dtc = BusinessServer.KNOCK_PREFIX_KEY + "dtc." + k
                                logger.debug('item=%s k_dtc=%s v=%s', item, k_dtc, v)
                                self._probe_dtc.notify_value_n(k_dtc, {"ITEM": item}, v)

                # Increment
                with self._increment_lock:
                    if len(self._dict_increment) > 0:
                        for item, value in self._dict_increment.iteritems():
                            logger.debug('item=%s value=%s', item, value.get())

                            self._probe_inc.notify_discovery_n("k.business.inc.discovery", {"ITEM": item})
                            self._probe_inc.notify_value_n(BusinessServer.KNOCK_PREFIX_KEY + "inc", {"ITEM": item}, value.get())

                # gauge
                with self._gauge_lock:
                    if len(self._dict_gauge) > 0:
                        for item, value in self._dict_gauge.iteritems():
                            logger.debug('item=%s value=%s', item, value)

                            self._probe_inc.notify_discovery_n("k.business.gauge.discovery", {"ITEM": item})
                            self._probe_inc.notify_value_n(BusinessServer.KNOCK_PREFIX_KEY + "gauge", {"ITEM": item}, value)

                # Next schedule (in lock, re-entrant)
                self._notify_schedule_next()
        except Exception as e:
            logger.warn("Internal ex=%s", SolBase.extostr(e))
            Meters.aii("knock_stat_udp_notify_run_ex")
        finally:
            elapsed_ms = SolBase.msdiff(ms_start)
            logger.info("Exiting, ms=%s", elapsed_ms)
            Meters.dtci("knock_stat_udp_notify_run_dtc", elapsed_ms)
