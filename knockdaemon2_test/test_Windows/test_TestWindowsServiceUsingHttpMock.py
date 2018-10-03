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
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    from knockdaemon2.Windows.KnockDaemon.KnockDaemonEvent import KnockDaemonEvent
    from pysolbase.SolBase import SolBase

    SolBase.voodoo_init()

    import logging
    import os
    import unittest
    from os.path import dirname, abspath

    import gevent
    import redis
    from pysolbase.FileUtility import FileUtility

    from knockdaemon2.HttpMock.HttpMock import HttpMock
    from knockdaemon2.Platform.PTools import PTools
    from knockdaemon2.Windows.KnockDaemon.KnockDaemon import KnockDaemonService, D_PATH, set_default_paths

    logger = logging.getLogger(__name__)


    class TestWindowsServiceUsingHttpMock(unittest.TestCase):
        """
        Test
        """

        def setUp(self):
            """
            Setup
            """

            os.environ.setdefault("KNOCK_UNITTEST", "yes")

            SolBase.voodoo_init()

            # Wait 2 sec
            SolBase.sleep(1000)
            self.run_idx = 0

            # Log
            logger.info("setup : Entering, %s", SolBase.get_current_pid_as_string())

            self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
            self.manager_config_dir = self.current_dir + "conf" + SolBase.get_pathseparator() + "real"
            self.manager_config_file = self.manager_config_dir + SolBase.get_pathseparator() + "knockdaemon2.yaml"

            # Config
            self.testtimeout_ms = 5000
            self.stdout_timeout_ms = 2500
            self.stderr_timeout_ms = 500

            # Temp redis : clear ALL
            r = redis.Redis()
            r.flushall()
            del r

            # Clean
            self._clean_files()

            # Start http
            self._start_http_mock()

        def tearDown(self):
            """
            Test
            """
            if self.h:
                self.h.stop()
                self.h = None

        # ==============================
        # HTTP MOCK
        # ==============================

        def _start_http_mock(self):
            """
            Test
            """
            self.h = HttpMock()

            self.h.start()
            self.assertTrue(self.h._is_running)
            self.assertIsNotNone(self.h._wsgi_server)
            self.assertIsNotNone(self.h._server_greenlet)

            # Wait 1 sec
            SolBase.sleep(1000)

        # ==============================
        # UTILITIES
        # ==============================

        # noinspection PyMethodMayBeStatic
        def _clean_files(self):
            """
            Clean files
            """

            # if FileUtility.is_file_exist(self.daemon_pid_file):
            #     logger.info("Deleting %s", self.daemon_pid_file)
            #    os.remove(self.daemon_pid_file)

        # noinspection PyMethodMayBeStatic
        def _file_to_list(self, file_name, sep="\n"):
            """
            Load a file to a list, \n delimited
            :param file_name: File name
            :type file_name: str
            :param sep: separator
            :type sep: str
            :return list
            :rtype list
            """

            ret = None
            # noinspection PyBroadException
            try:
                if FileUtility.is_file_exist(file_name):
                    ret = FileUtility.file_to_textbuffer(file_name, "ascii")
            except:
                ret = None
            finally:
                if ret:
                    return ret.split(sep)
                else:
                    return list()

        def _status_to_dict(self, file_name, sep="\n", value_sep="="):
            """
            Status to dict
            :param file_name: File name
            :type file_name: str
            :param sep: separator
            :type sep: str
            :param sep: separator for value
            :type sep: str
            :return dict
            :rtype dict
            """

            out_dict = dict()
            cur_list = self._file_to_list(file_name, sep)
            for it in cur_list:
                ar = it.split(value_sep)
                if len(ar) != 2:
                    continue
                out_dict[ar[0]] = ar[1]

            return out_dict

        @unittest.skipIf(PTools.get_distribution_type() != "windows", "no windows service on linux")
        def test_start_status_reload_stop_windows_direct(self):
            """
            Test
            """

            # OVERRIDE CONFIG
            set_default_paths()
            if self.manager_config_dir not in D_PATH["AR_SEARCH_DIRS"]:
                D_PATH["AR_SEARCH_DIRS"] = [self.manager_config_dir]

            # Alloc
            logger.info("*** ALLOC")
            k = KnockDaemonService(args=["knockdaemon2"])

            # Start
            logger.info("*** RUN (BLOCKING, spawned)")
            g = gevent.spawn(k.SvcDoRun)

            # Query
            for _ in range(0, 10):
                logger.info("*** QUERY")
                k.SvcInterrogate()
                SolBase.sleep(500)

            # Force write
            KnockDaemonEvent.write_manager_status(k)

            # Stop
            logger.info("*** STOP")
            k.SvcStop()

            # Check (5 sec timeout)
            g.join(timeout=5.0)
