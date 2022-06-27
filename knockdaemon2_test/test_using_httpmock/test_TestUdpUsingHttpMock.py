"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2022 Laurent Labatut / Laurent Champagnac
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

from pysolbase.SolBase import SolBase

SolBase.voodoo_init()

import logging
import os
import unittest
from os.path import dirname, abspath

import gevent
import redis
import ujson
from gevent.event import Event
from pysolmeters.AtomicInt import AtomicInt
from pysolmeters.Meters import Meters

from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.Core.UDPBusinessServerBase import UDPBusinessServerBase
from knockdaemon2.Core.UDPServer import UDPServer
from knockdaemon2.HttpMock.HttpMock import HttpMock
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Tests.TestHelpers import expect_value
from knockdaemon2.Transport.InfluxAsyncTransport import InfluxAsyncTransport
from knockdaemon2_test.ForTest.UdpClient import UdpClient

logger = logging.getLogger(__name__)


class TestUdpUsingHttpMock(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        SolBase.voodoo_init()

        # Awful hack for tests (we may have a knockdaemon2 running on the machine we are running test)
        UDPServer.UDP_SOCKET_NAME = UDPServer.UDP_UNITTEST_SOCKET_NAME

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.manager_config_file = self.current_dir + "conf" + SolBase.get_pathseparator() + "protocol" + SolBase.get_pathseparator() + "knockdaemon2.yaml"
        self.k = None

        # Reset meter
        Meters.reset()

        # Debug stat on exit ?
        self.debug_stat = False

        self.k = None
        self.h = None
        self.b_buf_list = None

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

        # Bench stats
        self.bench_gauge = AtomicInt()
        self.bench_dtc = AtomicInt()
        self.bench_counter = AtomicInt()
        self.bench_ex = AtomicInt()

    def tearDown(self):
        """
        Setup (called after each test)
        """

        # Reset
        if self.k:
            logger.debug("k set, stopping, not normal")
            self.k.stop()
            self.k = None

        if self.h:
            logger.debug("h set, stopping, not normal")
            self.h.stop()
            self.h = None

        if self.debug_stat:
            Meters.write_to_logger()

        self._kick_host()

    # noinspection PyMethodMayBeStatic
    def _udp_client_connect_helper(self, uc):
        """
        Connect helper
        :param uc: UdpClient
        :type uc: UdpClient
        """

        # Use domain
        uc.connect(UDPServer.UDP_UNITTEST_SOCKET_NAME)

    def _kick_host(self):
        """
        This id dirty
        """

        # Start service
        self._start_http_mock()

        # Stop
        self.h.stop()
        self.h = None

    def _stop_all(self):
        """
        Test
        """

        if self.h:
            self.h.stop()
            self.h = None

        if self.k:
            self.k.stop()
            self.k = None

    def _start_all(self, start_manager=True):
        """
        Test
        :param start_manager: Test
        """

        # Meters.reset()
        self._start_http_mock()
        self._start_manager(start_manager)

    def _start_http_mock(self):
        """
        Test
        """
        self.h = HttpMock()

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

    def _start_manager(self, start_manager):
        """
        Test
        :param start_manager: bool
        """

        # Init manager
        self.k = KnockManager(self.manager_config_file, auto_start=start_manager)
        # noinspection PyBroadException
        try:
            self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_send_min_interval_ms = 5000
        except Exception:
            pass

        # Keep only one item (easier to test)
        self.k.probe_list.pop()

        # Override
        for p in self.k.probe_list:
            p.exec_interval_ms = 1000

        # Start
        if start_manager:
            self.k.start()

    def test_udp_start_stop_manual(self):
        """
        Test
        """

        logger.info("*** GO")

        self._start_all(start_manager=False)

        for _ in range(0, 5):
            # Reset meter
            Meters.reset()

            # Alloc
            logger.info("*** ALLOC")
            u = UDPServer(self.k, notify_interval_ms=1000)
            self.assertFalse(u._is_started)
            self.assertIsNotNone(u._manager)
            self.assertIsNone(u._business_server_domain_linux)

            # Start
            logger.info("*** START")
            u.start()
            self.assertTrue(u._is_started)
            self.assertIsNotNone(u._manager)
            self.assertIsNotNone(u._business_server_domain_linux)
            self.assertTrue(u._business_server_domain_linux._is_started)
            self.assertIsNotNone(u._business_server_domain_linux._manager)

            # Wait for start completion
            logger.info("*** WAIT")
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < 5000:
                if u._business_server_domain_linux.started:
                    break
                SolBase.sleep(100)
            self.assertTrue(u._business_server_domain_linux.started)
            self.assertIsNotNone(u._business_server_domain_linux._notify_greenlet)
            elapsed_ms = SolBase.msdiff(ms_start)

            # We have the 2 listener (domain and ip) now running : *2 on all meters.

            # Wait for at least ONE notify schedule (1000 ms) and check
            logger.info("*** SCHEDULE")
            SolBase.sleep(1250 - elapsed_ms)
            self.assertEqual(Meters.aig("knock_stat_udp_notify_run"), 1 * 2)
            self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

            # Wait for a second ONE (ie check reschedule)
            logger.info("*** SCHEDULE")
            SolBase.sleep(1250)
            self.assertEqual(Meters.aig("knock_stat_udp_notify_run"), 2 * 2)
            self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

            # Stop
            logger.info("*** STOP")
            u.stop()
            self.assertFalse(u._is_started)
            self.assertIsNone(u._business_server_domain_linux)

            # Re-check (schedule stopped)
            SolBase.sleep(1250)
            self.assertEqual(Meters.aig("knock_stat_udp_notify_run"), 2 * 2)
            self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

            logger.info("*** LOOP OVER")

        # OVER
        self._stop_all()

    def test_udp_start_stop_daemon(self):
        """
        Test
        """

        logger.info("*** GO")

        # We auto start udp daemon (which is started via manager)
        self._start_all(start_manager=True)

        # Check
        self.assertTrue(self.k._udp_server._is_started)
        self.assertIsNotNone(self.k._udp_server._manager)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux)
        self.assertTrue(self.k._udp_server._business_server_domain_linux._is_started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._manager)

        # Wait for start completion
        logger.info("*** WAIT")
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 5000:
            if self.k._udp_server._business_server_domain_linux.started:
                break
            SolBase.sleep(100)
        self.assertTrue(self.k._udp_server._business_server_domain_linux.started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._notify_greenlet)
        elapsed_ms = SolBase.msdiff(ms_start)

        # We have the 2 listener (domain and ip) now running : *2 on all meters.

        # Wait for at least ONE notify schedule (5000 ms default) and check
        logger.info("*** SCHEDULE")
        SolBase.sleep(5250 - elapsed_ms)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run"), 1 * 2)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

        # Wait for a second ONE (ie check reschedule)
        logger.info("*** SCHEDULE")
        SolBase.sleep(5250)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run"), 2 * 2)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

        # Stop
        logger.info("*** STOP MANAGER")
        self.k.stop()
        self.assertIsNone(self.k._udp_server)

        # Re-check (schedule stopped)
        SolBase.sleep(5250)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run"), 2 * 2)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

        # OVER
        self._stop_all()

    def test_udp_basic_send_simple(self):
        """
        Test
        """

        logger.info("*** GO")

        # We do NOT autostart (we do not want the transport to be started)
        self._start_all(start_manager=False)

        # Start udp server
        self.k._udp_server.start()

        # Check
        self.assertTrue(self.k._udp_server._is_started)
        self.assertIsNotNone(self.k._udp_server._manager)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux)
        self.assertTrue(self.k._udp_server._business_server_domain_linux._is_started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._manager)

        # Wait for start completion
        logger.info("*** WAIT")
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 5000:
            if self.k._udp_server._business_server_domain_linux.started:
                break
            SolBase.sleep(100)
        self.assertTrue(self.k._udp_server._business_server_domain_linux.started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._notify_greenlet)

        # ----------------------
        # OK, SEND
        # ----------------------

        udp_client = UdpClient()
        self._udp_client_connect_helper(udp_client)

        json_list = [
            # Counter
            ["counter1", UDPBusinessServerBase.COUNTER, 2.2],
            # Gauge
            ["gauge1", UDPBusinessServerBase.GAUGE, 3.3],
            # Dtc
            ["dtc1", UDPBusinessServerBase.DTC, 1]
        ]

        udp_client.send_json(json_list)

        udp_client.disconnect()

        # ----------------------
        # Wait for recv
        # ----------------------
        logger.info("*** WAIT RECV")
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 2500:
            # Check
            if (
                    Meters.aig("knock_stat_udp_recv") >= 1 and
                    Meters.aig("knock_stat_udp_recv_counter") == 1 and
                    Meters.aig("knock_stat_udp_recv_gauge") == 1 and
                    Meters.aig("knock_stat_udp_recv_dtc") == 1
            ):
                # Ok
                break

            # Wait
            SolBase.sleep(100)

        # Check
        self.assertGreaterEqual(Meters.aig("knock_stat_udp_recv"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_counter"), 1)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_gauge"), 1)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_dtc"), 1)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_unknown"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_ex"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_v2"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_tu_ex"), 0)

        # ----------------------
        # Wait for at least one UDP notify here
        # ----------------------

        logger.info("*** WAIT NOTIFY")

        target = Meters.aig("knock_stat_udp_notify_run") + 2

        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 11000:
            # Check
            if Meters.aig("knock_stat_udp_notify_run") >= target:
                break

            # Wait
            SolBase.sleep(100)

        # Check
        self.assertGreaterEqual(Meters.aig("knock_stat_udp_notify_run"), target)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

        # ----------------------
        # Check transport stuff
        # ----------------------
        logger.info("*** CHECK NOTIFY")

        logger.info("ZZZ=%s", self.k.superv_notify_value_list)

        # counter
        dd = {"ITEM": "counter1"}
        expect_value(self, self.k, "k.business.inc", 2.2, "eq", dd, cast_to_float=True)

        # gauge
        dd = {"ITEM": "gauge1"}
        expect_value(self, self.k, "k.business.gauge", 3.3, "eq", dd, cast_to_float=True)

        # dtc
        dd = {"ITEM": "dtc1"}
        expect_value(self, self.k, "k.business.dtc.00000-00050", 1.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.00050-00100", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.00100-00500", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.00500-01000", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.01000-02500", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.02500-05000", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.05000-10000", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.10000-30000", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.30000-60000", 0.0, "eq", dd, cast_to_float=True)
        expect_value(self, self.k, "k.business.dtc.60000-MAX", 0.0, "eq", dd, cast_to_float=True)

        # ----------------------
        # SEND OVER
        # ----------------------

        # Stop
        logger.info("*** STOP MANAGER")
        self.k.stop()
        self.assertIsNone(self.k._udp_server)

        # OVER
        self._stop_all()

    def test_udp_basic_send_simple_protocol_v2(self):
        """
        Test
        """

        logger.info("*** GO")

        # We do NOT autostart (we do not want the transport to be started)
        self._start_all(start_manager=False)

        # Start udp server
        self.k._udp_server.start()

        # Check
        self.assertTrue(self.k._udp_server._is_started)
        self.assertIsNotNone(self.k._udp_server._manager)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux)
        self.assertTrue(self.k._udp_server._business_server_domain_linux._is_started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._manager)

        # Wait for start completion
        logger.info("*** WAIT")
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 5000:
            if self.k._udp_server._business_server_domain_linux.started:
                break
            SolBase.sleep(100)
        self.assertTrue(self.k._udp_server._business_server_domain_linux.started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._notify_greenlet)

        # ----------------------
        # OK, SEND
        # ----------------------

        udp_client = UdpClient()
        self._udp_client_connect_helper(udp_client)

        json_list = [
            ["meters_v2_1", {"TAG1": "tag11", "TAG2": "tag21"}, 1.99, None, {"OPTTAG1": "opttag1"}],
            ["meters_v2_2", {"TAG1": "tag12", "TAG2": "tag22"}, 2.99, None, {"OPTTAG1": "opttag2"}],
        ]

        udp_client.send_json(json_list)

        udp_client.disconnect()

        # ----------------------
        # Wait for recv
        # ----------------------
        logger.info("*** WAIT RECV")
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 2500:
            # Check
            if Meters.aig("knock_stat_udp_recv_v2") >= 2:
                # Ok
                break

            # Wait
            SolBase.sleep(100)

        # Check
        self.assertGreaterEqual(Meters.aig("knock_stat_udp_recv"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_counter"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_gauge"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_dtc"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_unknown"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_ex"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_v2"), 2)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_tu_ex"), 0)

        # ----------------------
        # We dont need to wait for notify, since we flush directly to manager when in protocol v2 mode
        # ----------------------

        logger.info("*** WAIT NOTIFY : USELESS FOR UDP V2")

        # ----------------------
        # Check transport stuff
        # ----------------------
        logger.info("*** CHECK NOTIFY")

        logger.info("ZZZ=%s", self.k.superv_notify_value_list)

        # check 1
        dd = {"TAG1": "tag11", "TAG2": "tag21"}
        expect_value(self, self.k, "meters_v2_1", 1.99, "eq", dd, cast_to_float=True)

        # check 2
        dd = {"TAG1": "tag12", "TAG2": "tag22"}
        expect_value(self, self.k, "meters_v2_2", 2.99, "eq", dd, cast_to_float=True)

        # ----------------------
        # SEND OVER
        # ----------------------

        # Stop
        logger.info("*** STOP MANAGER")
        self.k.stop()
        self.assertIsNone(self.k._udp_server)

        # OVER
        self._stop_all()

    def _send_callback(self, b_buf):
        """
        Send callback
        :param b_buf: bytes
        :type b_buf: bytes
        """

        self.b_buf_list.append(b_buf)

    def test_udp_chunking(self):
        """
        Test
        """

        logger.info("*** GO")

        for udp_chunk in [1024, 2000, 4096, 8192, 16384, 32768, 65536]:
            ar = [2, 100, 1000, 10000, 100000]
            if PTools.is_cpu_arm():
                # For arm, we lower this
                ar = [2, 100, 1000]
                logger.info("ARM ON, lowering ar=%s", ar)

            for item_count in ar:
                # Reset
                self.b_buf_list = list()

                # Build data list
                data_list = list()
                for cur_id in range(0, item_count):
                    data_list.append(["counter" + str(cur_id), "C", cur_id])
                    data_list.append(["gauge" + str(cur_id), "G", cur_id])
                    data_list.append(["dtc" + str(cur_id), "DTC", cur_id])

                # Alloc
                u = UdpClient(max_udp_size=udp_chunk)

                # Send
                ms = SolBase.mscurrent()
                u._send_json(data_list, self._send_callback)
                ms_elapsed = SolBase.msdiff(ms)

                # Log
                if ms_elapsed > 0.0:
                    per_sec_item = float(len(data_list)) / float(ms_elapsed / 1000.0)
                    per_sec_chunk = float(len(self.b_buf_list)) / float(ms_elapsed / 1000.0)
                else:
                    per_sec_item = 0.0
                    per_sec_chunk = 0.0
                logger.info("len=%s/%s, udp_chunk=%s, ps=%.2f/%.2f", len(data_list), len(self.b_buf_list), udp_chunk, per_sec_item, per_sec_chunk)

                # Check the stuff
                total_item_count = 0
                for cur_b_buf in self.b_buf_list:
                    self.assertLessEqual(len(cur_b_buf), udp_chunk, "chunk=" + str(udp_chunk))
                    temp_list = ujson.loads(cur_b_buf)
                    total_item_count += len(temp_list)
                self.assertEqual(len(data_list), total_item_count)

    def test_udp_chunking_and_recv(self):
        """
        Test
        """

        logger.info("*** GO")

        # CANNOT USE MORE THAN 8192 UDP CHUNK SIZE BY DEFAULT.... BaseServer is hacked, we can raise it
        for udp_chunk in [1024, 4096, 8192, 16384, 61440]:
            max_count = 20000
            if PTools.is_cpu_arm():
                # For arm, we lower this
                logger.info("ARM ON, lowering max_count=200")
                max_count = 200

            for item_count in [max_count]:
                # Reset counters
                Meters.reset()

                # We do NOT autostart (we do not want the transport to be started)
                self._start_all(start_manager=True)

                # Build data list
                data_list = list()
                for cur_id in range(0, item_count):
                    data_list.append(["counter" + str(cur_id), "C", cur_id])
                    data_list.append(["gauge" + str(cur_id), "G", cur_id])
                    data_list.append(["dtc" + str(cur_id), "DTC", cur_id])

                # Alloc
                u = UdpClient(max_udp_size=udp_chunk)

                # Connect
                self._udp_client_connect_helper(u)

                # Send (real)
                ms = SolBase.mscurrent()
                u.send_json(data_list)
                ms_elapsed = SolBase.msdiff(ms)

                # Disconnect
                u.disconnect()

                # Log
                if ms_elapsed > 0:
                    per_sec_item = float(len(data_list)) / float(ms_elapsed / 1000.0)
                else:
                    per_sec_item = 0
                logger.info("len=%s, udp_chunk=%s, ps=%.2f", len(data_list), udp_chunk, per_sec_item)

                # Wait for completion
                logger.info("*** WAIT FOR COMPLETION")
                ms_start2 = SolBase.mscurrent()
                while SolBase.msdiff(ms_start2) < 20000:
                    ok = True
                    if Meters.aig("knock_stat_udp_recv_counter") != item_count:
                        ok = False
                    if Meters.aig("knock_stat_udp_recv_gauge") != item_count:
                        ok = False
                    if Meters.aig("knock_stat_udp_recv_dtc") != item_count:
                        ok = False
                    if ok:
                        logger.info("Completion ok")
                        break
                    else:
                        logger.info(
                            "Waiting...,  recv=%s:%s/%s/%s, ex=%s/%s, notif=%s/%s",
                            Meters.aig("knock_stat_udp_recv"),
                            Meters.aig("knock_stat_udp_recv_counter"),
                            Meters.aig("knock_stat_udp_recv_gauge"),
                            Meters.aig("knock_stat_udp_recv_dtc"),
                            Meters.aig("knock_stat_udp_recv_unknown"),
                            Meters.aig("knock_stat_udp_recv_ex"),
                            Meters.aig("knock_stat_udp_notify_run"),
                            Meters.aig("knock_stat_udp_notify_run_ex"),
                        )
                        SolBase.sleep(1000)

                # Check
                self.assertGreaterEqual(Meters.aig("knock_stat_udp_recv"), 0)
                self.assertEqual(Meters.aig("knock_stat_udp_recv_counter"), item_count, "udp_chunk=" + str(udp_chunk))
                self.assertEqual(Meters.aig("knock_stat_udp_recv_gauge"), item_count, "udp_chunk=" + str(udp_chunk))
                self.assertEqual(Meters.aig("knock_stat_udp_recv_dtc"), item_count, "udp_chunk=" + str(udp_chunk))
                self.assertEqual(Meters.aig("knock_stat_udp_recv_unknown"), 0, "udp_chunk=" + str(udp_chunk))
                self.assertEqual(Meters.aig("knock_stat_udp_recv_ex"), 0, "udp_chunk=" + str(udp_chunk))
                self.assertEqual(self.bench_ex.get(), 0, "udp_chunk=" + str(udp_chunk))

                # Stop
                logger.info("*** STOP MANAGER")
                self.k.stop()
                self.assertIsNone(self.k._udp_server)

                # OVER
                self._stop_all()

    def test_udp_basic_send_bench(self):
        """
        Test
        """

        logger.info("*** GO")

        # Greenlet count
        greenlet_count = 64

        # We do NOT autostart (we do not want the transport to be started)
        self._start_all(start_manager=True)

        # Check
        self.assertTrue(self.k._udp_server._is_started)
        self.assertIsNotNone(self.k._udp_server._manager)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux)
        self.assertTrue(self.k._udp_server._business_server_domain_linux._is_started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._manager)

        # Wait for start completion
        logger.info("*** WAIT")
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 5000:
            if self.k._udp_server._business_server_domain_linux.started:
                break
            SolBase.sleep(100)
        self.assertTrue(self.k._udp_server._business_server_domain_linux.started)
        self.assertIsNotNone(self.k._udp_server._business_server_domain_linux._notify_greenlet)

        # ----------------------
        # OK, SEND
        # ----------------------

        ms_duration = 10000
        run_event = Event()

        # Start
        logger.info("*** SPAWN")
        ar_g = list()
        for _ in range(0, greenlet_count):
            ar_g.append(gevent.spawn(self._run_bench, run_event))
            SolBase.sleep(0)

        # Run
        logger.info("*** RUNNING")
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < ms_duration:
            logger.info("Running..., send=%s/%s/%s, ex=%s, recv=%s:%s/%s/%s, ex=%s/%s, notif=%s/%s",
                        self.bench_counter.get(), self.bench_gauge.get(), self.bench_dtc.get(), self.bench_ex.get(),
                        Meters.aig("knock_stat_udp_recv"),
                        Meters.aig("knock_stat_udp_recv_counter"),
                        Meters.aig("knock_stat_udp_recv_gauge"),
                        Meters.aig("knock_stat_udp_recv_dtc"),
                        Meters.aig("knock_stat_udp_recv_unknown"),
                        Meters.aig("knock_stat_udp_recv_ex"),
                        Meters.aig("knock_stat_udp_notify_run"),
                        Meters.aig("knock_stat_udp_notify_run_ex"),
                        )
            self.assertEqual(self.bench_ex.get(), 0)
            SolBase.sleep(1000)

        ms_elapsed = SolBase.msdiff(ms_start)
        per_sec_send = float(self.bench_counter.get() + self.bench_gauge.get() + self.bench_dtc.get()) / float(ms_elapsed / 1000.0)

        # Signal
        run_event.set()

        # Wait for completion
        logger.info("*** WAIT FOR COMPLETION")
        ms_start2 = SolBase.mscurrent()
        while SolBase.msdiff(ms_start2) < ms_duration:
            ok = True
            if Meters.aig("knock_stat_udp_recv_counter") != self.bench_counter.get():
                ok = False
            if Meters.aig("knock_stat_udp_recv_gauge") != self.bench_gauge.get():
                ok = False
            if Meters.aig("knock_stat_udp_recv_dtc") != self.bench_dtc.get():
                ok = False
            if ok:
                logger.info("Completion ok")
                break
            else:
                logger.info(
                    "Waiting..., send=%s/%s/%s, ex=%s, recv=%s:%s/%s/%s, ex=%s/%s, notif=%s/%s",
                    self.bench_counter.get(), self.bench_gauge.get(), self.bench_dtc.get(), self.bench_ex.get(),
                    Meters.aig("knock_stat_udp_recv"),
                    Meters.aig("knock_stat_udp_recv_counter"),
                    Meters.aig("knock_stat_udp_recv_gauge"),
                    Meters.aig("knock_stat_udp_recv_dtc"),
                    Meters.aig("knock_stat_udp_recv_unknown"),
                    Meters.aig("knock_stat_udp_recv_ex"),
                    Meters.aig("knock_stat_udp_notify_run"),
                    Meters.aig("knock_stat_udp_notify_run_ex"),
                )
                SolBase.sleep(1000)

        # Check
        self.assertGreaterEqual(Meters.aig("knock_stat_udp_recv"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_counter"), self.bench_counter.get())
        self.assertEqual(Meters.aig("knock_stat_udp_recv_gauge"), self.bench_gauge.get())
        self.assertEqual(Meters.aig("knock_stat_udp_recv_dtc"), self.bench_dtc.get())
        self.assertEqual(Meters.aig("knock_stat_udp_recv_unknown"), 0)
        self.assertEqual(Meters.aig("knock_stat_udp_recv_ex"), 0)
        self.assertEqual(self.bench_ex.get(), 0)

        per_sec_recv = float(Meters.aig("knock_stat_udp_recv_counter") +
                             Meters.aig("knock_stat_udp_recv_gauge") +
                             Meters.aig("knock_stat_udp_recv_dtc")) / float(ms_elapsed / 1000.0)

        logger.info("*** PERSEC send=%.2f, recv=%.2f", per_sec_send, per_sec_recv)

        # ----------------------
        # Wait for at least one UDP notify here
        # ----------------------

        logger.info("*** WAIT NOTIFY")

        target = Meters.aig("knock_stat_udp_notify_run") + 2

        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < 11000:
            # Check
            if Meters.aig("knock_stat_udp_notify_run") >= target:
                break

            # Wait
            SolBase.sleep(100)

        # Check
        self.assertGreaterEqual(Meters.aig("knock_stat_udp_notify_run"), target)
        self.assertEqual(Meters.aig("knock_stat_udp_notify_run_ex"), 0)

        # ----------------------
        # SEND OVER
        # ----------------------

        # Stop
        logger.info("*** STOP MANAGER")
        self.k.stop()
        self.assertIsNone(self.k._udp_server)

        # OVER
        self._stop_all()

    def _run_bench(self, run_event):
        """
        Run
        :param run_event: Event
        :type run_event: Event
        """
        udp_client = UdpClient()
        try:
            # Connect
            self._udp_client_connect_helper(udp_client)

            while not run_event.is_set():
                json_list = [
                    # Counter
                    ["counter1", UDPBusinessServerBase.COUNTER, 2.2],
                    # Gauge
                    ["gauge1", UDPBusinessServerBase.GAUGE, 3.3],
                    # Dtc
                    ["dtc1", UDPBusinessServerBase.DTC, 1]
                ]

                SolBase.sleep(0)
                udp_client.send_json(json_list)
                SolBase.sleep(0)

                self.bench_counter.increment()
                self.bench_gauge.increment()
                self.bench_dtc.increment()

                # Keep some room for server
                SolBase.sleep(0)
        except Exception as e:
            logger.warning("Fatal ex=%s", SolBase.extostr(e))
            self.bench_ex.increment()
        finally:
            logger.info("Exiting")
            udp_client.disconnect()
