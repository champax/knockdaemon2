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
import os
import time

from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Load(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self._cpu_count = None
        self.category = "/os/load"

    def _execute_linux(self):
        """
        Exec
        """

        # Load
        load1, load5, load15 = self.get_load_avg()

        # Cpu
        d_cpu = self.get_cpu_stats()

        # Sysctl
        d_sysctl = self.get_sysctl()

        # User count
        n_users = self.get_users_count()

        # Set cpu count
        self._linux_set_cpu_count()

        # Host name
        hostname = os.uname()[1]

        # Local time
        local_time = int(time.time())

        # Go
        self.process_parsed(hostname, local_time, self._cpu_count, load1, load5, load15, d_cpu, d_sysctl, n_users)

    def process_parsed(self, hostname, local_time, n_cpu, load1, load5, load15, d_cpu, d_sysctl, n_users):
        """
        Process parsed
        :param hostname: str
        :type hostname: str
        :param local_time: int
        :type local_time: int
        :param n_cpu: int
        :type n_cpu: int
        :param load1: int
        :type load1: int
        :param load5: int
        :type load5: int
        :param load15: int
        :type load15: int
        :param d_cpu: dict
        :type d_cpu: dict
        :param d_sysctl: dict
        :type d_sysctl: dict
        :param n_users: int
        :type n_users: int
        """

        # Direct
        self.notify_value_n("k.os.hostname", None, hostname)
        self.notify_value_n("k.os.localtime", None, local_time)

        # From load
        self.notify_value_n("k.os.cpu.load.percpu.avg1", None, load1 / n_cpu)
        self.notify_value_n("k.os.cpu.load.percpu.avg5", None, load5 / n_cpu)
        self.notify_value_n("k.os.cpu.load.percpu.avg15", None, load15 / n_cpu)
        self.notify_value_n("k.os.cpu.core", None, n_cpu)

        # From cpu
        for key, value in d_cpu.items():
            if isinstance(value, (int, float)):
                if key not in "total,guest":
                    if value < 0:
                        value = 0
                    self.notify_value_n("k.os.cpu.util." + key, None, value / n_cpu)

        self.notify_value_n("k.os.cpu.switches", None, int(d_cpu["ctxt"]))
        self.notify_value_n("k.os.cpu.intr", None, int(d_cpu["softirqcount"]))
        self.notify_value_n("k.os.boottime", None, int(d_cpu["btime"]))
        self.notify_value_n("k.os.processes.running", None, int(d_cpu["proc_running"]))

        # From sysctl
        self.notify_value_n("k.os.maxfiles", None, int(d_sysctl["max_open_files"]))
        self.notify_value_n("k.os.maxproc", None, int(d_sysctl["max_proc"]))
        self.notify_value_n("k.os.openfiles", None, int(d_sysctl["open_file"]))

        # From user count
        self.notify_value_n("k.os.users.connected", None, n_users)

    @classmethod
    def get_load_avg(cls):
        """
        Get load average
        :return: tuple 1,5,15 min
        :rtype tuple
        """

        try:
            from os import getloadavg
            return getloadavg()
        except ImportError:
            # some systems don't provide getloadavg, try reading /proc/loadavg directly as fallback
            with open("/proc/loadavg") as f1:
                buf = f1.read()
            return cls.get_load_avg_from_buffer(buf)

    @classmethod
    def get_load_avg_from_buffer(cls, buf):
        """
        Get load avg from buffer
        :return: tuple 1,5,15 min
        :rtype tuple
        """
        loadavg = buf.split()
        return map(float, loadavg[:3])

    @classmethod
    def get_sysctl(cls):
        """
        Get sysctl infos
        :return: dict
        :rtype dict
        """
        with open("/proc/sys/fs/file-max") as f1:
            with open("/proc/sys/kernel/pid_max") as f2:
                with open("/proc/sys/fs/file-nr") as f3:
                    return cls.get_sys_ctl_from_buffer(f1.read(), f2.read(), f3.read())

    @classmethod
    def get_sys_ctl_from_buffer(cls, buf_file_max, buf_pid_max, buf_file_nr):
        """
        Get sysctl from buffer
        :param buf_file_max: str
        :type buf_file_max: str
        :param buf_pid_max: str
        :type buf_pid_max: str
        :param buf_file_nr: str
        :type buf_file_nr: str
        :return: dict
        :rtype dict
        """
        result = dict()
        result["max_open_files"] = buf_file_max.strip()
        result["max_proc"] = buf_pid_max.strip()
        result["open_file"] = buf_file_nr.strip().split()[0]
        return result

    @classmethod
    def get_tick(cls):
        """
        Get tick
        :return: float
        :rtype float
        """
        return 1.0 / os.sysconf(os.sysconf_names["SC_CLK_TCK"])

    @classmethod
    def get_cpu_stats_from_buffer(cls, buf_proc_stat):
        """
        Get cpu from buffer
        :param buf_proc_stat: str
        :type buf_proc_stat: str
        :return: dict
        :rtype dict
        """

        tick = cls.get_tick()
        ar = buf_proc_stat.split("\n")
        cpu = dict()

        try:
            # kernel 3
            cpu["name"], cpu["user"], cpu["nice"], cpu["system"], cpu["idle"], cpu["iowait"], cpu["interrupt"], cpu["softirq"], cpu["steal"], cpu["guest"], unused = ar[0].replace("  ", " ").split(" ", 10)
        except ValueError:
            # kernel 2.6
            cpu["name"], cpu["user"], cpu["nice"], cpu["system"], cpu["idle"], cpu["iowait"], cpu["interrupt"], cpu["softirq"], unused = ar[0].replace("  ", " ").split(" ", 8)
            cpu["guest"] = 0
            cpu["steal"] = 0

        cpu["total"] = 0
        total = 0
        for key, value in cpu.items():
            try:
                int_value = int(value)
                cpu[key] = int_value
                total += int_value
            except ValueError:
                pass

        cpu["total"] = total * tick
        for line in ar:
            if line.startswith("ctxt"):
                cpu["ctxt"] = line.split()[1]
            elif line.startswith("softirq"):
                cpu["softirqcount"] = line.split()[1]
            elif line.startswith("btime"):
                cpu["btime"] = line.split()[1]
            elif line.startswith("procs_running"):
                cpu["proc_running"] = line.split()[1]

        return cpu

    @classmethod
    def get_cpu_stats(cls):
        """
        Get cpu
        :return: dict
        :rtype dict
        """
        with open("/proc/stat") as f1:
            return cls.get_cpu_stats_from_buffer(f1.read())

    def _linux_set_cpu_count(self):
        """
        Number of virtual or physical CPUs on this system, i.e.
        user/real as output by time(1) when called with an optimally scaling
        userspace-only program
        """

        # If done, exit
        if self._cpu_count:
            return
        self._cpu_count = self.get_cpu_count()

    @classmethod
    def get_cpu_count(cls):
        """
        Get cpu count
        :return int
        :rtype int
        """

        # Python 2.6+
        try:
            import multiprocessing

            return multiprocessing.cpu_count()
        except (ImportError, NotImplementedError):
            pass

        # POSIX
        try:
            # noinspection PyUnresolvedReferences
            res = int(os.sysconf("SC_NPROCESSORS_ONLN"))

            if res > 0:
                return res
        except (AttributeError, ValueError):
            pass

        # Windows
        try:
            res = int(os.environ["NUMBER_OF_PROCESSORS"])

            if res > 0:
                return res
        except (KeyError, ValueError):
            pass

        # BSD
        try:
            ec, so, se = ButcherTools.invoke("sysctl -n hw.ncpu")
            # sysctl = subprocess.Popen(["sysctl", "-n", "hw.ncpu"], stdout=subprocess.PIPE)
            # sc_stdout = sysctl.communicate()[0]
            if ec != 0:
                logger.warning("ex=%s, so=%s, se=%s", ec, so, se)
                pass

            sc_stdout = so
            res = int(sc_stdout)

            if res > 0:
                return res
        except (OSError, ValueError):
            pass

        # Linux
        try:
            with open("/proc/cpuinfo") as f1:
                buf = f1.read()
            return cls.get_cpu_count_from_buffer(buf)
        except IOError:
            pass

        # Other UNIXes (heuristic)
        try:
            dmesg = None
            try:
                dmesg = open("/var/run/dmesg.boot").read()
            except IOError:
                ec, so, se = ButcherTools.invoke("dmesg")
                if ec != 0:
                    logger.warning("ex=%s, so=%s, se=%s", ec, so, se)
                else:
                    dmesg = so

            res = 0
            while "\ncpu" + str(res) + ":" in dmesg:
                res += 1

            if res > 0:
                return res
        except OSError:
            pass

        raise Exception("Can not determine number of CPUs on this system")

    @classmethod
    def get_cpu_count_from_buffer(cls, buf):
        """
        Get cpu count from buffer
        :param buf: str
        :type buf: str
        :return: int
        :rtype int
        """

        res = buf.count("processor       :")
        if res == 0:
            res = buf.count("processor\t:")
        if res == 0:
            res = buf.count("processor:")
        if res == 0:
            res = buf.count("processor")
        if res == 0:
            return 1
        else:
            return res

    @classmethod
    def get_users_count(cls):
        """
        Get
        :return:
        """

        # number = os.popen('users|wc -w').read().strip()

        # Do not support pipe at this stage (http://stackoverflow.com/questions/13332268/python-subprocess-command-with-pipe)

        ec, so, se = ButcherTools.invoke("users")
        if ec != 0:
            logger.warning("ex=%s, so=%s, se=%s", ec, so, se)
        else:
            return cls.get_users_count_from_buffer(so.decode("utf8"))

    @classmethod
    def get_users_count_from_buffer(cls, buf):
        """
        Get user count from buffer
        :param buf: str
        :type buf: str
        :return: int
        :rtype int
        """

        buf = buf.strip()
        if len(buf) > 0:
            return len(buf.split(" "))
        else:
            return 0

    @classmethod
    def process_ar_queue(cls, ar, ms_current):
        """
        Process ar queue
        :param ar: list of dict(ms, q)
        :type ar: list
        :param ms_current: current ms
        :type ms_current: float
        :return tuple queue len 1min, 5min, 15min
        :rtype tuple
        """

        ms_15_min = 15 * 60 * 1000
        ms_5_min = 5 * 60 * 1000
        ms_1_min = 1 * 60 * 1000

        # No data?
        if len(ar) == 0:
            return 0, 0, 0

        # ----------------------------------
        # Evict all items older than 15 min
        # ----------------------------------
        ar_ok = list()
        for d in ar:
            # Evict
            if SolBase.msdiff(d["ms"], ms_current) > ms_15_min:
                # Kick it
                continue
            else:
                # Keep it
                ar_ok.append(d)

        # Re-init
        del ar[:]
        ar.extend(ar_ok)

        # Compute avg15
        c_15 = 0
        sm_15 = 0
        c_5 = 0
        sm_5 = 0
        c_1 = 0
        sm_1 = 0
        for d in ar:
            if SolBase.msdiff(d["ms"], ms_current) <= ms_15_min:
                c_15 += 1
                sm_15 += d["q"]
            if SolBase.msdiff(d["ms"], ms_current) <= ms_5_min:
                c_5 += 1
                sm_5 += d["q"]
            if SolBase.msdiff(d["ms"], ms_current) <= ms_1_min:
                c_1 += 1
                sm_1 += d["q"]

        # Fix stuff
        if c_1 == 0:
            c_1 = 1
            sm_1 = ar[-1]["q"]
        if c_5 == 0:
            c_5 = 1
            sm_5 = ar[-1]["q"]
        if c_15 == 0:
            c_15 = 1
            sm_15 = ar[-1]["q"]

        # Compute
        logger.info(
            "Got (%s/%s), (%s/%s), (%s/%s)",
            sm_1, c_1,
            sm_5, c_5,
            sm_15, c_15
        )
        avg_1 = float(sm_1) / float(c_1)
        avg_5 = float(sm_5) / float(c_15)
        avg_15 = float(sm_15) / float(c_15)

        # Over
        logger.info(
            "Got avg1=%.2f (%s/%s), avg5=%.2f (%s/%s), avg15=%.2f (%s/%s)",
            avg_1, sm_1, c_1,
            avg_5, sm_5, c_5,
            avg_15, sm_15, c_15,
        )
        return avg_1, avg_5, avg_15
