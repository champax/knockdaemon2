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
import logging
from math import floor

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Uptime(KnockProbe):
    """
    Probe
    """

    UPTIME_PATH = "/proc/uptime"

    def __init__(self):
        """
        Constructor
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.category = "/os/misc"

    def _execute_linux(self):
        """
        Exec
        """

        # Load
        buf = self.get_uptime_buffer()

        # Process
        self.process_uptime_buffer(buf)

    def process_uptime_buffer(self, buf):
        """
        Process
        :param buf: str
        :type buf: str
        """
        # Notify we are up
        self.notify_value_n("k.os.knock", None, 1)
        self.notify_value_n("k.os.uptime", None, int(floor(float(buf.split()[0]))))

    @classmethod
    def get_uptime_buffer(cls):
        """
        Get uptime buffer
        :return: str
        :rtype str
        """
        with open(cls.UPTIME_PATH) as f:
            return f.read()
