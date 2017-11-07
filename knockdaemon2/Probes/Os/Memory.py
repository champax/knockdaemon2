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

from pythonsol.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)
if PTools.get_distribution_type() == "windows":
    from knockdaemon2.Windows.Wmi.Wmi import Wmi

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
        KnockProbe.__init__(self, linux_support=True, windows_support=True)
        self.mem_info = MEMINFO_PATH

        # Go
        self.category = "/os/memory"

    def init_from_config(self, config_parser, section_name):
        """
        Initialize from configuration
        :param config_parser: dict
        :type config_parser: dict
        :param section_name: Ini file section for our probe
        :type section_name: str
        """

        # Base
        KnockProbe.init_from_config(self, config_parser, section_name)

        # Go
        pass

    def _execute_linux(self):
        """
        Execute a probe.
        """

        # Fetch
        memory_total, memory_used, swap_total, swap_used, memory_free, swap_free, memory_buffers, memory_cached = self._get_mem_info()

        # Notify
        self._notify_data(
            memory_total=memory_total,
            memory_used=memory_used,
            memory_cached=memory_cached,
            memory_buffers=memory_buffers,
            memory_free=memory_free,
            swap_total=swap_total,
            swap_used=swap_used,
            swap_free=swap_free,
        )

    def _execute_windows(self):
        """
        Execute a probe.
        """

        # Win32_OperatingSystem :: FreePhysicalMemory
        # => ## FREE RAM SIZE
        # => Number, in kilobytes, of physical memory currently unused and available
        # => in kilobytes

        # Win32_OperatingSystem :: FreeVirtualMemory
        # => Number, in kilobytes, of virtual memory currently unused and available.
        # => in kilobytes

        # Win32_OperatingSystem :: TotalVirtualMemorySize
        # => ## RAM SIZE + SWAP SIZE
        # => calculated by adding the amount of total RAM to the amount of paging space
        # => in kilobytes

        # Win32_OperatingSystem :: TotalVisibleMemorySize
        # => Total amount, in kilobytes, of physical memory available to the operating system
        # => in kilobytes

        # Win32_OperatingSystem :: TotalSwapSpaceSize
        # => ## SWAP SIZE
        # => Total swap space, None if swap OFF
        # => in kilobytes

        # --------------------------------------
        # MEMORY
        # --------------------------------------

        # Win32_PerfFormattedData_PerfOS_Memory :: AvailableBytes
        # => FREE + ZEROED + STANDBY
        # => Amount of physical memory in bytes available to processes running on the computer.
        # => This value is calculated by summing space on the Zeroed, Free, and Standby memory lists.
        # => Free memory is ready for use;
        # => Zeroed memory is pages of memory filled with zeros to prevent later processes from seeing data used by a previous process.
        # => Standby memory is memory removed from a process's working set (its physical memory) on route to disk, but is still available to be recalled
        # => in bytes

        # Win32_PerfFormattedData_PerfOS_Memory :: FreeAndZeroPageListBytes
        # => FREE + ZEROED
        # => Free & Zero Page List Bytes is the amount of physical memory, in bytes, that is assigned to the free and zero page lists.
        # => This memory does not contain cached data. It is immediately available for allocation to a process or for system use.'
        # => in bytes

        # Win32_PerfFormattedData_PerfOS_Memory :: ModifiedPageListBytes
        # => Modified Page List Bytes is the amount of physical memory, in bytes, that is assigned to the modified page list.
        # => This memory contains cached data and code that is not actively in use by processes, the system and the system cache.
        # => This memory needs to be written out before it will be available for allocation to a process or for system use.
        # => in bytes

        # --------------------------------------
        # SWAP (Available only if swap is ON)
        # --------------------------------------

        # Win32_PageFileUsage :: AllocatedBaseSize
        # => Actual amount of disk space allocated for use with this page file
        # => in megabytes

        # Win32_PageFileUsage :: CurrentUsage
        # => Amount of disk space currently used by the page file.
        # => in megabytes

        # --------------------------------------
        # MAPPING
        # --------------------------------------

        # swap_total        => Win32_PageFileUsage :: AllocatedBaseSize (or 0 if None)
        # swap_used         => Win32_PageFileUsage :: CurrentUsage (or 0 if None)
        # swap_free         => swap_total - swap_used (caution if swap_total is 0)

        # memory_total      => Win32_OperatingSystem :: TotalVisibleMemorySize
        # memory_free       => Win32_PerfFormattedData_PerfOS_Memory :: FreeAndZeroPageListBytes
        # memory_cached     => Win32_PerfFormattedData_PerfOS_Memory :: AvailableBytes - Win32_PerfFormattedData_PerfOS_Memory :: FreeAndZeroPageListBytes - Win32_PerfFormattedData_PerfOS_Memory :: ModifiedPageListBytes
        # memory_used       => memory_total - memory_cached - memory_free
        # memory_buffers    => Win32_PerfFormattedData_PerfOS_Memory :: ModifiedPageListBytes

        d = None
        try:
            d, age_ms = Wmi.wmi_get_dict()
            logger.info("Using wmi with age_ms=%s", age_ms)

            # ---------------------
            # FETCH
            # ---------------------
            av_bytes = int(d["Win32_PerfFormattedData_PerfOS_Memory"].get("AvailableBytes", 0))
            free_and_zero_bytes = int(d["Win32_PerfFormattedData_PerfOS_Memory"].get("FreeAndZeroPageListBytes", 0))

            memory_total = int(d["Win32_OperatingSystem"].get("TotalVisibleMemorySize", 0)) * 1024
            memory_free = free_and_zero_bytes
            memory_cached = av_bytes - free_and_zero_bytes
            memory_buffers = int(d["Win32_PerfFormattedData_PerfOS_Memory"].get("ModifiedPageListBytes", 0))
            memory_used = memory_total - memory_cached - memory_free - memory_buffers

            delta_check = memory_total - memory_free - memory_cached - memory_used - memory_buffers

            # Swap (possible multiple page files)
            swap_total = 0
            swap_used = 0
            swap_free = 0
            if "Win32_PageFileUsage" in d:
                # Swap ON
                for cur_pf in d["Win32_PageFileUsage"]:
                    swap_total = int(cur_pf.get("AllocatedBaseSize", 0)) * 1024 * 1024
                    swap_used = int(cur_pf.get("CurrentUsage", 0)) * 1024 * 1024
                swap_free = swap_total - swap_used
            else:
                # Swap OFF
                pass

            # ---------------------
            # LOG
            # ---------------------
            logger.info("Got av_bytes           =%s", av_bytes)
            logger.info("Got free_and_zero_bytes=%s", free_and_zero_bytes)

            logger.info("Got memory_total       =%s", memory_total)
            logger.info("Got memory_used        =%s", memory_used)
            logger.info("Got memory_cached      =%s", memory_cached)
            logger.info("Got memory_free        =%s", memory_free)
            logger.info("Got memory_buffers     =%s", memory_buffers)
            logger.info("Got delta_check        =%s", delta_check)

            logger.info("Got swap_total         =%s", swap_total)
            logger.info("Got swap_used          =%s", swap_used)
            logger.info("Got swap_free          =%s", swap_free)

            # ---------------------
            # NOTIFY
            # ---------------------
            self._notify_data(
                memory_total=memory_total,
                memory_used=memory_used,
                memory_cached=memory_cached,
                memory_buffers=memory_buffers,
                memory_free=memory_free,
                swap_total=swap_total,
                swap_used=swap_used,
                swap_free=swap_free,
            )
        except Exception as e:
            logger.warn("Exception while processing, ex=%s, d=%s", SolBase.extostr(e), d)

    def _notify_data(self, memory_total, memory_used, memory_cached, memory_buffers, memory_free, swap_total, swap_used, swap_free):
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
        self.notify_value_n("k.os.memory.size.available", None, memory_free)
        self.notify_value_n("k.os.swap.size.free", None, swap_free)
        if swap_total > 0:
            self.notify_value_n("k.os.swap.size.pfree", None, 100.1 * swap_free / swap_total)
        else:
            self.notify_value_n("k.os.swap.size.pfree", None, 100)
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

        meminfo_file = None
        try:
            meminfo_file = open(self.mem_info)
            for line in meminfo_file:
                if line.startswith('MemTotal'):
                    memory_total = self._get_value_from_line(line)
                elif line.startswith('MemFree'):
                    memory_free = self._get_value_from_line(line)
                elif line.startswith('Buffers'):
                    memory_buffers = self._get_value_from_line(line)
                elif line.startswith('Cached'):
                    memory_cached = self._get_value_from_line(line)
                elif line.startswith('SwapTotal'):
                    swap_total = self._get_value_from_line(line)
                elif line.startswith('SwapFree'):
                    swap_free = self._get_value_from_line(line)

            # Finish it
            memory_used = memory_total - memory_free - memory_buffers - memory_cached
            swap_used = swap_total - swap_free
            return memory_total, memory_used, swap_total, swap_used, memory_free, swap_free, memory_buffers, memory_cached
        finally:
            if meminfo_file:
                meminfo_file.close()

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
