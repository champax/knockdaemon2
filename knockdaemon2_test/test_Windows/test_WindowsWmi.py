"""
-*- coding: utf-8 -*-
===============================================================================

Copyright (C) 2013/2016 Laurent Labatut / Laurent Champagnac



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
import unittest
from collections import Sized

from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    from pysolbase.SolBase import SolBase
    from knockdaemon2.Windows.Helper.Netstat import get_netstat

    SolBase.voodoo_init()

    import logging
    import os

    from os.path import dirname, abspath

    from knockdaemon2.Windows.Wmi.Wmi import Wmi

    logger = logging.getLogger(__name__)

    SolBase.voodoo_init()
    SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file=None, log_to_syslog=False, log_to_console=True)


    class TestWindowsWmi(unittest.TestCase):
        """
        Test description
        """

        def setUp(self):
            """
            Setup (called before each test)
            """

            os.environ.setdefault("KNOCK_UNITTEST", "yes")

            self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
            self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            'conf/realall/knockdaemon2.ini')
            self.refresh_count = 0
            Wmi._reset()

        def tearDown(self):
            """
            Setup (called after each test)
            """

            Wmi.wmi_stop()
            Wmi._reset()

        def test_wmi_fetch_all(self):
            """
            Test
            """

            logger.info("Go")

            # Full fetch
            Wmi._wmi_fetch_all()

            # Get
            d_ms = Wmi._WMI_DICT_LAST_REFRESH_MS
            d_wmi = Wmi._WMI_DICT
            self.assertIsNotNone(d_ms)
            self.assertIsNotNone(d_wmi)

            # Flush
            Wmi._flush_props(Wmi._WMI_DICT, Wmi._WMI_DICT_PROPS)

            # ---------------------
            # Check
            # ---------------------

            self.assertEqual(len(d_wmi), len(Wmi._WMI_INSTANCES))

            for k1, v1 in d_wmi.iteritems():
                d_wmi = Wmi._WMI_INSTANCES[k1]
                if d_wmi["type"] == "direct":
                    self.assertIsInstance(v1, dict)
                    self.assertGreaterEqual(len(v1), 1)
                elif d_wmi["type"] == "list":
                    self.assertIsInstance(v1, list)
                    self.assertGreaterEqual(len(v1), 1)
                    self.assertIsInstance(v1[0], dict)
                    self.assertGreaterEqual(len(v1[0]), 1)
                elif d_wmi["type"] == "wql":
                    if d_wmi["read"] == "count":
                        self.assertIsInstance(v1, int)
                    elif d_wmi["read"] == "list":
                        self.assertIsInstance(v1, list)
                    elif d_wmi["read"] == "direct":
                        self.assertIsInstance(v1, dict)
                    else:
                        self.fail("Invalid read=%s" % d_wmi["read"])
                else:
                    self.fail("Invalid type=%s" % d_wmi["type"])

            # ==================================
            # Ensure recent for all classes
            # TODO : Enhance test here for ensure_recent
            # ==================================
            for k in Wmi._WMI_DICT.keys():
                Wmi.ensure_recent(k)

            # AND FULL FETCH
            Wmi._wmi_fetch_all()

        def on_wmi_refresh(self):
            """
            Test
            """
            logger.info("Got wmi refresh!")
            self.refresh_count += 1

        def test_wmi_start_schedule_stop_loop(self):
            """
            Test
            """
            for i in range(3):
                try:
                    logger.info("*** START CHECK PASS %s", i)

                    # Reset
                    self.refresh_count = 0
                    Wmi._reset()

                    # REGISTER US
                    Wmi._WMI_UNITTEST_CB = self.on_wmi_refresh

                    # OVERRIDE
                    Wmi._WMI_GREENLET_INTERVAL_MS = 1000

                    # ------------------------
                    # Check initial
                    # ------------------------
                    self.assertIsNone(Wmi._WMI_DICT)
                    self.assertIsNone(Wmi._WMI_DICT_LAST_REFRESH_MS)
                    self.assertFalse(Wmi._WMI_IS_STARTED)
                    self.assertIsNone(Wmi._WMI_GREENLET)

                    # ------------------------
                    # Start
                    # ------------------------
                    Wmi.wmi_start()

                    # Check
                    self.assertIsNotNone(Wmi._WMI_DICT)
                    self.assertIsNotNone(Wmi._WMI_DICT_LAST_REFRESH_MS)
                    _ = Wmi._WMI_DICT
                    ms_1 = Wmi._WMI_DICT_LAST_REFRESH_MS
                    self.assertTrue(Wmi._WMI_IS_STARTED)
                    self.assertIsNotNone(Wmi._WMI_GREENLET)
                    self.assertEqual(len(Wmi._WMI_DICT), len(Wmi._WMI_INSTANCES))
                    for k1, d1 in Wmi._WMI_DICT.iteritems():
                        if isinstance(d1, Sized):
                            self.assertGreaterEqual(len(d1), 1)
                        else:
                            self.assertIsNotNone(d1)

                    # ------------------------
                    # Wait until refresh
                    # ------------------------
                    for refresh_loop in range(0, 3):
                        ms = SolBase.mscurrent()
                        while True:
                            if self.refresh_count > refresh_loop + 1:
                                logger.info("Refresh reached, loop=%s+1, count=%s", refresh_loop, self.refresh_count)
                                break
                            elif SolBase.msdiff(ms) > Wmi._WMI_DICT_LAST_REFRESH_MS + (Wmi._WMI_GREENLET_INTERVAL_MS * 2):
                                # Timeout
                                logger.warn("Timeout waiting for WMI Refresh")
                                break

                            else:
                                SolBase.sleep(100)

                        # ------------------------
                        # Check refresh now
                        # ------------------------
                        self.assertIsNotNone(Wmi._WMI_DICT)
                        self.assertIsNotNone(Wmi._WMI_DICT_LAST_REFRESH_MS)
                        _ = Wmi._WMI_DICT
                        ms_2 = Wmi._WMI_DICT_LAST_REFRESH_MS
                        self.assertTrue(Wmi._WMI_IS_STARTED)
                        self.assertIsNotNone(Wmi._WMI_GREENLET)
                        self.assertEqual(len(Wmi._WMI_DICT), len(Wmi._WMI_INSTANCES))
                        for k1, d1 in Wmi._WMI_DICT.iteritems():
                            if isinstance(d1, Sized):
                                self.assertGreaterEqual(len(d1), 1)
                            else:
                                self.assertIsNotNone(d1)

                        self.assertNotEqual(ms_1, ms_2)
                        self.assertGreater(ms_2, ms_1)

                    # ------------------------
                    # Stop
                    # ------------------------
                    Wmi.wmi_stop()

                    # Check (dict is retained on stop)
                    self.assertIsNotNone(Wmi._WMI_DICT)
                    self.assertIsNotNone(Wmi._WMI_DICT_LAST_REFRESH_MS)
                    self.assertFalse(Wmi._WMI_IS_STARTED)
                    self.assertIsNone(Wmi._WMI_GREENLET)

                finally:
                    Wmi._WMI_UNITTEST_CB = None
                    Wmi.wmi_stop()
                    logger.info("*** END CHECK PASS %s", i)

        def test_netstat(self):
            """
            Test
            """

            ar = get_netstat()
            for d in ar:
                logger.info("d=%s", d)
                self.assertIn("local_addr", d)
                self.assertIn("local_port", d)
                self.assertIn("remote_addr", d)
                self.assertIn("remote_port", d)
                self.assertIn("state", d)
                self.assertIn("pid", d)

        def test_uint32_max(self):
            """
            Test
            """

            v1 = -1000000000.0
            v2 = Wmi.fix_uint32_max(v1)
            self.assertEqual(v2, 3294967295.0)

            v1 = 1000000000.0
            v2 = Wmi.fix_uint32_max(v1)
            self.assertEqual(v2, 1000000000.0)
