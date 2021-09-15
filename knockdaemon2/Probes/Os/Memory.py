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

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)
if PTools.get_distribution_type() == "windows":
    pass

MEMINFO_PATH = '/proc/meminfo'


class Memory(KnockProbe):
    """
    Memory probe
    """

    def __init__(self):
        """
        Constructor
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=False)
        self.mem_info = MEMINFO_PATH

        # Go
        self.category = "/os/memory"

    def _execute_linux(self):
        """
        Execute a probe.
        """

        # Fetch
        logger.info("Getting memory now")
        memory_total, memory_used, swap_total, swap_used, memory_free, swap_free, memory_buffers, memory_cached, memory_available = self._get_mem_info()
        logger.info("Getting memory done")

        # Notify
        self._notify_data(
            memory_total=memory_total,
            memory_used=memory_used,
            memory_available=memory_available,
            memory_cached=memory_cached,
            memory_buffers=memory_buffers,
            memory_free=memory_free,
            swap_total=swap_total,
            swap_used=swap_used,
            swap_free=swap_free,
        )
        logger.info("Notify memory done")

    def _notify_data(self, memory_total, memory_used, memory_cached, memory_buffers, memory_free, swap_total, swap_used, swap_free, memory_available=None):
        """
        Notify
        :param memory_total: int
        :type memory_total: int
        :param memory_used: float
        :type memory_used: float
        :param memory_cached: int
        :type memory_cached: int
        :param memory_buffers: int
        :type memory_buffers: int
        :param memory_free: int
        :type memory_free: int
        :param swap_total: int
        :type swap_total: int
        :param swap_used: float
        :type swap_used: float
        :param swap_free: int
        :type swap_free: int

        """
        self.notify_value_n("k.os.memory.size.free", None, memory_free)
        if memory_available is not None:
            self.notify_value_n("k.os.memory.size.available", None, memory_available)
        self.notify_value_n("k.os.swap.size.free", None, swap_free)
        if swap_total > 0:
            self.notify_value_n("k.os.swap.size.pfree", None, 100.1 * swap_free / swap_total)
        else:
            self.notify_value_n("k.os.swap.size.pfree", None, 100.0)
        self.notify_value_n("k.os.memory.size.total", None, memory_total)
        self.notify_value_n("k.os.swap.size.total", None, swap_total)
        self.notify_value_n("k.os.memory.size.buffers", None, memory_buffers)
        self.notify_value_n("k.os.memory.size.cached", None, memory_cached)
        self.notify_value_n("k.os.memory.size.used", None, memory_used)
        self.notify_value_n("k.os.swap.size.used", None, swap_used)

    def _get_mem_info(self):
        """
        Get memory info
        :return tuple
        :rtype tuple
        """
        memory_total = 0
        memory_free = 0
        memory_buffers = 0
        memory_cached = 0
        swap_total = 0
        swap_free = 0
        memory_available = 0

        meminfo_file = None
        try:
            logger.info("Opening mem_info=%s", self.mem_info)
            meminfo_file = open(self.mem_info)
            logger.info("Opened mem_info=%s", self.mem_info)
            for line in meminfo_file:
                if line.startswith('MemTotal'):
                    memory_total = self._get_value_from_line(line)
                elif line.startswith('MemFree'):
                    memory_free = self._get_value_from_line(line)
                elif line.startswith('MemAvailable'):
                    memory_available = self._get_value_from_line(line)
                elif line.startswith('Buffers'):
                    memory_buffers = self._get_value_from_line(line)
                elif line.startswith('Cached'):
                    memory_cached = self._get_value_from_line(line)
                elif line.startswith('SwapTotal'):
                    swap_total = self._get_value_from_line(line)
                elif line.startswith('SwapFree'):
                    swap_free = self._get_value_from_line(line)

            # Finish it
            logger.info("Parsed mem_info")
            memory_used = memory_total - memory_free - memory_buffers - memory_cached
            swap_used = swap_total - swap_free
            return memory_total, memory_used, swap_total, swap_used, memory_free, swap_free, memory_buffers, memory_cached, memory_available
        finally:
            if meminfo_file:
                meminfo_file.close()

    # noinspection PyMethodMayBeStatic
    def _get_value_from_line(self, line):
        """
        Get
        :param line:
        :return:
        """
        value = line.split()[1]
        # convert into int
        value = int(value)
        # convert from kilobytes into bytes
        value *= 1024
        return value
