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
from math import floor

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)
if PTools.get_distribution_type() == "windows":
    pass

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

    # noinspection PyMethodMayBeStatic
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
