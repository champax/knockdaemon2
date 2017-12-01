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

from os import listdir
from os.path import isdir, join
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    from knockdaemon2.Windows.Wmi.Wmi import Wmi

logger = logging.getLogger(__name__)


class NumberOfProcesses(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.category = "/os/misc"

    def _execute_linux(self):
        """
        Exec
        """

        # This is in fact the number of running processes
        self.notify_value_n("k.os.processes.total", None, self._get_process_count())

    def _execute_windows(self):
        """
        Exec
        """
        try:
            d, age_ms = Wmi.wmi_get_dict()
            logger.info("Using wmi with age_ms=%s", age_ms)

            # Total thread count is TOO SLOW
            # th_total_count = int(d["WQL_RunningThreadTotalCount"])
            th_total_count = int(d["WQL_RunningThreadCount"])
            logger.info("Got th_total_count=%s", th_total_count)

            self.notify_value_n("k.os.processes.total", None, th_total_count)

        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))

    # noinspection PyMethodMayBeStatic
    def _get_process_count(self):
        """
        Get
        :return:
        """
        result = 0
        for name in listdir("/proc"):
            path = join("/proc", name)
            if isdir(path) and name.isdigit():
                if len(open(path + "/cmdline").readline()) > 0:
                    result += 1
        return result
