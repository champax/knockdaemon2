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
import time
from datetime import datetime

import os
import pytz
from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)

if PTools.get_distribution_type() == "windows":
    from knockdaemon2.Windows.Wmi.Wmi import Wmi

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
            if isinstance(value, (long, int, float)):
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
                logger.warn("ex=%s, so=%s, se=%s", ec, so, se)
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
                    logger.warn("ex=%s, so=%s, se=%s", ec, so, se)
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
            logger.warn("ex=%s, so=%s, se=%s", ec, so, se)
        else:
            buf = so.strip()
            if len(buf) > 0:
                number = len(buf.split(' '))
            else:
                number = 0
            return number

    # =======================================
    # Windows support
    # =======================================

    def _windows_set_cpu_count(self, d):
        """
        Set total number of cores present accross all cpus (HT cores not included) inside _cpu_count
        :param d: wmi dict
        :type d: dict
        """

        # If done, exit
        if self._cpu_count:
            return

        # We target :
        # Win32_Processor :: CPUx => NumberOfCores => 4
        # Note : For a 2 core HT : NumberOfCores is 2 and NumberOfLogicalProcessors is 4, we use NumberOfCores (real cpu cores)
        total_core_count = 0

        # Browse all physical CPU
        for cpu_props in d["Win32_Processor"]:
            # Get cores
            core_count = int(cpu_props["NumberOfCores"])
            name = cpu_props["Name"]
            logger.info("Got cores=%s, name=%s", core_count, name)
            # Sum
            total_core_count += core_count

        # Ok
        self._cpu_count = total_core_count
        logger.info("Detected total_core_count=%s, assigned to _cpu_count", total_core_count)

    # noinspection PyMethodMayBeStatic
    def _get_raw_proc_perf(self, d_wmi):
        """
        Get perf dict
        :param d_wmi dict
        :type d_wmi dict
        :return dict
        :rtype dict
        """

        for d in d_wmi["Win32_PerfRawData_PerfOS_Processor"]:
            if "_total" == d["Name"].lower():
                return d
        return None

    def _execute_windows(self):
        """
        Exec
        """

        d = None
        try:
            # We NEED recent data for RAW perf. This call is blocking.
            Wmi.ensure_recent("Win32_PerfRawData_PerfOS_System")
            Wmi.ensure_recent("Win32_PerfRawData_PerfOS_Processor")

            # Get datas
            d, age_ms = Wmi.wmi_get_dict()
            logger.info("Using wmi with age_ms=%s", age_ms)

            # Set cpu count (if needed)
            self._windows_set_cpu_count(d)

            # -------------------------
            # Ok, load...
            # -------------------------

            d_proc_perf_raw = self._get_raw_proc_perf(d_wmi=d)
            assert d_proc_perf_raw, "d_proc_perf_raw must be set"

            # This is not available on windows
            # We use ProcessorQueueLength
            queue_len = int(d["Win32_PerfFormattedData_PerfOS_System"]["ProcessorQueueLength"])
            logger.info("Got queue_len=%s", queue_len)

            # This is instant value, we need to store history
            # We should retain queue_len each second, but its too heavy, so we retain each run in array
            self._ar_proc_qlen.append({"ms": SolBase.mscurrent(), "q": queue_len})
            load1, load5, load15 = Load.process_ar_queue(self._ar_proc_qlen, SolBase.mscurrent())
            logger.info("Got _ar_proc_qlen len=%s, q=%s", len(self._ar_proc_qlen), self._ar_proc_qlen)
            logger.info("Got raw load1=%.2f, load5=%.2f, load15=%.2f", load1, load5, load15)

            # Normalize
            load1 /= float(self._cpu_count)
            load5 /= float(self._cpu_count)
            load15 /= float(self._cpu_count)
            logger.info("Got nor load1=%.2f, load5=%.2f, load15=%.2f, cpu_count=%s", load1, load5, load15, self._cpu_count)

            # Notify
            self.notify_value_n("k.os.cpu.load.percpu.avg1", None, load1)
            self.notify_value_n("k.os.cpu.load.percpu.avg5", None, load5)
            self.notify_value_n("k.os.cpu.load.percpu.avg15", None, load15)
            self.notify_value_n("k.os.cpu.core", None, self._cpu_count)

            # =========================================
            # Ok, cpu usages...
            # =========================================

            d_cpu = dict()

            # We need :
            # 'k.os.boottime' 1467005981
            # 'k.os.hostname' 'klchgui01'
            # 'k.os.localtime' 1489434351
            # 'k.os.cpu.util[,softirq]' 113763      # cumulative, / cpu_count
            # 'k.os.cpu.util[,iowait]' 8874729      # cumulative, / cpu_count
            # 'k.os.cpu.util[,system]' 14525502     # cumulative, / cpu_count
            # 'k.os.cpu.util[,idle]' 2142535263     # cumulative, / cpu_count
            # 'k.os.cpu.util[,user]' 43317681       # cumulative, / cpu_count
            # 'k.os.cpu.util[,interrupt]' 1373      # cumulative, / cpu_count
            # 'k.os.cpu.util[,steal]' 2401629       # cumulative, / cpu_count
            # 'k.os.cpu.util[,nice]' 2035           # cumulative, / cpu_count
            # 'k.os.cpu.switches' 96431364224       # cumulative, Context switches (sum)
            # 'k.os.cpu.intr' 9180015588            # cumulative, Interrupts (sum)

            # 'k.os.processes.total[,,run]' 3           # Running process count (cur)
            # 'k.os.maxfiles' '1048576'             # Max open files (cur)
            # 'k.os.maxproc' '131072'               # Max process count (cur)
            # 'k.os.users.connected' 1                    # Connected users (cur)

            # ----------------------
            # Boot time and local time
            # The "btime" line gives the time at which the system booted, in seconds since the Unix epoch.
            # We don't support that in windows (moreover we don't use that)
            # ----------------------

            # Get
            boot_time = d["Win32_OperatingSystem"]["LastBootUpTime"]
            logger.info("Got type=%s, boot_time=%s", type(boot_time), boot_time)

            # Format is yyyyMMddhhmmss.ffffff+zzz
            # We need to compute seconds elapsed since this date, so we need a date, utc naive
            dt_boot_utc = Load.parse_time(boot_time)
            elapsed_boot_sec = (SolBase.datediff(dt_boot_utc) / 1000)
            logger.info("Got dt_boot_utc=%s, elapsed_boot_sec=%s", dt_boot_utc, elapsed_boot_sec)
            d_cpu["k.os.boottime"] = elapsed_boot_sec

            # Local time : direct
            d_cpu["k.os.localtime"] = int(time.time())

            # ----------------------
            # Hostname
            # ----------------------
            d_cpu["k.os.hostname"] = SolBase.get_machine_name()

            # ----------------------
            # Cpu stuff
            # ----------------------

            # CAUTION :
            # - We handle ALL stuff as cumulative values
            # - Windows returning stuff as immediate values
            # - Server handle stuff as delta per second
            # SO :
            # We use RAW datas from Win32_PerfRawData_PerfOS_Processor

            # Example :
            # sec 0         50% cpu                         => server receive 50       = 50 (no previous value, we store it raw)
            # sec 60        50% cpu,    60s * 50% = 30      => server receive 50 + 30  = 80      => server delta = 30        => for 60 sec : 30 / 60 = 50%
            # sec 120       50% cpu,    60s * 50% = 30      => server receive 80 + 30  = 110     => server delta = 30        => for 60 sec : 30 / 60 = 50%
            # sec 180       100% cpu,   60s * 100% = 30     => server receive 110 + 60 = 170     => server delta = 60        => for 60 sec : 60 / 60 = 100%

            # 'k.os.cpu.util[,softirq]' 113763      # cumulative, / cpu_count
            # 'k.os.cpu.util[,iowait]' 8874729      # cumulative, / cpu_count
            # 'k.os.cpu.util[,system]' 14525502     # cumulative, / cpu_count
            # 'k.os.cpu.util[,idle]' 2142535263     # cumulative, / cpu_count
            # 'k.os.cpu.util[,user]' 43317681       # cumulative, / cpu_count
            # 'k.os.cpu.util[,interrupt]' 1373      # cumulative, / cpu_count
            # 'k.os.cpu.util[,steal]' 2401629       # cumulative, / cpu_count
            # 'k.os.cpu.util[,nice]' 2035           # cumulative, / cpu_count
            # 'k.os.cpu.switches' 96431364224       # cumulative, Context switches (sum)
            # 'k.os.cpu.intr' 9180015588            # cumulative, Interrupts (sum)

            # Fetch raw values
            d_cur_val = dict()
            for k_key, w_d, w_key in [
                # We map PercentDPCTime
                ["k.os.cpu.util[,softirq]", d_proc_perf_raw, "PercentDPCTime"],
                # Must remove PercentDPCTime and interrupts from this one, since they are INCLUDED inside(yeaaaaaah guys GG)
                ["k.os.cpu.util[,system]", d_proc_perf_raw, "PercentPrivilegedTime"],
                ["k.os.cpu.util[,idle]", d_proc_perf_raw, "PercentIdleTime"],
                ["k.os.cpu.util[,user]", d_proc_perf_raw, "PercentUserTime"],
                ["k.os.cpu.util[,interrupt]", d_proc_perf_raw, "PercentInterruptTime"],
                # Will be zero (not supported)
                ["k.os.cpu.util[,steal]", None, None],
                ["k.os.cpu.util[,iowait]", None, None],
                ["k.os.cpu.util[,nice]", None, None],
                # Int/Switches
                ["k.os.cpu.switches", d["Win32_PerfRawData_PerfOS_System"], "ContextSwitchesPersec"],
                ["k.os.cpu.intr", d_proc_perf_raw, "InterruptsPersec"],
            ]:
                # FETCH (or set)
                if w_key:
                    d_cur_val[k_key] = float(w_d[w_key])
                else:
                    d_cur_val[k_key] = 0.0

            # Fix "k.os.cpu.util[,system]" : "k.os.cpu.util[,softirq]" and  interrupt
            d_cur_val["k.os.cpu.util[,system]"] -= d_cur_val["k.os.cpu.util[,softirq]"]
            d_cur_val["k.os.cpu.util[,system]"] -= d_cur_val["k.os.cpu.util[,interrupt]"]

            # For check only
            raw_cpu_usage = float(d_proc_perf_raw["PercentProcessorTime"])

            # Logs
            logger.info("Got dir %s=%s", "raw_cpu_usage".ljust(48), str(int(raw_cpu_usage)).rjust(20))
            chk_sum = 0.0
            for k, v in d_cur_val.iteritems():
                logger.info("Got raw %s=%s", k.ljust(48), str(int(v)).rjust(20))
                chk_sum += v
            logger.info("Got chk %s=%s", "chk_cpu_usage".ljust(48), str(int(chk_sum)).rjust(20))
            logger.info("Got chk %s=%s", "chk_diff".ljust(48), str(int(raw_cpu_usage - chk_sum)).rjust(20))

            # For cpu we need precision, so get the timestamp
            ts_100 = float(d_proc_perf_raw["Timestamp_Sys100NS"])
            logger.info("Got ts_100=%s", ts_100)
            ts_epoch = Wmi.get_sec_epoch_from_ns(ts_100)
            logger.info("Got ts_epoch=%s", ts_epoch)

            # Raw values are cumulative 100NS-ticks, divide by 10000 to get ms
            # Linux values are usually hundredths of a second, so divide again by 10 to get 1/100 sec (we are % based at server end)
            # And we DO NOT normalize by cpu count since we are already targeting total
            for k, v in d_cur_val.iteritems():
                # Do not do it for these one
                if k in ["k.os.cpu.intr"]:
                    continue
                elif k in ["k.os.cpu.switches"]:
                    # Here, we have uint32, which is mapped by pywin32 to int, which can become negative (???)
                    # If it is negative : uint32 max minus our value
                    if v < 0:
                        d_cur_val[k] = Wmi.fix_uint32_max(v)
                else:
                    # Got to ms (1/1000)
                    ms = float(v) / 10000.0
                    # Got to 1/100
                    cms = float(ms) / 10.0
                    # Normalize
                    # nms = float(cms) / float(self._cpu_count)
                    # Update
                    d_cur_val[k] = cms

            for k, v in d_cur_val.iteritems():
                logger.info("Got fin %s=%s", k.ljust(48), str(int(v)).rjust(20))

            # Merge
            d_cpu.update(d_cur_val)

            # ===========================
            # RUNNING PROCESSES / CONNECTED USERS
            # Runnign threads => We browse Win32_Thread and check ThreadState running (2)
            # Connected users (cur) => Win32_LogonSession, LogonType == 10
            # ===========================

            d_cpu["k.os.processes.total[,,run]"] = d["WQL_RunningThreadCount"]
            d_cpu["k.os.users.connected"] = d["WQL_ConnectedUsers"]

            # ===========================
            # MISC
            # 'k.os.maxfiles' '1048576'             # Max open files (cur) => BYPASS
            # 'k.os.maxproc' '131072'               # Max process count (cur) => BYPASS
            # ===========================

            # Roughly
            d_cpu["k.os.maxfiles"] = 16711680
            d_cpu["k.os.maxproc"] = 16711680

            # Notify all
            for k, v in d_cpu.iteritems():
                # For k.os.cpu.util : push precise
                if k.startswith("k.os.cpu.util"):
                    self.notify_value_n(k, None, v, ts_epoch)
                else:
                    self.notify_value_n(k, None, v)

        except Exception as e:
            logger.warn("Exception while processing, ex=%s, d=%s", SolBase.extostr(e), d)

    @classmethod
    def parse_time(cls, st):
        """
        Parse date time string (20170312044209.003363-420)
        :param st: unicode,str as 20170312044209.003363-420
        :type st: unicode,str
        :return datetime (naive, utc)
        :rtype datetime
        """

        year = int(st[0:4])
        month = int(st[4:6])
        day = int(st[6:8])
        hh = int(st[8:10])
        mm = int(st[10:12])
        ss = int(st[12:14])
        ms = int(st[15:21])
        tz = st[21:]
        if len(tz) > 0:
            tz = int(tz)
        else:
            tz = 0

        # Timezone aware date
        # noinspection PyArgumentList
        dt = datetime(year=year, month=month, day=day, hour=hh, minute=mm, second=ss, microsecond=ms, tzinfo=pytz.FixedOffset(tz))
        logger.info("Got a.dt=%s", dt)

        # Add (if naive) or move (if aware) to UTC
        if not dt.tzinfo:
            # If naive, add utc
            dt = dt.replace(tzinfo=pytz.utc)
        else:
            # Not naive, go utc, keep aware
            dt = dt.astimezone(pytz.utc)
        logger.info("Got b.dt=%s", dt)

        # Move from aware to naive
        dt = dt.replace(tzinfo=None)
        logger.info("Got c.dt=%s", dt)

        return dt

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
