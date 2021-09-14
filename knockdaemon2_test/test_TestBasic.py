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
import random
import unittest
from os.path import dirname, abspath

import redis
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Tests.TestHelpers import expect_disco
from knockdaemon2.Tests.TestHelpers import expect_value
from knockdaemon2_test.ForTest.TestTransport import TestTransport

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class TestBasic(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.config_file = self.current_dir + "conf" + SolBase.get_pathseparator() + "basic" + SolBase.get_pathseparator() + "knockdaemon2.yaml"
        self.k = None

        # Reset meter
        Meters.reset()

        # Debug stat on exit ?
        self.debug_stat = False

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

        # Invoke timeout
        self.invoke_timeout = 10000
        if PTools.is_cpu_arm():
            self.invoke_timeout = 60000
            logger.info("ARM ON, raising invoke timeout=%s", self.invoke_timeout)

    def tearDown(self):
        """
        Setup (called after each test)
        """
        if self.k:
            logger.warning("k set, stopping, not normal")
            self.k.stop()
            self.k = None

        if self.debug_stat:
            Meters.write_to_logger()

    def test_load_config(self):
        """
        Test
        """

        self.k = KnockManager(self.config_file)

        self.assertIsNotNone(self.k)
        self.assertEqual(self.k._exectimeout_ms, 1000)
        self.assertIsNotNone(self.k._ar_knock_transport)
        self.assertEqual(len(self.k._ar_knock_transport), 1)
        self.assertEqual(len(self.k._probe_list), 2)
        for p in self.k._probe_list:
            if p.key == "TestProbe1":
                self.assertEqual(p.custom_key_b, "customValueB_1")
                self.assertEqual(p.exec_count, 0)
                self.assertEqual(p.exec_enabled, True)
                self.assertEqual(p.exec_interval_ms, 1000)
            elif p.key == "TestProbe2":
                self.assertEqual(p.custom_key_b, "customValueB_2")
                self.assertEqual(p.exec_count, 0)
                self.assertEqual(p.exec_enabled, True)
                self.assertEqual(p.exec_interval_ms, 1000)
            else:
                self.fail("Invalid key=" + p.key)
        self.assertFalse(self.k._is_running)

    # ==========================
    # START/STOP
    # ==========================

    def _start_stop_internal(self, loop_count):
        """
        Test
        :param loop_count: test
        """

        for _ in range(0, loop_count):
            self._start_stop_internal_go()

    def _start_stop_internal_go(self):
        """
        Test
        """
        self.k = KnockManager(self.config_file)

        # Start
        self.k.start()

        # Stop
        self.k.stop()
        self.assertFalse(self.k._is_running)
        self.assertIsNone(self.k._exec_greenlet)
        self.k = None

    def test_start_stop(self):
        """
        Test
        """
        self._start_stop_internal(1)

    def test_start_stop_loop20(self):
        """
        Test
        """
        self._start_stop_internal(20)

    # ==========================
    # EXEC
    # ==========================

    def _exec_internal_go(self, exec_interval_ms, run_count):
        """
        Test
        :param exec_interval_ms: test
        !param run_count: Test
        """

        # Reset meter
        # Meters.reset()

        # Init
        self.k = KnockManager(self.config_file)

        # Override for test
        for p in self.k._probe_list:
            p.exec_interval_ms = exec_interval_ms

        # Start
        self.k.start()

        # 100 ms for each probes, wait 1 sec, we should have 10 exec for each at least
        SolBase.sleep(exec_interval_ms * run_count)

        # Stop
        self.k.stop()

        # Check
        for p in self.k._probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            # Windows scheduling is more variable, decrease check
            self.assertGreaterEqual(p.exec_count, run_count / 2)
            self.assertLess(p.exec_count, run_count + 2)
            self.assertGreater(c.initial_ms_start, 0)
            self.assertEqual(p.exec_count, c.exec_count_so_far)

        # Validate
        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_probe_timeout"), 0)
        # Windows scheduling is more variable, decrease check
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_count"), run_count * len(self.k._probe_list) / 2)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        # Windows scheduling is more variable, decrease check
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), run_count / 2)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Finish
        self.k = None

    def test_dict_merge(self):
        """
        Test
        """

        d1 = {
            "knockd": {
                "toto": "totov",
                "tutu": "tutuv",
                "zzz": {
                    "xxx": "xxxv",
                    "yyy": "yyyv"
                }
            }
        }

        d2 = {
            "knockd": {
                "tutu": "123",
                "zzz": {
                    "yyy": "456",
                    "new": "newv"

                },
                "ttt": "999"
            }
        }

        d1 = KnockManager.dict_merge(d1, d2)
        self.assertEqual(d1["knockd"]["toto"], "totov")
        self.assertEqual(d1["knockd"]["tutu"], "123")
        self.assertEqual(d1["knockd"]["zzz"]["xxx"], "xxxv")
        self.assertEqual(d1["knockd"]["zzz"]["yyy"], "456")
        self.assertEqual(d1["knockd"]["zzz"]["new"], "newv")
        self.assertEqual(d1["knockd"]["ttt"], "999")

    @unittest.skipIf(PTools.is_cpu_arm(), "disabled for arm (lagging)")
    def test_exec_basic(self):
        """
        Test
        """
        self._exec_internal_go(50, 20)
        self._exec_internal_go(100, 10)
        self._exec_internal_go(200, 5)
        self._exec_internal_go(500, 2)

    def test_exec_basic_timeout(self):
        """
        Test
        """

        # Init
        self.k = KnockManager(self.config_file)
        self.k._exectimeout_ms = 500

        # Override for test
        for p in self.k._probe_list:
            p.exec_interval_ms = 1000
            p.sleep_ms_in_exec = 1000

        # Start
        self.k.start()

        # We will have 2 timeout at 500 ms
        SolBase.sleep(1500)

        # Stop
        self.k.stop()

        # Check
        for p in self.k._probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreaterEqual(p.exec_count, 0)
            self.assertGreater(c.initial_ms_start, 0)

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_timeout"), len(self.k._probe_list))
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_count"), len(self.k._probe_list))
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 1)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Finish
        self.k = None

    def test_exec_basic_slow_probe_derive(self):
        """
        Test
        """

        # Init
        self.k = KnockManager(self.config_file)
        self.k._exectimeout_ms = 30000

        # Keep only one probe
        self.k._probe_list = [self.k._probe_list[0]]

        # Override for test
        self.assertEqual(len(self.k._probe_list), 1)
        for p in self.k._probe_list:
            p.exec_interval_ms = 2000
            p.sleep_ms_in_exec = 1000
            p.ar_exec_start = list()

        # Start
        ms_start = SolBase.mscurrent()
        self.k.start()

        # We will have
        # run 1 : ms_start
        # run 2 : ms_start + 2000 (this is the interval, even if exec took 2000)
        target_count = 30
        while True:
            ok_count = 0
            for p in self.k._probe_list:
                if len(p.ar_exec_start) >= target_count:
                    ok_count += 1
            if ok_count == len(self.k._probe_list):
                logger.info("Got ok_count signal")
                break
            elif SolBase.msdiff(ms_start) > target_count * (1000 + 2000 + 1000):
                logger.info("Got timeout signal")
                break
            else:
                # Randomize exec sleep between 0 and 1000
                r = random.randint(500, 1500)
                assert 500 <= r <= 1500
                for p in self.k._probe_list:
                    p.sleep_ms_in_exec = r
                # Wait
                SolBase.sleep(100)

        # Stop
        self.k.stop()

        # Check
        for p in self.k._probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreaterEqual(p.exec_count, 0)
            self.assertGreater(c.initial_ms_start, 0)
            self.assertGreater(c.exec_count_so_far, 0)
            self.assertGreaterEqual(len(p.ar_exec_start), 2)

            # Check exec array
            prev_ms = None
            idx = 0
            for cur_ms in p.ar_exec_start:
                if prev_ms is None:
                    initial_delta_ms = SolBase.msdiff(c.initial_ms_start, cur_ms)
                    logger.info("Got prev_ms=%.0f, cur_ms=%.0f, delta_ms=%.0f, initial_delta_ms=%.0f", 0.0, cur_ms, 0.0, initial_delta_ms)
                else:
                    delta_ms = SolBase.msdiff(prev_ms, cur_ms)
                    initial_delta_ms = SolBase.msdiff(c.initial_ms_start, cur_ms)
                    expected_delta_ms = float(idx) * 2000.0
                    derive_ms = initial_delta_ms - expected_delta_ms
                    logger.info("Got delta_ms=%.0f, i_delta_ms=%.0f, exp=%.0f, derive=%.0f", delta_ms, initial_delta_ms, expected_delta_ms, derive_ms)

                    # 500 ms max on derive
                    allowed_derive_ms = 500
                    self.assertLess(derive_ms, allowed_derive_ms)
                    self.assertLess(delta_ms, 2000 + allowed_derive_ms)

                prev_ms = cur_ms
                idx += 1

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_timeout"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_count"), len(self.k._probe_list) * target_count)
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 1)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Finish
        self.k = None

    def test_exec_basic_timeout_with_override(self):
        """
        Test
        """

        # Init
        self.k = KnockManager(self.config_file)
        self.k._exectimeout_ms = 500

        # Override for test
        for p in self.k._probe_list:
            p.exec_interval_ms = 1000
            p.sleep_ms_in_exec = 1000
            # We force timeout to 2000 : we should have no timeout
            p.exec_timeout_override_ms = 2000

        # Start
        self.k.start()

        # We will have NO timeout
        SolBase.sleep(1500)

        # Stop
        self.k.stop()

        # Check
        for p in self.k._probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreaterEqual(p.exec_count, 0)
            self.assertGreater(c.initial_ms_start, 0)

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_timeout"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_count"), len(self.k._probe_list))
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 1)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Finish
        self.k = None

    def test_exec_basic_timeout_x2(self):
        """
        Test
        """

        # Init
        self.k = KnockManager(self.config_file)
        self.k._exectimeout_ms = 500

        # Override for test
        for p in self.k._probe_list:
            p.exec_interval_ms = 1000
            p.sleep_ms_in_exec = 1000

        # Start
        self.k.start()

        # We will have 2 timeout at 500 ms
        # Run 0 : delay 0 ms,    timeout 500 ms => total 500 ms
        # Run 0 : delay 0 ms,    timeout 500 ms => total 500 ms
        # Run 1 : delay 0 ms,    timeout 500 ms => total 500 ms
        # Run 1 : delay 0 ms,    timeout 500 ms => total 500 ms
        # + 250 margin
        SolBase.sleep(500 + 500 + 500 + 500 + 250)

        # Stop
        self.k.stop()

        # Check
        for p in self.k._probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertGreaterEqual(p.exec_count, 0)
            self.assertGreater(c.initial_ms_start, 0)

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_timeout"), len(self.k._probe_list) * 2)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_probe_count"), len(self.k._probe_list) * 2)
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 2)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Finish
        self.k = None

    def test_notify_basic(self):
        """
        Test
        """

        # Reset meter
        # Meters.reset()

        # Init
        self.k = KnockManager(self.config_file)

        # Keep only one item (easier to test)
        self.k._probe_list.pop()

        # Override
        for p in self.k._probe_list:
            p.exec_interval_ms = 500

        # Start
        self.k.start()

        # Wait 1000
        SolBase.sleep(1000 + 250)

        # Stop
        self.k.stop()

        # Check
        for p in self.k._probe_list:
            logger.info("p=%s", p)
            c = self.k._get_probe_context(p)
            self.assertEqual(p.exec_count, 3)
            self.assertGreater(c.initial_ms_start, 0)
            self.assertEqual(c.exec_count_so_far, p.exec_count)

        # Validate

        self.assertEqual(Meters.aig("knock_stat_exec_probe_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_probe_bypass"), 0)

        self.assertEqual(Meters.aig("knock_stat_exec_all_inner_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_outer_exception"), 0)
        self.assertEqual(Meters.aig("knock_stat_exec_all_finally_exception"), 0)
        self.assertGreaterEqual(Meters.aig("knock_stat_exec_all_count"), 3)
        self.assertEqual(Meters.aig("knock_stat_exec_all_too_slow"), 0)

        # Validate discovery
        self.assertEqual(len(self.k._superv_notify_disco_hash), 3)
        expect_disco(self, self.k, "test.dummy.discovery", {"TYPE": "all"})
        expect_disco(self, self.k, "test.dummy.discovery", {"TYPE": "one"})
        expect_disco(self, self.k, "test.dummy.discovery", {"TYPE": "two"})

        # Validate values (6 per exec)
        self.assertEqual(len(self.k._superv_notify_value_list), 3 * 6)

        # Check them
        expect_value(self, self.k, "test.dummy.count", 100, "eq", {"TYPE": "all"}, target_count=3)
        expect_value(self, self.k, "test.dummy.count", 90, "eq", {"TYPE": "one"}, target_count=3)
        expect_value(self, self.k, "test.dummy.count", 10, "eq", {"TYPE": "two"}, target_count=3)

        expect_value(self, self.k, "test.dummy.error", 5, "eq", {"TYPE": "all"}, target_count=3)
        expect_value(self, self.k, "test.dummy.error", 3, "eq", {"TYPE": "one"}, target_count=3)
        expect_value(self, self.k, "test.dummy.error", 2, "eq", {"TYPE": "two"}, target_count=3)

        # Validate node hash
        self.assertEqual(self.k.get_first_transport_by_type(TestTransport).node_hash["host"], SolBase.get_machine_name())

        # Validate transport notify
        self.assertEqual(self.k.get_first_transport_by_type(TestTransport).notify_call_count, 3)
        self.assertEqual(self.k._superv_notify_disco_hash, self.k.get_first_transport_by_type(TestTransport).notify_hash)
        self.assertEqual(self.k._superv_notify_value_list, self.k.get_first_transport_by_type(TestTransport).notify_values)

        # Over
        self.k = None

    def test_invoke(self):
        """
        inv
        :return: (ec, so, si)
        """

        ec, so, se = ButcherTools.invoke("whoami", shell=False, timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, 0)
        self.assertGreater(len(so), 0)
        self.assertEqual(len(se), 0)

        ec, so, se = ButcherTools.invoke("whoami", shell=True, timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, 0)
        self.assertGreater(len(so), 0)
        self.assertEqual(len(se), 0)

        ec, so, se = ButcherTools.invoke("ls -l /tmp", timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, 0)
        self.assertGreater(len(so), 0)
        self.assertEqual(len(se), 0)

        ec, so, se = ButcherTools.invoke("ls -l /tmpxxx", shell=False, timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertNotEqual(ec, 0)
        self.assertEqual(len(so), 0)
        self.assertGreater(len(se), 0)

        ec, so, se = ButcherTools.invoke("ls -l /tmpxxx", shell=True, timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertNotEqual(ec, 0)
        self.assertEqual(len(so), 0)
        self.assertGreater(len(se), 0)

        ec, so, se = ButcherTools.invoke("sleep 2", timeout_ms=100)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, -999)
        self.assertEqual(len(so), 0)
        self.assertEqual(len(se), 0)

        ec, so, se = ButcherTools.invoke("sleep 9", timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, 0)
        self.assertEqual(len(so), 0)
        self.assertEqual(len(se), 0)

        ec, so, se = ButcherTools.invoke("sleep 2", timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, 0)
        self.assertEqual(len(so), 0)
        self.assertEqual(len(se), 0)

        ec, so, se = ButcherTools.invoke("cmd_donotexists", timeout_ms=self.invoke_timeout)
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, -998)
        self.assertEqual(len(so), 0)
        self.assertEqual(len(se), 0)

        self.assertRaises(Exception, ButcherTools.invoke, "ls -l | wc -l")
