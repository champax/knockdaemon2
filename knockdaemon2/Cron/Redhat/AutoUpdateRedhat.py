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
import sys

import os
from os.path import basename
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Cron.AutoUpdateBase import AutoUpdateBase, ExitOnError

SolBase.voodoo_init()

logger = logging.getLogger(__name__)


class AutoUpdateRedhat(AutoUpdateBase):
    """
    Auto update for redhat/centos
    """

    def __init__(self, config_file_name='/etc/knock/knockdaemon2/knockdaemon2.ini', unittest=False, auto_start=True, lock_file='/var/run/knockdaemon2_autoupdate.pid'):
        """
        Init
        :param config_file_name: name of configuration file
        :type config_file_name: str
        :param unittest: run under unittest
        :type unittest: bool
        """

        # Go
        logger.info("Entering")
        self.rpm_file_full_path = None
        self.rpm_url = None

        # Call base
        AutoUpdateBase.__init__(self, config_file_name, unittest, auto_start, lock_file)

    # ==============================================
    # TOOLS
    # ==============================================

    def _download_rpm_file(self, binary_url):
        """
        Download rpm file
        :param binary_url: str
        :type binary_url: str
        """

        logger.info("Going to download rpm file, binary_url=%s", binary_url)

        # Remove file if exist
        filename = basename(binary_url)
        self.rpm_file_full_path = os.path.join('/tmp', filename)
        if os.path.isfile(self.rpm_file_full_path):
            os.unlink(self.rpm_file_full_path)

        # Download
        with open(self.rpm_file_full_path, 'w') as file_handle:
            hreq = HttpRequest()
            hc = HttpClient()
            hreq.uri = binary_url
            logger.info("Starting download, binary_url=%s", binary_url)
            hresp = hc.go_http(hreq)

            # Check
            if hresp.status_code != 200:
                logger.warn('Cant download binary_url=%s, got hresp=%s', binary_url, hresp)
                raise ExitOnError(2, "Download error")

            # Write
            file_handle.write(hresp.buffer)

            # Done
            logger.info("Download done, filesize=%s, path=%s", hresp.content_length, self.rpm_file_full_path)

    def _remove_rpm(self):
        """
        Remove rpm
        """
        os.unlink(self.rpm_file_full_path)

    def _log_yum_info(self):
        """
        Log apt-cache policy
        """

        kh = KnockHelpers()
        cmd = kh.sudoize("yum info knockdaemon2")
        logger.info("Invoking, cmd=%s", cmd)
        ec, so, se = ButcherTools.invoke(cmd, shell=False, timeout_ms=self.invoke_timeout)
        if so:
            so = so.replace("\n", " | ")
        if se:
            se = se.replace("\n", " | ")
        if ec != 0:
            logger.warn("Invoke failed, ec=%s, so=%s, se=%s", ec, so, se)
        else:
            logger.info("Invoke ok, ec=%s, so=%s, se=%s", ec, so, se)

    def _install_rpm(self):
        """
        Install previously downloaded rpm file
        :return:
        :rtype:
        """

        try:

            # Version log
            self._log_yum_info()

            # -----------------------
            # FIRE UPDATE
            # -----------------------

            kh = KnockHelpers()
            cmd = kh.sudoize("yum localinstall -y %s" % self.rpm_file_full_path)
            logger.info("Starting knockdaemon2 installation, using cmd=%s", cmd)
            ec, so, se = ButcherTools.invoke(cmd, shell=True, timeout_ms=self.invoke_timeout)
            if so:
                so = so.replace("\n", " | ")
            if se:
                se = se.replace("\n", " | ")
            if ec != 0:
                logger.warn("Invoke failed, ec=%s, so=%s, se=%s", ec, so, se)
                raise ExitOnError(3, message="so=%s, se=%s" % (so, se))

            logger.info("Installation ok, ec=%s, se=%s, so=%s", ec, so, se)
            logger.info('Updated knockdaemon2 successfully')

        finally:
            # Restart
            self._restart_daemon()

            # Version
            self._log_yum_info()

    # ==============================================
    # ==============================================
    # SYSTEM DEPENDENT
    # ==============================================
    # ==============================================

    def _z_platform_upgrade_knockdaemon2(self, binary_url):
        """
        Local update knock daemon
        :param binary_url: binary package url (deb, rpm, whatever)
        :type binary_url: str
        """

        logger.info("Entering, binary_url=%s", binary_url)

        # Store uri
        self.rpm_url = binary_url

        # Go
        if self._unittest:
            logger.warn("UNITTEST ON, BYPASSING INSTALL")
            self._download_rpm_file(binary_url)
            self._remove_rpm()
            return

        # Real upgrade
        self._download_rpm_file(binary_url)
        self._install_rpm()
        self._remove_rpm()

    def _z_platform_get_local_version(self):
        """
        Get local version from knockdaemon2 using yum info output parsing
        :return: Local version
        :rtype: str
        """

        # No relevant lib at this stage which do not requires yum installed, so let's go manually
        if self._unittest:
            logger.warn("Unittest on, mocking local version=0.1.1-401")
            return "0.1.1-401"

        # Go
        cmd = "yum info knockdaemon2"

        ret_code, so, se = ButcherTools.invoke(cmd, timeout_ms=self.invoke_timeout)
        if ret_code != 0:
            logger.warn("cmd=%s ret_code=%s se=%s", cmd, ret_code, se)
            if not self._unittest:
                sys.exit(ret_code)
            else:
                raise Exception("yum info knockdaemon2 failed")

        # Ok
        return AutoUpdateRedhat._z_platform_get_local_version_from_buffer(so)

    @classmethod
    def _z_platform_get_local_version_from_buffer(cls, buf):
        """
        Get local version from knockdaemon2
        :param buf: yum info output buffer
        :type buf: str
        :return: Local version
        :rtype: str
        """

        logger.info("Got yum info buf=%s", repr(buf))
        rpm_version = None
        rpm_release = None
        for line in buf.split("\n"):
            if line.startswith("Version"):
                rpm_version = line.split(":")[1].strip()
                logger.info('Local rpm_version=%s', rpm_version)
            elif line.startswith("Release"):
                rpm_release = line.split(":")[1].strip()
                logger.info('Local rpm_release=%s', rpm_release)

        # Check
        if rpm_version is None:
            raise Exception("Unable to locate rpm_version")
        if rpm_release is None:
            raise Exception("Unable to locate rpm_release")

        v = rpm_version + "-" + rpm_release
        logger.info("Returning v=%s", v)
        return v
