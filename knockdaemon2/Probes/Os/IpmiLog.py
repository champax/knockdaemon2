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
import os

from gevent import Timeout

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe
import logging

logger = logging.getLogger(__name__)


class IpmiLog(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """

        """

        KnockProbe.__init__(self)
        self.ipmi_success = True

        self.category = "/os/misc"

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        LA DOC PD DU CUL
        :return:
        """
        if not self.ipmi_success:
            return

        if os.path.isdir('/sys/bus/xen'):
            # Xen
            if not os.path.isfile('/proc/xen/xsd_kva'):
                # Xen Dom U
                self.notify_value_n("k.ipmi.log", None, "No ipmi sel data")
                return
        with Timeout(5):
            try:
                (ec, so, se) = ButcherTools.invoke("ipmi-sel")
                logger.info("ec=%s", ec)
                logger.info("so=%s", so)
                logger.info("se=%s", se)

                if ec == 0:
                    self.notify_value_n("k.ipmi.log", None, so)

            except Timeout:
                self.ipmi_success = False
