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
import os
import re
import stat

from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


def get_zpool_io_buffer(file_name):
    """
    Get zpool io
    :param file_name: str
    :type file_name: str
    :return: str
    :rtype str
    """
    with open(file_name) as f:
        return f.read()


class DiskSpace(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.hash_fs = dict()
        self.previous_stat = dict()

        # Windows tricks
        self._last_run_ms = SolBase.mscurrent()
        self._d_accu = None

        self.category = "/os/disk"

    @classmethod
    def get_cmdline_buffer(cls):
        """
        Get cmdline buffer
        :return: None,str
        :rtype None,str
        """
        try:
            with open('/proc/cmdline') as f:
                return f.read()
        except Exception as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
            return None

    @classmethod
    def resolv_root(cls, cmdline_buf):
        """
        Convert obscure /dev/root to something more usable
        :param cmdline_buf: str,None
        :type cmdline_buf: str,None
        :return list,None
        :rtype list,None
        """
        try:
            if cmdline_buf is None:
                return None
            cmdline_buf = cmdline_buf.strip()
            if len(cmdline_buf) == 0:
                return None
            for block in cmdline_buf.strip().split(' '):
                if block.startswith('root='):
                    _, device = block.split('=')
                    return device
        except Exception as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
            return None

    @classmethod
    def add_to_hash(cls, h, key, value):
        """
        Add to specified hash ("max" for dev.io.percentused, "sum" for others)
        :param h: Hash
        :type h: dict
        :param key: Key
        :type key: str
        :param value: Value
        :type value: int, float
        """
        if key not in h:
            h[key] = value
        else:
            if key.startswith('k.vfs.dev.io.percentused'):
                h[key] = max(value, h[key])
            else:
                h[key] += value

    def hash_file_reset(self):
        """
        Reset all
        """

        self.hash_fs = dict()

    def hash_file(self, key, d_disco, new_val, operator):
        """
        Hash file item
        :param key: Key
        :type key: str
        :param d_disco: dict
        :type d_disco: dict
        :param new_val: Value
        :type new_val: int, float
        :param operator: Operator
        :type operator: str
        """

        if key not in self.hash_fs:
            # Not hashed : set
            self.hash_fs[key] = (d_disco, new_val)
            return

        # Hashed, get
        cur_val = self.hash_fs[key][1]

        # Apply operator
        if operator == "max":
            self.hash_fs[key] = (d_disco, max(cur_val, new_val))
        elif operator == "min":
            self.hash_fs[key] = (d_disco, min(cur_val, new_val))
        elif operator == "sum":
            self.hash_fs[key] = (d_disco, cur_val + new_val)

    def _execute_linux(self):
        """
        Exec
        """

        # READ : cmdline
        buf_cmdline = self.get_cmdline_buffer()

        # READ : diskstats
        with open('/proc/diskstats', mode='r') as f:
            buf_diskstats = f.read()

        # READ: mtab
        with open('/etc/mtab', mode='r') as f:
            buf_mtab = f.read()

        # Process
        self.process_from_buffer(buf_cmdline, buf_diskstats, buf_mtab)

    @classmethod
    def can_be_processed(cls, fstype, mountpoint):
        """
        Check if we can process this file system
        :param fstype: str
        :type fstype: str
        :param mountpoint: str
        :type mountpoint: str
        :return: bool
        :rtype bool
        """
        if fstype in ('ext2', 'ext3', 'ext4', 'zfs', 'xfs', 'btrfs'):
            if mountpoint.startswith('/mnt/') or \
                    mountpoint.startswith('/tmp/') or \
                    mountpoint.startswith('/media/') or \
                    "/.zfs/snapshot/" in mountpoint:
                return False
            else:
                return True
        else:
            return False

    def process_from_buffer(self, buf_cmdline, buf_diskstats, buf_mtab):
        """
        Process from buffer
        :param buf_cmdline: str,None
        :type buf_cmdline: str,None
        :param buf_diskstats: str
        :type buf_diskstats: str
        :param buf_mtab: str
        :type buf_mtab: str
        """

        # Reset
        self.hash_file_reset()
        all_hash = dict()

        # Split
        ar_diskstats = buf_diskstats.split("\n")

        # Root resolve
        resolved_root = self.resolv_root(buf_cmdline)

        # PROCESS : mtab
        for line in buf_mtab.split("\n"):
            line = line.strip()
            if len(line) == 0:
                continue
            # Split
            device, mountpoint, fstype, options, order, prio = line.split()

            # Check
            if not self.can_be_processed(fstype, mountpoint):
                continue

            # Usage
            self.notify_disk_usage(mountpoint)

            # Go
            current_time_ms = SolBase.mscurrent()
            # CHECK ZFS
            if fstype in 'zfs':
                # ----------------------------------
                # ZFS
                # ----------------------------------
                if '/' in device:
                    device = device.split('/')[0]

                # only zpool have stat
                try:
                    # FILE_OP : mocked in unittest
                    zpool_io_buf = get_zpool_io_buffer('/proc/spl/kstat/zfs/' + device + '/io')
                    stats_disk = zpool_io_buf.split("\n")[2]

                    """
                    u_longlong_t     nread;       /* number of bytes read */
                    u_longlong_t     nwritten;    /* number of bytes written */
                    uint_t           reads;       /* number of read operations */
                    uint_t           writes;      /* number of write operations */
                    hrtime_t         wtime;       /* cumulative wait (pre-service) time nanosec*/
                    hrtime_t         wlentime;    /* cumulative wait length*time product*/
                    hrtime_t         wlastupdate; /* last time wait queue changed */
                    hrtime_t         rtime;       /* cumulative run (service) time nanosec*/
                    hrtime_t         rlentime;    /* cumulative run length*time product */
                    hrtime_t         rlastupdate; /* last time run queue changed */
                    uint_t           wcnt;        /* count of elements in wait state */
                    uint_t           rcnt;        /* count of elements in run state */
                    """
                    # parse stat_disk and cast to float
                    nread, nwritten, reads, writes, wtime, wlentime, wlastupdate, rtime, rlentime, rlastupdate, wcnt, rcnt = map(lambda x: float(x), stats_disk.split())

                    if mountpoint not in self.previous_stat:
                        self.previous_stat[mountpoint] = dict()
                    cumulative_wait_rtime_ms = rtime * 10 ** -6

                    if 'cumulative_wait_rtime_ms' in self.previous_stat[mountpoint]:
                        last_rtime_used = cumulative_wait_rtime_ms - self.previous_stat[mountpoint]['cumulative_wait_rtime_ms']
                        last_time_elapsed = current_time_ms - self.previous_stat[mountpoint]['current_time_ms']

                        percent_io_used_rtime = last_rtime_used / last_time_elapsed * 100

                        self.notify_value_n("k.vfs.dev.io.percentused", {"FSNAME": mountpoint}, percent_io_used_rtime)

                        self.add_to_hash(all_hash, 'k.vfs.dev.io.percentused', percent_io_used_rtime)

                    self.previous_stat[mountpoint]['cumulative_wait_rtime_ms'] = cumulative_wait_rtime_ms
                    self.previous_stat[mountpoint]['current_time_ms'] = current_time_ms

                    self.notify_value_n("k.vfs.dev.read.totalcount", {"FSNAME": mountpoint}, int(reads))
                    self.notify_value_n("k.vfs.dev.read.totalbytes", {"FSNAME": mountpoint}, int(nread))

                    self.notify_value_n("k.vfs.dev.write.totalcount", {"FSNAME": mountpoint}, int(writes))
                    self.notify_value_n("k.vfs.dev.write.totalbytes", {"FSNAME": mountpoint}, int(nwritten))

                    self.notify_value_n("k.vfs.dev.io.currentcount", {"FSNAME": mountpoint}, int(rcnt))
                    self.notify_value_n("k.vfs.dev.io.totalms", {"FSNAME": mountpoint}, int(cumulative_wait_rtime_ms))

                    # All
                    self.add_to_hash(all_hash, 'k.vfs.dev.read.totalcount', int(reads))
                    self.add_to_hash(all_hash, 'k.vfs.dev.read.totalbytes', int(nread))

                    self.add_to_hash(all_hash, 'k.vfs.dev.write.totalcount', int(writes))
                    self.add_to_hash(all_hash, 'k.vfs.dev.write.totalbytes', int(nwritten))

                    self.add_to_hash(all_hash, 'k.vfs.dev.io.currentcount', int(rcnt))
                    self.add_to_hash(all_hash, 'k.vfs.dev.io.totalms', int(cumulative_wait_rtime_ms))

                except Exception as e:
                    logger.warning("Ex=%s", SolBase.extostr(e))
            else:
                # ----------------------------------
                # NON ZFS
                # ----------------------------------

                # Convert obscure /dev/root to something more usable
                if device == '/dev/root':
                    device = resolved_root
                    if device is None:
                        continue

                # FILE_OP : mocked in unittest
                mode = os.stat(device)
                if stat.S_ISLNK(mode.st_mode):
                    device = os.path.realpath(device)
                    mode = os.stat(device)

                # FILE_OP (indirect) : both mocked in unittest
                major = os.major(mode.st_rdev)
                minor = os.minor(mode.st_rdev)
                for line2 in ar_diskstats:
                    line2 = line2.strip()
                    if len(line2) == 0:
                        continue
                    regex = r"^\s*" + str(major) + r"\s+" + str(minor) + r"\s+"
                    if not re.search(regex, line2):
                        continue
                    temp_ar = line2.split()

                    # line is THE good line
                    self.notify_value_n("k.vfs.dev.read.totalcount", {"FSNAME": mountpoint}, int(temp_ar[3]))
                    self.notify_value_n("k.vfs.dev.read.totalsectorcount", {"FSNAME": mountpoint}, int(temp_ar[5]))
                    self.notify_value_n("k.vfs.dev.read.totalbytes", {"FSNAME": mountpoint}, int(temp_ar[5]) * 512)
                    self.notify_value_n("k.vfs.dev.read.totalms", {"FSNAME": mountpoint}, int(temp_ar[6]))
                    self.notify_value_n("k.vfs.dev.write.totalcount", {"FSNAME": mountpoint}, int(temp_ar[7]))
                    self.notify_value_n("k.vfs.dev.write.totalsectorcount", {"FSNAME": mountpoint}, int(temp_ar[9]))
                    self.notify_value_n("k.vfs.dev.write.totalbytes", {"FSNAME": mountpoint}, int(temp_ar[9]) * 512)
                    self.notify_value_n("k.vfs.dev.write.totalms", {"FSNAME": mountpoint}, int(temp_ar[10]))
                    self.notify_value_n("k.vfs.dev.io.currentcount", {"FSNAME": mountpoint}, int(temp_ar[11]))
                    self.notify_value_n("k.vfs.dev.io.totalms", {"FSNAME": mountpoint}, int(temp_ar[12]))

                    # ALL handling
                    self.add_to_hash(all_hash, 'k.vfs.dev.read.totalcount', int(temp_ar[3]))
                    self.add_to_hash(all_hash, 'k.vfs.dev.read.totalsectorcount', int(temp_ar[5]))
                    self.add_to_hash(all_hash, 'k.vfs.dev.read.totalbytes', (int(temp_ar[5]) * 512))
                    self.add_to_hash(all_hash, 'k.vfs.dev.read.totalms', int(temp_ar[6]))

                    self.add_to_hash(all_hash, 'k.vfs.dev.write.totalcount', int(temp_ar[7]))

                    self.add_to_hash(all_hash, 'k.vfs.dev.write.totalsectorcount', int(temp_ar[9]))
                    self.add_to_hash(all_hash, 'k.vfs.dev.write.totalbytes', (int(temp_ar[9]) * 512))
                    self.add_to_hash(all_hash, 'k.vfs.dev.write.totalms', int(temp_ar[10]))

                    self.add_to_hash(all_hash, 'k.vfs.dev.io.currentcount', int(temp_ar[11]))
                    self.add_to_hash(all_hash, 'k.vfs.dev.io.totalms', int(temp_ar[12]))

                    if mountpoint not in self.previous_stat:
                        self.previous_stat[mountpoint] = dict()

                    cumulative_wait_time_ms = float(temp_ar[12])
                    if 'cumulative_wait_time_ms' in self.previous_stat[mountpoint]:
                        last_time_used = cumulative_wait_time_ms - self.previous_stat[mountpoint]['cumulative_wait_time_ms']
                        last_time_elapsed = current_time_ms - self.previous_stat[mountpoint]['current_time_ms']

                        logger.debug("calculating percent_io_used_time, mountpoint=%s  last_time_elapsed=%s , self.previous_stat[mountpoint]=%s", mountpoint, last_time_elapsed, self.previous_stat[mountpoint])
                        percent_io_used_time = last_time_used / last_time_elapsed * 100

                        self.notify_value_n("k.vfs.dev.io.percentused", {"FSNAME": mountpoint}, percent_io_used_time)
                        self.add_to_hash(all_hash, 'k.vfs.dev.io.percentused', percent_io_used_time)

                    self.previous_stat[mountpoint]['cumulative_wait_time_ms'] = cumulative_wait_time_ms
                    self.previous_stat[mountpoint]['current_time_ms'] = current_time_ms
                    break

        # -----------------------------
        # Handle "ALL" keys
        # -----------------------------
        for key, value in all_hash.items():
            self.notify_value_n(key, {"FSNAME": "ALL"}, value)

        for key, v in self.hash_fs.items():
            d_disco = v[0]
            value = v[1]
            self.notify_value_n(key, d_disco, value)

    def notify_disk_usage(self, path):
        """
        Push disk usage statistics about the given path.

        Returned valus is a named tuple with attributes 'total', 'used' and
        'free', which are the amount of total, used and free space, in bytes.
        :param path: str
        :type path: str
        """
        # FILE_OP : mocked in unittest
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        pfree = round(100.0 * free / total, 2)
        if st.f_files == 0:
            inodepfree = 100.0
        else:
            inodepfree = 100.0 * st.f_ffree / st.f_files

        self.notify_value_n("k.vfs.fs.size.free", {"FSNAME": path}, free)
        self.notify_value_n("k.vfs.fs.size.pfree", {"FSNAME": path}, pfree)
        self.notify_value_n("k.vfs.fs.inode.pfree", {"FSNAME": path}, inodepfree)
        self.notify_value_n("k.vfs.fs.size.total", {"FSNAME": path}, total)
        self.notify_value_n("k.vfs.fs.size.used", {"FSNAME": path}, used)

        # Max handling
        self.hash_file('k.vfs.fs.size.free', {"FSNAME": "ALL"}, free, "min")
        self.hash_file('k.vfs.fs.size.pfree', {"FSNAME": "ALL"}, pfree, "min")
        self.hash_file('k.vfs.fs.inode.pfree', {"FSNAME": "ALL"}, inodepfree, "min")
        self.hash_file('k.vfs.fs.size.total', {"FSNAME": "ALL"}, total, "sum")
        self.hash_file('k.vfs.fs.size.used', {"FSNAME": "ALL"}, used, "sum")
