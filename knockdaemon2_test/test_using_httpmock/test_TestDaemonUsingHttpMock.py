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
import sys
import unittest
from multiprocessing import Process
from os.path import dirname, abspath

import redis
from pysolbase.FileUtility import FileUtility

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Daemon.KnockDaemon import KnockDaemon
from knockdaemon2.HttpMock.HttpMock import HttpMock

logger = logging.getLogger(__name__)

# Patch to dispatch env to subprocess
oldPath = os.environ.get("PYTHONPATH")
if oldPath is not None:
    os.environ["PYTHONPATH"] = ":".join(sys.path) + ":" + oldPath
else:
    os.environ["PYTHONPATH"] = ":".join(sys.path)
os.environ["PATH"] = ", ".join(sys.path) + ", " + os.environ["PATH"]

real_stdout = sys.stdout
real_stderr = sys.stderr
real_stdin = sys.stdin


class TestDaemonUsingHttpMock(unittest.TestCase):
    """
    Test
    """

    def setUp(self):
        """
        Setup
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        SolBase.voodoo_init()

        # Reset (teamcity broke the whole stuff)
        logger.info("GOT sys.stdin=%s", sys.stdin)
        logger.info("GOT real_stdin=%s", real_stdin)
        if "TEAMCITY_VERSION" in os.environ:
            self.hack_console=True
        else:
            self.hack_console=False
        logger.info("*** Using hack_console=%s", self.hack_console)

        if self.hack_console:
            self.tc_stdin = sys.stdin
            self.tc_stdout = sys.stdout
            self.tc_stderr = sys.stderr
            sys.stdin = real_stdin
            sys.stdout = real_stdout
            sys.stderr = real_stderr

        # Wait 2 sec
        SolBase.sleep(1000)
        self.run_idx = 0

        # Log
        logger.info("setup : Entering, %s", SolBase.get_current_pid_as_string())

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.manager_config_file = self.current_dir + "conf" + SolBase.get_pathseparator() + "real" + SolBase.get_pathseparator() + "knockdaemon2.yaml"

        # Config
        self.testtimeout_ms = 5000
        self.stdout_timeout_ms = 2500
        self.stderr_timeout_ms = 500

        self.daemon_pid_file = "/tmp/knockdaemon2.pid"
        self.daemon_std_out = "/tmp/knockdaemon2.out.txt"
        self.daemon_std_err = "/tmp/knockdaemon2.err.txt"

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

        # Clean
        self._clean_files()

        # Start http
        self._start_http_mock()

        # Ensure we are ok with gevent #600
        ec, so, se = ButcherTools.invoke("ls -l /tmp")
        logger.info("ec=%s", ec)
        logger.info("so=%s", so)
        logger.info("se=%s", se)
        self.assertEqual(ec, 0)
        self.assertGreater(len(so), 0)
        self.assertEqual(len(se), 0)

    def tearDown(self):
        """
        Test
        """
        if self.h:
            self.h.stop()
            self.h = None

        for cur_f in [self.daemon_std_err, self.daemon_std_out]:
            try:
                logger.info("*** FLUSH, cur_f=%s", cur_f)
                ar = self._file_to_list(cur_f)
                for s in ar:
                    print(s)
            except Exception as e:
                logger.warning("Ex=%s", SolBase.extostr(e))

        for cur_f in [self.daemon_pid_file, self.daemon_std_err, self.daemon_std_out]:
            try:
                if FileUtility.is_file_exist(cur_f):
                    os.remove(cur_f)
            except Exception as e:
                logger.warning("Ex=%s", SolBase.extostr(e))

        # Reset (otherwise it blows up into teamcity again)
        logger.info("*** TEARDOWN in")
        if self.hack_console:
            sys.stdin.close()
            sys.stderr.close()
            sys.stdin.close()
            sys.stdin = self.tc_stdin
            sys.stdout = self.tc_stdout
            sys.stderr = self.tc_stderr
        logger.info("*** TEARDOWN out")

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

    def _clean_files(self):
        """
        Clean files
        """

        if FileUtility.is_file_exist(self.daemon_pid_file):
            logger.info("Deleting %s", self.daemon_pid_file)
            os.remove(self.daemon_pid_file)

        if FileUtility.is_file_exist(self.daemon_std_out):
            logger.info("Deleting %s", self.daemon_std_out)
            os.remove(self.daemon_std_out)

        if FileUtility.is_file_exist(self.daemon_std_err):
            logger.info("Deleting %s", self.daemon_std_err)
            os.remove(self.daemon_std_err)

    # noinspection PyMethodMayBeStatic
    def _reset_std_capture(self):
        """
        Doc
        """
        pass

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
        except Exception:
            ret = None
        finally:
            if ret and len(ret) > 0:
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

    def _get_std_out(self):
        """
        Get
        :return: A String
        """

        ms_start = SolBase.mscurrent()
        while True:
            ar = self._file_to_list(self.daemon_std_out)
            if len(ar) > 0:
                return ar
            elif SolBase.msdiff(ms_start) > self.stdout_timeout_ms:
                return list()
            else:
                SolBase.sleep(10)

    def _get_std_err(self):
        """
        Get
        :return: A String
        """

        ms_start = SolBase.mscurrent()
        while True:
            ar = self._file_to_list(self.daemon_std_err)
            if len(ar) > 0:
                return ar
            elif SolBase.msdiff(ms_start) > self.stderr_timeout_ms:
                return list()
            else:
                SolBase.sleep(10)

    def test_start_status_reload_stop_debian(self):
        """
        Test
        """

        p_list = list()
        try:

            # Start
            self._reset_std_capture()

            # Params
            ar = list()
            ar.append("testProgram")
            ar.append("-pidfile={0}".format(self.daemon_pid_file))
            ar.append("-stderr={0}".format(self.daemon_std_err))
            ar.append("-stdout={0}".format(self.daemon_std_out))
            ar.append("-c={0}".format(self.manager_config_file))
            ar.append("start")

            # =========================
            # START
            # =========================

            # Launch
            logger.info("Firing main_helper, ar=%s", ar)
            p = Process(target=KnockDaemon.main_helper, args=(ar, {}))

            logger.info("Start now")
            p.start()

            logger.info("Join now")
            p.join()

            logger.info("Append now")
            p_list.append(p)

            # Try wait for stdout
            logger.info("Wait now")
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < self.stdout_timeout_ms:
                if "n".join(self._get_std_out()).find("knockdaemon2 started") >= 0:
                    break
                else:
                    SolBase.sleep(10)

            # Check
            logger.info("Check now, p.exitcode=%s", p.exitcode)

            # Get std (caution, we are async since forked)
            logger.debug("stdOut ### START")
            for s in self._get_std_out():
                logger.debug("stdOut => %s", s)
            logger.debug("stdOut ### END")

            logger.debug("stdErr ### START")
            for s in self._get_std_err():
                logger.debug("stdErr => %s", s)
            logger.debug("stdErr ### END")

            # Check
            self.assertTrue(p.exitcode == 0)
            self.assertTrue(len(self._get_std_err()) == 0)
            self.assertTrue("\n".join(self._get_std_out()).find(" ERROR ") < 0)
            self.assertTrue("\n".join(self._get_std_out()).find(" WARN ") < 0)

            # =========================
            # STATUS
            # =========================

            for ii in range(0, 10):
                logger.info("*** STATUS, ii=%s", ii)
                # Args
                ar = list()
                ar.append("testProgram")
                ar.append("-pidfile={0}".format(self.daemon_pid_file))
                ar.append("status")

                # Launch
                p = Process(target=KnockDaemon.main_helper, args=(ar, {}))
                p_list.append(p)
                p.start()
                p.join()
                self.assertTrue(p.exitcode == 0)
                SolBase.sleep(100)

            # =========================
            # RELOAD
            # =========================

            for ii in range(0, 10):
                logger.info("*** RELOAD, ii=%s", ii)

                # Args
                ar = list()
                ar.append("testProgram")
                ar.append("-pidfile={0}".format(self.daemon_pid_file))
                ar.append("reload")

                # Launch
                p = Process(target=KnockDaemon.main_helper, args=(ar, {}))
                p_list.append(p)
                p.start()
                p.join()
                self.assertTrue(p.exitcode == 0)
                SolBase.sleep(100)

            # =========================
            # STOP
            # =========================

            # Args
            ar = list()
            ar.append("testProgram")
            ar.append("-pidfile={0}".format(self.daemon_pid_file))
            ar.append("stop")

            # Launch
            p = Process(target=KnockDaemon.main_helper, args=(ar, {}))
            p_list.append(p)
            p.start()
            p.join()

            # =========================
            # OVER, CHECK LOGS
            # =========================

            # Try wait for stdout
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < self.stdout_timeout_ms:
                if "\n".join(self._get_std_out()).find("knockdaemon2 started") >= 0:
                    break
                else:
                    SolBase.sleep(10)

            # Get std (caution, we are async since forked)
            logger.debug("stdOut ### START")
            for s in self._get_std_out():
                logger.debug("stdOut => %s", s)
            logger.debug("stdOut ### END")

            logger.debug("stdErr ### START")
            for s in self._get_std_err():
                logger.debug("stdErr => %s", s)
            logger.debug("stdErr ### END")

            # Check
            self.assertTrue(p.exitcode == 0)
            self.assertTrue(len(self._get_std_err()) == 0)
            self.assertTrue("\n".join(self._get_std_out()).find(" ERROR ") < 0)
            self.assertTrue("\n".join(self._get_std_out()).find(" WARN ") < 0)

        finally:
            try:
                for p in p_list:
                    p.terminate()
            except Exception as e:
                logger.warning("Ex=%s", e)
            logger.info("Exiting test, idx=%s", self.run_idx)
