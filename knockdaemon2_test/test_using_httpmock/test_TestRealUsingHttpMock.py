"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac
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
import unittest

import os
import redis
# noinspection PyUnresolvedReferences,PyPackageRequirements
from nose.plugins.attrib import attr
from os.path import dirname, abspath
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.HttpMock.HttpMock import HttpMock
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Transport.HttpAsyncTransport import HttpAsyncTransport

logger = logging.getLogger(__name__)
SolBase.voodoo_init()


@attr('prov')
class TestRealUsingHttpMock(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.manager_config_file = \
            self.current_dir + "conf" + SolBase.get_pathseparator() + "real" \
            + SolBase.get_pathseparator() + "knockdaemon2.ini"
        self.k = None

        # Reset meter
        Meters.reset()

        # Debug stat on exit ?
        self.debug_stat = False

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

        # If windows, perform a WMI initial refresh to get datas
        if PTools.get_distribution_type() == "windows":
            from knockdaemon2.Windows.Wmi.Wmi import Wmi
            Wmi._wmi_fetch_all()
            Wmi._flush_props(Wmi._WMI_DICT, Wmi._WMI_DICT_PROPS)

    def tearDown(self):
        """
        Setup (called after each test)
        """
        if self.k:
            logger.warn("k set, stopping, not normal")
            self.k.stop()
            self.k = None

        if self.h:
            logger.warn("h set, stopping, not normal")
            self.h.stop()
            self.h = None

        if self.debug_stat:
            Meters.write_to_logger()

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

    def _start_all(self):
        """
        Test
        """

        # Meters.reset()
        self._start_http_mock()
        self._start_manager()

    def _start_http_mock(self):
        """
        Test
        """
        self.h = HttpMock()

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

    def _start_manager(self):
        """
        Test
        """

        # Init manager
        self.k = KnockManager(self.manager_config_file)
        self.k.get_transport_by_type(HttpAsyncTransport)._http_send_min_interval_ms = 5000

        # Start
        self.k.start()

    def test_real(self):
        """
        Test
        """

        # Start
        self._start_all()

        # Wait for 2 exec at least + 2 transport ok at least
        timeout_ms = 60000
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < timeout_ms:
            # Transport
            if Meters.aig("knock_stat_transport_ok_count") >= 2 \
                    and not self.k.get_transport_by_type(HttpAsyncTransport)._http_pending:
                break

            SolBase.sleep(50)

        # Stop
        self.k.stop()

        # Check
        for p in self.k._probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreater(c.initial_ms_start, 0)

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 2)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Validate discovery (must be empty since notified)
        self.assertEqual(len(self.k._superv_notify_disco_hash), 0)
        # Validate values (must be empty since notified)
        self.assertEqual(len(self.k._superv_notify_value_list), 0)

        # Validate to superv (critical)
        self.assertGreater(Meters.aig("knock_stat_transport_spv_processed"), 0)
        self.assertGreater(Meters.aig("knock_stat_transport_spv_total"), 0)

        self.k = None

        # Over
        self._stop_all()
