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
import os
import shutil
import unittest
from os.path import dirname, abspath

import redis
from nose.plugins.attrib import attr
from pythonsol.FileUtility import FileUtility
from pythonsol.SolBase import SolBase
from pythonsol.meter.MeterManager import MeterManager

from knockdaemon.Core.KnockManager import KnockManager
from knockdaemon.Core.KnockStat import KnockStat
from knockdaemon.HttpMock.HttpMock import HttpMock
from knockdaemon.Platform.PTools import PTools
from knockdaemon.Transport.HttpAsyncTransport import HttpAsyncTransport

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


@attr('prov')
class TestRealAllUsingHttpMock(unittest.TestCase):
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
            self.current_dir + "conf" + SolBase.get_pathseparator() + "realall" \
            + SolBase.get_pathseparator() + "knockdaemon.ini"        
        self.k = None

        # Config files
        for f in [
            "k.CheckProcess.json",
            "k.CheckDns.json",
            "knockdaemon.ini",
            SolBase.get_pathseparator().join(["conf.d", "10_auth.ini"])
        ]:
            src = self.current_dir + "conf" + SolBase.get_pathseparator() + "realall" + SolBase.get_pathseparator() + f
            dst = PTools.get_tmp_dir() + SolBase.get_pathseparator() + f

            dir_name = dirname(dst)
            if not FileUtility.is_dir_exist(dir_name):
                os.makedirs(dir_name)
            shutil.copyfile(src, dst)

            # Load
            buf = FileUtility.file_to_textbuffer(dst, "utf8")

            # Replace
            buf = buf.replace("/tmp", PTools.get_tmp_dir())

            # Write
            FileUtility.append_text_tofile(dst, buf, "utf8", overwrite=True)

        # Overwrite
        self.manager_config_file = PTools.get_tmp_dir() + SolBase.get_pathseparator() + "knockdaemon.ini"

        # Reset meter
        MeterManager._hash_meter = dict()

        # Debug stat on exit ?
        self.debug_stat = False

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

        # If windows, perform a WMI initial refresh to get datas
        if PTools.get_distribution_type() == "windows":
            from knockdaemon.Windows.Wmi.Wmi import Wmi
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
            ks = MeterManager.get(KnockStat)
            for k, v in ks.to_dict().iteritems():
                logger.info("stat, %s => %s", k, v)

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

        # MeterManager._hash_meter = dict()
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

        # Do NOT Start
        pass

    def test_real_all(self):
        """
        Test
        """

        # Start
        self._start_all()

        # Execute everything once
        self.k.exec_all()

        # Wait for 2 exec at least + 2 transport ok at least + margin
        logger.info("*** WAIT")
        timeout_ms = 5000
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < timeout_ms:
            # Transport
            if MeterManager.get(KnockStat).transport_ok_count.get() >= 1 \
                    and not self.k.get_transport_by_type(HttpAsyncTransport)._http_pending and len(self.k._superv_notify_value_list) == 0:
                break

            SolBase.sleep(50)

        # Wait a bit
        SolBase.sleep(500)

        # Check
        logger.info("*** CHECK")
        for p in self.k._probe_list:
            logger.debug("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreater(c.initial_ms_start, 0)

        # Validate k.business.dtc.discovery
        logger.info("*** VALIDATE")
        ks = MeterManager.get(KnockStat)
        self.assertEqual(ks.exec_probe_exception.get(), 0)
        self.assertEqual(ks.exec_probe_bypass.get(), 0)

        self.assertEqual(ks.exec_all_inner_exception.get(), 0)
        self.assertEqual(ks.exec_all_outer_exception.get(), 0)
        self.assertEqual(ks.exec_all_finally_exception.get(), 0)
        self.assertGreaterEqual(ks.exec_all_count.get(), 0)
        self.assertEqual(ks.exec_all_too_slow.get(), 0)

        # Validate discovery (must be empty since notified)
        self.assertEqual(len(self.k._superv_notify_disco_hash), 0)
        # Validate values (must be empty since notified)
        self.assertEqual(len(self.k._superv_notify_value_list), 0, self.k._superv_notify_value_list)

        # Validate to superv (critical)
        self.assertGreater(ks.transport_spv_processed.get(), 0)
        self.assertGreater(ks.transport_spv_total.get(), 0)

        # Over
        self._stop_all()
