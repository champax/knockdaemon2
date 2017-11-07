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
from math import floor

from pythonsol.SolBase import SolBase

from knockdaemon.Core.KnockProbe import KnockProbe
from knockdaemon.Platform.PTools import PTools

logger = logging.getLogger(__name__)
if PTools.get_distribution_type() == "windows":
    from knockdaemon.Windows.Wmi.Wmi import Wmi

UPTIME_PATH = "/proc/uptime"


class Uptime(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Constructor
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.category = "/os/misc"

    def _execute_linux(self):
        """
        Exec
        """
        # Notify we are up
        self.notify_value_n("k.os.knock", None, 1)
        self.notify_value_n("k.os.uptime", None, self._get_uptime())

    def _execute_windows(self):
        """
        Exec
        """

        d = None
        try:
            # Win32_OperatingSystem :: LastBootUpTime => 20170312044209.003363-420
            # => Date and time the operating system was last restarted.
            # => unicode

            # Win32_PerfFormattedData_PerfOS_System :: SystemUpTime
            # => Elapsed time, in seconds, that the computer has been running after it was last started.
            # => This property displays the difference between the start time and the current time.

            d, age_ms = Wmi.wmi_get_dict()
            logger.info("Using wmi with age_ms=%s", age_ms)

            elapsed_sec = int(d["Win32_PerfFormattedData_PerfOS_System"]["SystemUpTime"])
            logger.info("Got elapsed_sec=%s", elapsed_sec)

            # Notify we are up
            self.notify_value_n("k.os.knock", None, 1)
            self.notify_value_n("k.os.uptime", None, elapsed_sec)
        except Exception as e:
            logger.warn("Exception while processing, ex=%s, d=%s", SolBase.extostr(e), d)

    def _get_uptime(self):
        """
        Get uptime in seconds
        :return:
        """

        # The first number is the total number of seconds the system has been up
        uptime_file = open(UPTIME_PATH)
        uptime = int(floor(float(uptime_file.read().split()[0])))
        uptime_file.close()
        return uptime
