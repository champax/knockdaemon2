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

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Memory(KnockProbe):
    """
    Memory probe
    """

    MEMINFO_PATH = '/proc/meminfo'

    def __init__(self):
        """
        Constructor
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        # Go
        self.category = "/os/memory"

        # Memory file
        self.mem_info_file = Memory.MEMINFO_PATH

    def _execute_linux(self):
        """
        Execute a probe.
        """

        # Fetch
        memory_total, memory_used, swap_total, swap_used, memory_free, swap_free, memory_buffers, memory_cached, memory_available = self.get_mem_info()

        # Notify
        self.notify_mem_info(
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

    def notify_mem_info(self, memory_total, memory_used, memory_cached, memory_buffers, memory_free, swap_total, swap_used, swap_free, memory_available=None):
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
        :param memory_available: int,None
        :type memory_available: int,None

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

    def get_mem_info(self):
        """
        Get memory info
        :return tuple
        :rtype tuple
        """

        with open(self.mem_info_file) as f1:
            return self.get_mem_info_from_buffer(f1.read())

    @classmethod
    def get_mem_info_from_buffer(cls, buf):
        """
        Get mem info from buffer
        :param buf: str
        :type buf: str
        :return: tuple
        :rtype tuple
        """

        memory_total = 0
        memory_free = 0
        memory_buffers = 0
        memory_cached = 0
        swap_total = 0
        swap_free = 0
        memory_available = 0

        ar = buf.split("\n")
        for line in ar:
            if line.startswith('MemTotal'):
                memory_total = cls.get_value_from_line(line)
            elif line.startswith('MemFree'):
                memory_free = cls.get_value_from_line(line)
            elif line.startswith('MemAvailable'):
                memory_available = cls.get_value_from_line(line)
            elif line.startswith('Buffers'):
                memory_buffers = cls.get_value_from_line(line)
            elif line.startswith('Cached'):
                memory_cached = cls.get_value_from_line(line)
            elif line.startswith('SwapTotal'):
                swap_total = cls.get_value_from_line(line)
            elif line.startswith('SwapFree'):
                swap_free = cls.get_value_from_line(line)

        # Finish it
        memory_used = memory_total - memory_free - memory_buffers - memory_cached
        swap_used = swap_total - swap_free
        return memory_total, memory_used, swap_total, swap_used, memory_free, swap_free, memory_buffers, memory_cached, memory_available

    @classmethod
    def get_value_from_line(cls, line):
        """
        Get
        :param line:str
        :type line: str
        :return: int
        :rtype int
        """
        value = line.split()[1]
        # convert into int
        value = int(value)
        # convert from kilobytes into bytes (if kB found)
        if line.lower().endswith("kb"):
            value *= 1024
        return value
