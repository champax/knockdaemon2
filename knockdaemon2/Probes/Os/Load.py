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
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)

if PTools.get_distribution_type() == "windows":
    pass

try:
    from os import getloadavg
except ImportError:
    # some systems don't provide getloadavg, try reading /proc/loadavg directly as fallback
    LOADAVG_PATH = '/proc/loadavg'


    def getloadavg():
        """
        Doc
        """
        loadavg_file = open(LOADAVG_PATH)
        content = loadavg_file.read()
        loadavg = content.split()
        loadavg_file.close()
        return map(float, loadavg[:3])


class Load(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        # Init
        self._cpu_count = None
        self._ar_proc_qlen = list()
        self._last_run_ms = SolBase.mscurrent()
        self._d_accu = None

        self.category = "/os/load"

    def _execute_linux(self):
        """
        Exec
        """

        # Set cpu count if needed
        self._linux_set_cpu_count()

        # Go

        cpu_count = self._cpu_count
        load1, load5, load15 = getloadavg()
        self.notify_value_n("k.os.cpu.load.percpu.avg1", None, load1 / cpu_count)
        self.notify_value_n("k.os.cpu.load.percpu.avg5", None, load5 / cpu_count)
        self.notify_value_n("k.os.cpu.load.percpu.avg15", None, load15 / cpu_count)
        self.notify_value_n("k.os.cpu.core", None, cpu_count)

        cpu = self.get_stat()

        for key, value in cpu.items():
            if isinstance(value, (int, float)):
                if key not in "total,guest":
                    if value < 0:
                        value = 0
                    self.notify_value_n("k.os.cpu.util." + key, None, value / cpu_count)

        self.notify_value_n("k.os.cpu.switches", None, int(cpu["ctxt"]))
        self.notify_value_n("k.os.cpu.intr", None, int(cpu["softirqcount"]))
        self.notify_value_n("k.os.boottime", None, int(cpu["btime"]))
        self.notify_value_n("k.os.processes.running", None, int(cpu["proc_running"]))

        self.notify_value_n("k.os.hostname", None, os.uname()[1])
        self.notify_value_n("k.os.localtime", None, int(time.time()))

        sysctl = self.get_sysctl()
        self.notify_value_n("k.os.maxfiles", None, int(sysctl["max_open_files"]))
        self.notify_value_n("k.os.maxproc", None, int(sysctl["max_proc"]))
        self.notify_value_n("k.os.openfiles", None, int(sysctl["open_file"]))
        self.notify_value_n("k.os.users.connected", None, self.get_users_count())

    # noinspection PyMethodMayBeStatic
    def get_sysctl(self):
        """
        Get
        :return:
        """
        result = dict()
        result["max_open_files"] = open("/proc/sys/fs/file-max").read().strip()
        result["max_proc"] = open("/proc/sys/kernel/pid_max").read().strip()
        result["open_file"] = open("/proc/sys/fs/file-nr").read().strip().split()[0]

        return result

    # noinspection PyMethodMayBeStatic
    def get_stat(self):
        """
        Get
        :return:
        """
        # noinspection PyUnresolvedReferences
        tick = 1.0 / os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        cpu = dict()
        lines = open("/proc/stat").read().splitlines()

        try:
            # kernel 3
            cpu["name"], cpu["user"], cpu["nice"], cpu["system"], cpu["idle"], cpu["iowait"], cpu["interrupt"], cpu["softirq"], cpu["steal"], cpu["guest"], unused = lines[0].replace("  ", " ").split(" ", 10)
        except ValueError:
            # kernel 2.6
            cpu["name"], cpu["user"], cpu["nice"], cpu["system"], cpu["idle"], cpu["iowait"], cpu["interrupt"], cpu["softirq"], unused = lines[0].replace("  ", " ").split(" ", 8)
            cpu["guest"] = 0
            cpu["steal"] = 0

        cpu["total"] = 0
        total = 0
        for key, value in cpu.items():
            # noinspection PyBroadException
            try:
                int_value = int(value)
                cpu[key] = int_value
                total += int_value
            except Exception:
                pass

        cpu["total"] = total * tick
        for line in lines:
            if line.startswith("ctxt"):
                cpu["ctxt"] = line.split()[1]
            elif line.startswith("softirq"):
                cpu["softirqcount"] = line.split()[1]
            elif line.startswith("btime"):
                cpu["btime"] = line.split()[1]
            elif line.startswith("procs_running"):
                cpu["proc_running"] = line.split()[1]

        return cpu

    def _linux_set_cpu_count(self):
        """
        Number of virtual or physical CPUs on this system, i.e.
        user/real as output by time(1) when called with an optimally scaling
        userspace-only program
        """

        # If done, exit
        if self._cpu_count:
            return
        self._cpu_count = self._linux_get_cpu_count_internal()

    # noinspection PyMethodMayBeStatic
    def _linux_get_cpu_count_internal(self):
        """
        Internal method
        :return int
        :rtype int
        """

        # Python 2.6+
        try:
            import multiprocessing

            return multiprocessing.cpu_count()
        except (ImportError, NotImplementedError):
            pass

        # TODO : unittest : split in methods

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
            res = open("/proc/cpuinfo").read().count("processor\t:")

            if res > 0:
                return res
        except IOError:
            pass

        # Other UNIXes (heuristic)
        try:
            dmesg = None
            try:
                dmesg = open("/var/run/dmesg.boot").read()
            except IOError:
                # dmesg_process = subprocess.Popen(["dmesg"], stdout=subprocess.PIPE)
                # dmesg = dmesg_process.communicate()[0]
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

    # noinspection PyMethodMayBeStatic
    def get_users_count(self):
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
            buf = so.strip()
            if len(buf) > 0:
                number = len(buf.split(' '))
            else:
                number = 0
            return number

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
