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
import logging
import platform
import unittest

import os
import re
from os.path import dirname, abspath
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Cron.Debian.AutoUpdateDebian import AutoUpdateDebian
from knockdaemon2.Cron.Redhat.AutoUpdateRedhat import AutoUpdateRedhat
from knockdaemon2.HttpMock.HttpMock import HttpMock
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)

SolBase.voodoo_init()
SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file=None, log_to_syslog=False, log_to_console=True)


def _get_debian_local_daemon_version():
    """
    For test
    """

    pkg_name = 'knockdaemon2'
    cmd = "apt-cache policy %s" % pkg_name

    # Invoke timeout
    invoke_timeout = 10000
    if PTools.is_cpu_arm():
        invoke_timeout = 120000

    ret_code, so, se = ButcherTools.invoke(cmd, timeout_ms=invoke_timeout)
    if ret_code != 0:
        return None

    for line in so.split('\n'):
        if line.startswith(' ***'):
            version = re.split('\s+', line)[2]
            logger.info('Local version=%s', version)
            return version


def _get_redhat_local_daemon_version():
    """
    For test
    """

    cmd = "yum info knockdaemon2"

    # Invoke timeout
    invoke_timeout = 10000
    if PTools.is_cpu_arm():
        invoke_timeout = 120000

    ret_code, so, se = ButcherTools.invoke(cmd, timeout_ms=invoke_timeout)
    if ret_code != 0:
        return None

    # noinspection PyProtectedMember
    return AutoUpdateRedhat._z_platform_get_local_version_from_buffer(so)


class TestAutoupdate(unittest.TestCase):
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
                                        'conf/realall/knockdaemon2.yaml')

        self.h = None

        # Reset meter
        Meters.reset()

        # Debug stat on exit ?
        self.debug_stat = False

    def tearDown(self):
        """
        Setup (called after each test)
        """

        if self.h:
            logger.warn("h set, stopping, not normal")
            self.h.stop()
            self.h = None

        if self.debug_stat:
            Meters.write_to_logger()

    # ===================================
    # DEBIAN
    # ===================================

    @unittest.skipIf(PTools.get_distribution_type() != "debian", "debian required")
    def test_get_os(self):
        """
        Test get os
        """

        # Local get
        test_name, test_version, _ = platform.linux_distribution()

        # Update, get local version (if installed)
        au = AutoUpdateDebian(config_file_name=self.config_file, unittest=False, auto_start=False, lock_file='/tmp/kdupdate.lock')
        os_name, os_version, os_arch = au._get_os()
        logger.info("GOT %s, %s, %s", os_name, os_version, os_arch)

        self.assertIsNotNone(os_name)
        self.assertIsNotNone(os_version)
        self.assertIsNotNone(os_arch)

        # Need amd64 or aarch64
        self.assertIn(os_arch, ["amd64", "aarch64", "armv6l", "armv7l"])

        # Check
        self.assertTrue(os_name, test_name)
        self.assertTrue(os_version, test_version)

    # ===================================
    # DEBIAN
    # ===================================

    @unittest.skipIf(PTools.get_distribution_type() != "debian", "debian required")
    def test_debian_update_unittest_on(self):
        """
        Test
        """

        # Start mock
        self.h = HttpMock()
        self.h.start()

        # Update, unittest mode ON (mock local version, server version, .deb uri)
        au = AutoUpdateDebian(config_file_name=self.config_file, unittest=True, auto_start=False, lock_file='/tmp/kdupdate.lock')

        # Run
        au.run(force_update=True)

        # Deb file removed
        self.assertFalse(FileUtility.is_file_exist("/tmp/mockdeb"))

        # Manual steps
        au._download_deb_file(au.deb_url)
        self.assertTrue(FileUtility.is_file_exist("/tmp/mockdeb"))
        au._remove_deb()
        self.assertFalse(FileUtility.is_file_exist("/tmp/mockdeb"))

        # Check server version
        self.assertEqual(au.deb_url, "http://127.0.0.1:7900/mockdeb")
        self.assertEqual(au._get_prod_version()[0], "0.1.1-406")
        self.assertEqual(au._z_platform_get_local_version(), "0.1.1-399")

    @unittest.skipIf(PTools.get_distribution_type() != "debian", "debian required")
    def test_debian_get_localversion(self):
        """
        Test get local version (if daemon is installed)
        :return:
        """

        # Check
        if _get_debian_local_daemon_version() is None:
            logger.info("knockdaemon2 is not installed locally (apt), bypass")
            return

        # Update, get local version (if installed)
        au = AutoUpdateDebian(config_file_name=self.config_file, unittest=False, auto_start=False, lock_file='/tmp/kdupdate.lock')
        v = au._z_platform_get_local_version()
        self.assertEqual(v, _get_debian_local_daemon_version())

    # ===================================
    # REDHAT / CENTOS
    # ===================================

    @unittest.skipIf(PTools.get_distribution_type() != "redhat", "redhat/centos required")
    def test_redhat_update_unittest_on(self):
        """
        Test
        """

        # Start mock
        self.h = HttpMock()
        self.h.start()

        # Update, unittest mode ON (mock local version, server version, .deb uri)
        au = AutoUpdateRedhat(config_file_name=self.config_file, unittest=True, auto_start=False, lock_file='/tmp/kdupdate.lock')

        # Run
        au.run(force_update=True)

        # Deb file removed
        self.assertFalse(FileUtility.is_file_exist("/tmp/mockrpm"))

        # Manual steps
        au._download_rpm_file(au.rpm_url)
        self.assertTrue(FileUtility.is_file_exist("/tmp/mockrpm"))
        au._remove_rpm()
        self.assertFalse(FileUtility.is_file_exist("/tmp/mockrpm"))

        # Check server version
        self.assertEqual(au.rpm_url, "http://127.0.0.1:7900/mockrpm")
        self.assertEqual(au._get_prod_version()[0], "0.1.1-452")
        self.assertEqual(au._z_platform_get_local_version(), "0.1.1-401")

    @unittest.skipIf(PTools.get_distribution_type() != "redhat", "redhat/centos required")
    def test_redhat_get_localversion(self):
        """
        Test get local version (if daemon is installed)
        :return:
        """

        # Check
        if _get_redhat_local_daemon_version() is None:
            logger.info("knockdaemon2 is not installed locally (yum), bypass")
            return

        # Update, get local version (if installed)
        au = AutoUpdateRedhat(config_file_name=self.config_file, unittest=False, auto_start=False, lock_file='/tmp/kdupdate.lock')
        v = au._z_platform_get_local_version()
        self.assertEqual(v, _get_redhat_local_daemon_version())

    def test_redhat_yum_info_from_buffer(self):
        """
        Test
        """

        buf = "Installed Packages \n" \
              "Name        : knockdaemon2 \n" \
              "Arch        : x86_64 \n" \
              "Version     : 0.1.1 \n" \
              "Release     : 453 \n" \
              "Size        : 80 M \n" \
              "Repo        : installed \n" \
              "From repo   : knock \n" \
              "Summary     : Knock Center Daemon \n" \
              "URL         : https://knock.center \n" \
              "License     : GPL \n" \
              "Description : Knock Center Daemon \n" \
              "            : https://knock.center \n"

        v = AutoUpdateRedhat._z_platform_get_local_version_from_buffer(buf)
        self.assertEqual(v, "0.1.1-453")
