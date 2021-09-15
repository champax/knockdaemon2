"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2021 Laurent Labatut / Laurent Champagnac
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
import os
import unittest
from os.path import dirname, abspath

import redis
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.HttpMock.HttpMock import HttpMock
from knockdaemon2.Transport.InfluxAsyncTransport import InfluxAsyncTransport

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class TestProtocolUsingHttpMock(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        SolBase.voodoo_init()

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

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

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
        self.k = KnockManager(self.manager_config_file)
        self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_send_min_interval_ms = 5000

        # Meters prefix, first transport
        self.ft_meters_prefix = self.k.get_first_meters_prefix_by_type(InfluxAsyncTransport)

        # Keep only one item (easier to test)
        self.k.probe_list.pop()

        # Override
        for p in self.k.probe_list:
            p.exec_interval_ms = 1000

        # Start
        if start_manager:
            self.k.start()

    def test_protocol_basic(self):
        """
        Test
        """

        # Start
        self._start_all()

        # Wait for 2 exec at least + 2 transport ok at least
        timeout_ms = 60000
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < timeout_ms:
            ok = True

            # Probes
            for p in self.k.probe_list:
                if p.exec_count < 2:
                    ok = False

            # Transport
            if Meters.aig(self.ft_meters_prefix + "knock_stat_transport_ok_count") < 2:
                ok = False

            # Check
            if ok:
                break
            else:
                SolBase.sleep(50)

        # Stop
        self.k.stop()

        # Check
        for p in self.k.probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreaterEqual(p.exec_count, 2)
            self.assertGreater(c.initial_ms_start, 0)

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 2)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Validate values (must be empty since notified)
        self.assertEqual(len(self.k.superv_notify_value_list), 0)

        # Check transport
        self.assertGreaterEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_call_count"), 1)
        self.assertGreaterEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_ok_count"), 1)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_exception_count"), 0)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_failed_count"), 0)

        # Over
        self._stop_all()

    def test_protocol_basic_paranoid(self):
        """
        Test
        """

        # Start
        self._start_all()
        self.h._paranoid_enabled = True

        # Wait for 2 exec at least + 2 transport ok at least
        timeout_ms = 60000
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < timeout_ms:
            ok = True

            # Probes
            for p in self.k.probe_list:
                if p.exec_count < 2:
                    ok = False

            # Transport
            if Meters.aig(self.ft_meters_prefix + "knock_stat_transport_ok_count") < 2:
                ok = False

            # Check
            if ok:
                break
            else:
                SolBase.sleep(50)

        # Stop
        self.k.stop()

        # Check
        for p in self.k.probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreaterEqual(p.exec_count, 2)
            self.assertGreater(c.initial_ms_start, 0)

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 2)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Validate values (must be empty since notified)
        self.assertEqual(len(self.k.superv_notify_value_list), 0)

        # Check transport
        self.assertGreaterEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_call_count"), 1)
        self.assertGreaterEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_ok_count"), 1)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_exception_count"), 0)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_failed_count"), 0)

        # Over
        self._stop_all()
