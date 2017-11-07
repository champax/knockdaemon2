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
import re
from os.path import basename
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Cron.AutoUpdateBase import AutoUpdateBase, ExitOnError

SolBase.voodoo_init()

logger = logging.getLogger(__name__)


class AutoUpdateDebian(AutoUpdateBase):
    """
    Auto update for debian
    """

    def __init__(self, config_file_name='/etc/knock/knockdaemon2/knockdaemon2.yaml', unittest=False, auto_start=True, lock_file='/var/run/knockdaemon2_autoupdate.pid'):
        """
        Init
        :param config_file_name: name of configuration file
        :type config_file_name: str
        :param unittest: run under unittest
        :type unittest: bool
        """

        # Go
        logger.info("Entering")

        # Our variables
        self.deb_file_full_path = None
        self.deb_url = None

        # Call base
        AutoUpdateBase.__init__(self, config_file_name, unittest, auto_start, lock_file)

    def _download_deb_file(self, binary_url):
        """
        Download deb file
        :param binary_url: str
        :type binary_url: str
        :return:
        :rtype:
        """

        logger.info("Going to download deb file, binary_url=%s", binary_url)

        # Remove file if exist
        filename = basename(binary_url)
        self.deb_file_full_path = os.path.join('/tmp', filename)
        if os.path.isfile(self.deb_file_full_path):
            os.unlink(self.deb_file_full_path)

        # Download
        with open(self.deb_file_full_path, 'w') as file_handle:
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
            logger.info("Download done, filesize=%s", hresp.content_length)

    def _log_apt_policy(self):
        """
        Log apt-cache policy
        """

        kh = KnockHelpers()
        cmd = kh.sudoize("apt-cache policy knockdaemon2")
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

    def _install_deb(self):
        """
        Install previously downloaded deb file
        :return:
        :rtype:
        """

        try:
            # Version log
            self._log_apt_policy()

            # -----------------------
            # FIRE UPDATE
            # -----------------------
            kh = KnockHelpers()
            cmd = kh.sudoize("DEBIAN_FRONTEND=noninteractive /usr/bin/dpkg -i --force-confdef --force-confold %s" % self.deb_file_full_path)
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
            self._log_apt_policy()

    def _remove_deb(self):
        """

        :return:
        :rtype:
        """
        os.unlink(self.deb_file_full_path)

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

        # Store uri
        self.deb_url = binary_url

        # Go
        if self._unittest:
            logger.warn("UNITTEST ON, BYPASSING INSTALL")
            self._download_deb_file(binary_url)
            self._remove_deb()
            return

        # Real upgrade
        self._download_deb_file(binary_url)
        self._install_deb()
        self._remove_deb()

    def _z_platform_get_local_version(self):
        """
        Get local version
        :return: Local version
        :rtype: str
        """

        if self._unittest:
            logger.warn("Unittest on, mocking local version=0.1.1-399")
            return "0.1.1-399"

        # Go
        cmd = "apt-cache policy knockdaemon2"

        ret_code, so, se = ButcherTools.invoke(cmd, timeout_ms=self.invoke_timeout)
        if ret_code != 0:
            logger.warn("cmd=%s ret_code=%s se=%s", cmd, ret_code, se)
            if not self._unittest:
                sys.exit(ret_code)
            else:
                raise Exception("apt-cache policy failed")

        for line in so.split('\n'):
            if line.startswith(' ***'):
                version = re.split('\s+', line)[2]
                logger.info('Local version=%s', version)
                return version
