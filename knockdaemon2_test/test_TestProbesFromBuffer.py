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

# MONKEY ASAP
from pysolbase.SolBase import SolBase

SolBase.voodoo_init()

import re
import dateutil.parser
import ujson
import logging
import os
import shutil
import sys
import unittest
from os.path import dirname, abspath

import distro
import psutil
from dns.resolver import Resolver
from pysolbase.FileUtility import FileUtility
from pysolmeters.Meters import Meters

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Probes.Apache.ApacheStat import ApacheStat
from knockdaemon2.Probes.Haproxy.Haproxy import Haproxy
from knockdaemon2.Probes.Inventory.Inventory import Inventory
from knockdaemon2.Probes.Mongodb.MongoDbStat import MongoDbStat
from knockdaemon2.Probes.Mysql.Mysql import Mysql
from knockdaemon2.Probes.Nginx.NGinxStat import NginxStat
from knockdaemon2.Probes.Os.CheckDns import CheckDns
from knockdaemon2.Probes.Os.CheckProcess import CheckProcess
from knockdaemon2.Probes.Os.DiskSpace import DiskSpace
from knockdaemon2.Probes.Os.HddStatus import HddStatus
from knockdaemon2.Probes.Os.IpvsAdm import IpvsAdm
from knockdaemon2.Probes.Os.Load import Load
from knockdaemon2.Probes.Os.Mdstat import Mdstat
from knockdaemon2.Probes.Os.Memory import Memory
from knockdaemon2.Probes.Os.NetStat import Netstat
from knockdaemon2.Probes.Os.Network import Network
from knockdaemon2.Probes.Os.ProcNum import NumberOfProcesses
from knockdaemon2.Probes.Os.Service import Service
from knockdaemon2.Probes.Os.TimeDiff import TimeDiff
from knockdaemon2.Probes.Os.UpTime import Uptime
from knockdaemon2.Probes.Rabbitmq.RabbitmqStat import RabbitmqStat
from knockdaemon2.Probes.Redis.RedisStat import RedisStat
from knockdaemon2.Probes.Uwsgi.UwsgiStat import UwsgiStat
from knockdaemon2.Probes.Varnish.VarnishStat import VarnishStat
from knockdaemon2.Tests.TestHelpers import exec_helper
from knockdaemon2.Tests.TestHelpers import expect_value

logger = logging.getLogger(__name__)


class TestProbesFromBuffer(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.config_file = self.current_dir + "conf" + SolBase.get_pathseparator() + "realall" + SolBase.get_pathseparator() + "knockdaemon2.yaml"

        self.sample_dir = self.current_dir + "../z_docs/samples/"
        self.assertTrue(FileUtility.is_dir_exist(self.sample_dir))

        # Config files
        for f in [
            "k.CheckProcess.json",
            "k.CheckDns.json",
            "knockdaemon2.yaml",
            SolBase.get_pathseparator().join(["conf.d", "10_auth.yaml"])
        ]:
            src = self.current_dir + "conf" + SolBase.get_pathseparator() + "realall" + SolBase.get_pathseparator() + f
            dst = PTools.get_tmp_dir() + SolBase.get_pathseparator() + f

            dir_name = dirname(dst)
            if not FileUtility.is_dir_exist(dir_name):
                os.makedirs(dir_name)
            shutil.copyfile(src, dst)

            # Load
            buf = FileUtility.file_to_textbuffer(dst, "utf8")

            # Replace
            buf = buf.replace("/tmp", PTools.get_tmp_dir())

            # Write
            FileUtility.append_text_to_file(dst, buf, "utf8", overwrite=True)

        # Overwrite
        self.config_file = PTools.get_tmp_dir() + SolBase.get_pathseparator() + "knockdaemon2.yaml"

        # Reset meter
        Meters.reset()

        # Allocate, do not start
        self.k = KnockManager(self.config_file, auto_start=False)

        # Debug stat on exit ?
        self.debug_stat = False
        self.optional_key = list()

        # Overide parameter in probe to mock
        self.conf_probe_override = dict()

    def tearDown(self):
        """
        Setup (called after each test)
        """

        if self.debug_stat:
            Meters.write_to_logger()

    def test_from_buffer_nginx(self):
        """
        Test
        """

        # Init
        ap = NginxStat()
        ap.set_manager(self.k)

        # Go
        for fn in [
            "nginx/nginx.out",
        ]:
            # Path
            fn = self.sample_dir + fn

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Load
            self.assertTrue(FileUtility.is_file_exist(fn))
            buf = FileUtility.file_to_binary(fn)

            # Process
            ap.process_nginx_buffer(nginx_buf=buf, pool_id="default", ms_http=11)

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Validate results - data
            dd = {"ID": "default"}
            expect_value(self, self.k, "k.nginx.started", 1, "eq", dd)
            expect_value(self, self.k, "k.nginx.reading", 0, "gte", dd)
            expect_value(self, self.k, "k.nginx.writing", 0, "gte", dd)
            expect_value(self, self.k, "k.nginx.connections", 0, "gte", dd)
            expect_value(self, self.k, "k.nginx.waiting", 0, "gte", dd)
            expect_value(self, self.k, "k.nginx.requests", 1, "gte", dd)
            expect_value(self, self.k, "k.nginx.accepted", 1, "gte", dd)

    @unittest.skipIf(SolBase.get_machine_name() == 'admin01', 'Not compatible jessie')
    @unittest.skipIf(Service().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Service())
    @unittest.skip("TODO : Re-enable later")
    def test_Service(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, Service)

        # Validate results - disco

        expect_value(self, self.k, "k.os.service.running", 1, 'eq', {"SERVICE": "rsyslog"})
        expect_value(self, self.k, "k.os.service.running", 1, 'eq', {"SERVICE": "cron"})
        expect_value(self, self.k, "k.os.service.running_count", 2, 'eq', None)

    def test_uwsgi_get_type(self):
        """
        Test
        """

        ar = "/usr/bin/uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/toto.ini --daemonize /var/log/uwsgi/app/toto.log".split(" ")
        s_uwsgi = Service.uwsgi_get_type(ar)
        self.assertEquals(s_uwsgi, "uwsgi_default_toto")

        ar = "/usr/bin/uwsgi".split(" ")
        s_uwsgi = Service.uwsgi_get_type(ar)
        self.assertEquals(s_uwsgi, "uwsgi_na")

    def test_uwsgi_get_processes(self):
        """
        Test
        """

        d = Service.uwsgi_get_processes()
        for k, v in d.items():
            logger.info("Got %s=%s", k, v)
        self.assertIsNotNone(d)
        if len(d) > 0:
            for k, v in d.items():
                self.assertIsNotNone(k)
                self.assertIsNotNone(v)
                self.assertIsInstance(k, str)
                self.assertTrue(k.startswith("uwsgi_"))
                self.assertIsInstance(v, int)

    @unittest.skipIf(Service().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Service())
    def test_Mdstat(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, Mdstat)

        # Validate results - disco
        pass

    def test_from_buffer_haproxy(self):
        """
        Test
        """

        # Init
        hp = Haproxy()
        hp.set_manager(self.k)

        # Go
        for fn in [
            "haproxy/haproxy.out",
            "haproxy/haproxy.2.out",
        ]:
            logger.info("*** GO, fn=%s", fn)

            # Path
            fn = self.sample_dir + fn

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Load
            self.assertTrue(FileUtility.is_file_exist(fn))
            buf = FileUtility.file_to_binary(fn)

            # Process
            hp.process_haproxy_buffer(buf.decode("utf8"))

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Validate results
            dd = {"PROXY": "ALL"}

            # Validate results - data
            expect_value(self, self.k, "k.haproxy.started", 1, "eq", dd)
            expect_value(self, self.k, "k.haproxy.session_cur", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.session_limit", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.denied_req", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.denied_resp", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.err_req", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.err_conn", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.err_resp", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.hrsp_1xx", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.hrsp_2xx", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.hrsp_3xx", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.hrsp_4xx", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.hrsp_5xx", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.hrsp_other", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.avg_time_queue_ms", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.avg_time_connect_ms", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.avg_time_resp_ms", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.avg_time_session_ms", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.status_ok", 0.0, "gte", dd)
            expect_value(self, self.k, "k.haproxy.status_ko", 0.0, "gte", dd)

            # expect_value(self, self.k, "k.haproxy.backend", 0.0, "exists", {"PROXY": "nodes"})
            # expect_value(self, self.k, "k.haproxy.frontend", 0.0, "exists", {"PROXY": "localnodes"})

    @unittest.skipIf(CheckDns().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % CheckDns())
    def test_CheckDns(self):
        """
        Test
        """

        # Exec it

        exec_helper(self, CheckDns)
        ns = Resolver().nameservers[0]

        # Validate results - disco
        dd = {"HOST": "knock.center", "SERVER": ns}

        # Validate results - data
        expect_value(self, self.k, "k.dns.resolv", "198.27.81.204", "eq", dd)
        expect_value(self, self.k, "k.dns.time", 0, "gte", dd)

    @unittest.skipIf(TimeDiff().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % TimeDiff())
    def test_TimeDiff(self):
        """
        Test
        """

        # Exec it

        exec_helper(self, TimeDiff)

        expect_value(self, self.k, "k.os.timediff", 10, "lte", None, cast_to_float=True)

    @unittest.skipIf(Inventory().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Inventory())
    def test_Inventory(self):
        """
        Test
        """

        # Requires SUDO :
        # user ALL=(ALL:ALL) NOPASSWD: /usr/sbin/dmidecode

        # Prepare
        (sysname, nodename, kernel, version, machine) = os.uname()
        distribution = distro.id()
        dversion = distro.version()

        # Exec it
        exec_helper(self, Inventory)

        # Check
        expect_value(self, self.k, "k.inventory.os", "%s %s %s" % (sysname, distribution, dversion), "eq", cast_to_float=False)
        expect_value(self, self.k, "k.inventory.kernel", kernel, "eq")
        expect_value(self, self.k, "k.inventory.name", nodename, "eq")

        # Run dmidecode
        ec, so, si = ButcherTools.invoke("sudo dmidecode")
        if ec == 0 and so.find("sorry") == -1:
            logger.info("Assuming dmidecode OK")
            expect_value(self, self.k, "k.inventory.vendor", None, "exists")
            expect_value(self, self.k, "k.inventory.mem", None, "exists")
            expect_value(self, self.k, "k.inventory.system", None, "exists")
            expect_value(self, self.k, "k.inventory.chassis", None, "exists")
            expect_value(self, self.k, "k.inventory.serial", None, "exists")
            expect_value(self, self.k, "k.inventory.cpu", None, "exists")
        else:
            logger.info("Assuming dmidecode KO")

    @unittest.skipIf(HddStatus().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % HddStatus())
    def test_from_buffer_hdd_status(self):
        """
        Test
        """

        # Init
        us = HddStatus()
        us.set_manager(self.k)

        # Init
        us.init_all_hash()

        # Parse hdd list
        s = self.sample_dir + "hdd_status/all_hdd.txt"
        self.assertTrue(FileUtility.is_file_exist(s))
        buf = FileUtility.file_to_textbuffer(s, "utf8")
        ar_hdd = list(HddStatus.scan_all_hdd_buffer(buf))
        self.assertIsNotNone(ar_hdd)
        self.assertEqual(ar_hdd, ["/dev/sda"])

        # Parse hdd error
        us.process_smartctl_error_only_buffer("sda", "")
        us.process_smartctl_error_only_buffer("sdb", "got_errors")

        # Parse hdd full buffer
        for hdd in ["sda", "sdb"]:
            s = self.sample_dir + "hdd_status/%s.txt" % hdd
            self.assertTrue(FileUtility.is_file_exist(s))
            buf = FileUtility.file_to_textbuffer(s, "utf8")
            us.process_smartctl_full_buffer(hdd, buf)

        # Finish
        us.push_all_hash()

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check sda
        dd = {"HDD": "sda"}
        expect_value(self, self.k, "k.hard.hd.status", None, "exists", dd)
        expect_value(self, self.k, "k.hard.hd.user_capacity", 500107862016.0, "eq", dd)
        expect_value(self, self.k, "k.hard.hd.reallocated_sector_ct", 0, "eq", dd)
        expect_value(self, self.k, "k.hard.hd.serial_number", "WD-WCC1U0437567", "eq", dd)
        expect_value(self, self.k, "k.hard.hd.health", "KNOCKOK", "eq", dd)
        expect_value(self, self.k, "k.hard.hd.device_model", "WDC WD5000AZRX-00A8LB0", "eq", dd)

        # Check sdb
        dd = {"HDD": "sdb"}
        expect_value(self, self.k, "k.hard.hd.status", None, "exists", dd)
        expect_value(self, self.k, "k.hard.hd.user_capacity", 512110190592.0, "eq", dd)
        expect_value(self, self.k, "k.hard.hd.reallocated_sector_ct", 99, "eq", dd)
        expect_value(self, self.k, "k.hard.hd.serial_number", "982S107CT5ZQ", "eq", dd)
        expect_value(self, self.k, "k.hard.hd.total_lbas_written", 384582, "eq", dd)
        expect_value(self, self.k, "k.hard.hd.health", "got_errors", "eq", dd)
        expect_value(self, self.k, "k.hard.hd.device_model", "TOSHIBA KSG60ZMV512G M.2 2280 512GB", "eq", dd)

        # Check ALL
        dd = {"HDD": "ALL"}
        expect_value(self, self.k, "k.hard.hd.reallocated_sector_ct", 99, "eq", dd)

    @unittest.skipIf(Load().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Load())
    def test_from_buffer_load(self):
        """
        Test
        """

        # ----------------------------
        # VALIDATE TRICK
        # ----------------------------

        # Example :
        # sec 0         50% cpu                         => server receive 50       = 50 (no previous value, we store it raw)
        # sec 60        50% cpu,    60s * 50% = 30      => server receive 50 + 30  = 80      => server delta = 30        => for 60 sec : 30 / 60 = 50%
        # sec 120       50% cpu,    60s * 50% = 30      => server receive 80 + 30  = 110     => server delta = 30        => for 60 sec : 30 / 60 = 50%
        # sec 180       100% cpu,   60s * 100% = 30     => server receive 110 + 60 = 170     => server delta = 60        => for 60 sec : 60 / 60 = 100%

        self.assertEqual(KnockHelpers.trick_instant_value_to_cumulative(None, 50.0, 0.0), 50.0)
        self.assertEqual(KnockHelpers.trick_instant_value_to_cumulative(50.0, 50.0, 60.0), 80.0)
        self.assertEqual(KnockHelpers.trick_instant_value_to_cumulative(80.0, 50.0, 60.0), 110.0)
        self.assertEqual(KnockHelpers.trick_instant_value_to_cumulative(110.0, 100.0, 60.0), 170.0)

        v_max = sys.float_info.max
        v_prev = v_max - 100.0
        v_cur = 202.0
        self.assertEqual(KnockHelpers.trick_instant_value_to_cumulative(v_prev, v_cur, 100.0), 202.0)

        # ----------------------------
        # Exec it
        # ----------------------------

        # Init
        us = Load()
        us.set_manager(self.k)

        # Load files
        fd = dict()
        for fs in ["cpu_info.txt", "file-max.txt", "file-nr.txt", "pid_max.txt", "proc_stat.txt", "users.txt", "loadavg.txt"]:
            s = self.sample_dir + "load/%s" % fs
            self.assertTrue(FileUtility.is_file_exist(s))
            buf = FileUtility.file_to_textbuffer(s, "utf8")
            fd[fs] = buf

        # Load
        load1, load5, load15 = us.get_load_avg()
        self.assertIsNotNone(load1)
        self.assertIsNotNone(load5)
        self.assertIsNotNone(load15)
        self.assertGreaterEqual(load1, 0)
        self.assertGreaterEqual(load5, 0)
        self.assertGreaterEqual(load15, 0)

        # Load again (from buffer this time)
        load1, load5, load15 = us.get_load_avg_from_buffer(fd["loadavg.txt"])
        self.assertIsNotNone(load1)
        self.assertIsNotNone(load5)
        self.assertIsNotNone(load15)
        self.assertGreaterEqual(load1, 0)
        self.assertGreaterEqual(load5, 0)
        self.assertGreaterEqual(load15, 0)

        # Cpu count
        n_cpu = us.get_cpu_count()
        self.assertGreater(n_cpu, 1)

        # Cpu count again (from buffer this time)
        n_cpu = us.get_cpu_count_from_buffer(fd["cpu_info.txt"])
        self.assertEqual(n_cpu, 12)

        # Cpu
        d_cpu = us.get_cpu_stats_from_buffer(fd["proc_stat.txt"])

        # Sysctl
        d_sysctl = us.get_sys_ctl_from_buffer(fd["file-max.txt"], fd["pid_max.txt"], fd["file-nr.txt"])

        # Users
        n_users = us.get_users_count_from_buffer(fd["users.txt"])

        # Push
        us.process_parsed("zzz", 999, n_cpu, load1, load5, load15, d_cpu, d_sysctl, n_users)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.os.cpu.load.percpu.avg1", 0.19583333333333333, "eq")
        expect_value(self, self.k, "k.os.cpu.load.percpu.avg5", 0.1575, "eq")
        expect_value(self, self.k, "k.os.cpu.load.percpu.avg15", 0.14916666666666667, "eq")
        expect_value(self, self.k, "k.os.cpu.core", 12, "eq")
        expect_value(self, self.k, "k.os.cpu.util.softirq", 523697.75, "eq")
        expect_value(self, self.k, "k.os.cpu.util.iowait", 46485.333333333336, "eq")
        expect_value(self, self.k, "k.os.cpu.util.system", 737093.5, "eq")
        expect_value(self, self.k, "k.os.cpu.util.idle", 53666677.5, "eq")
        expect_value(self, self.k, "k.os.cpu.util.user", 3414344.6666666665, "eq")
        expect_value(self, self.k, "k.os.cpu.util.interrupt", 0.0, "eq")
        expect_value(self, self.k, "k.os.cpu.util.steal", 0.0, "eq")
        expect_value(self, self.k, "k.os.cpu.util.nice", 185.58333333333334, "eq")
        expect_value(self, self.k, "k.os.cpu.switches", 4943625465, "eq")
        expect_value(self, self.k, "k.os.cpu.intr", 2495152497, "eq")
        expect_value(self, self.k, "k.os.boottime", 1639501438, "eq")
        expect_value(self, self.k, "k.os.processes.running", 2, "eq")
        expect_value(self, self.k, "k.os.hostname", "zzz", "eq")
        expect_value(self, self.k, "k.os.localtime", 999, "eq")
        expect_value(self, self.k, "k.os.maxfiles", 1048576, "eq")
        expect_value(self, self.k, "k.os.openfiles", 19552, "eq")
        expect_value(self, self.k, "k.os.maxproc", 32768, "eq")
        expect_value(self, self.k, "k.os.users.connected", 4, "eq")

    def test_from_buffer_redis(self):
        """
        Test
        """

        # Init
        rs = RedisStat()
        rs.set_manager(self.k)

        # Go
        for fn in [
            "redis/redis.out",
        ]:
            # Path
            fn = self.sample_dir + fn

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Load
            self.assertTrue(FileUtility.is_file_exist(fn))
            buf = FileUtility.file_to_textbuffer(fn, "utf8")

            # Convert to dict
            d_info = dict()
            for s in buf.split("\n"):
                s = s.strip()
                if len(s) == 0:
                    continue
                elif s.startswith("#"):
                    continue
                ar = s.split(":", 2)
                k = ar[0]
                v = ar[1]

                # Special processing
                if k.startswith("db"):
                    d_v = dict()
                    for ss in v.split(","):
                        ss_ar = ss.split("=")
                        d_v[ss_ar[0]] = int(ss_ar[1])
                    v = d_v

                # Push
                d_info[k] = v

            # Process
            rs.process_redis_dict(d_info, 6379, 22)

            # Process aggregate
            rs.process_redis_aggregate()

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Validate KEYS
            for cur_port in ["6379", "ALL"]:
                for _, knock_type, knock_key, _ in RedisStat.KEYS:
                    dd = {"RDPORT": cur_port}
                    if knock_type == "int":
                        expect_value(self, self.k, knock_key, -1, "gte", dd)
                    elif knock_type == "float":
                        expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                    elif knock_type == "str":
                        expect_value(self, self.k, knock_key, 0, "exists", dd)

    @unittest.skipIf(DiskSpace().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % DiskSpace())
    def test_DiskSpace(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, DiskSpace)
        SolBase.sleep(1000)
        exec_helper(self, DiskSpace)
        ar = ["/", "ALL"]

        for cur_p in ar:
            dd = {"FSNAME": cur_p}
            expect_value(self, self.k, "k.vfs.fs.size.free", 1, "gte", dd)

            expect_value(self, self.k, "k.vfs.fs.size.pfree", 0.0, "gte", dd)
            expect_value(self, self.k, "k.vfs.fs.size.pfree", 101.0, "lte", dd)

            expect_value(self, self.k, "k.vfs.fs.inode.pfree", 0.0, "gte", dd)
            expect_value(self, self.k, "k.vfs.fs.inode.pfree", 101.0, "lte", dd)

            expect_value(self, self.k, "k.vfs.fs.size.total", 1, "gte", dd)
            expect_value(self, self.k, "k.vfs.fs.size.used", 1, "gte", dd)

            expect_value(self, self.k, "k.vfs.dev.read.totalcount", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalsectorcount", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalbytes", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalms", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalcount", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalsectorcount", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalbytes", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalms", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.io.currentcount", 0, "gte", dd)
            expect_value(self, self.k, "k.vfs.dev.io.totalms", 0, "gte", dd)

    @unittest.skipIf(IpvsAdm().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % IpvsAdm())
    def test_IpvsAdm(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, IpvsAdm)

    @unittest.skipIf(Memory().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Memory())
    def test_Memory(self):
        """
        Test
        """

        # Exec it
        for _ in range(2):
            exec_helper(self, Memory)

            expect_value(self, self.k, "k.os.memory.size.available", 0, "gte")
            expect_value(self, self.k, "k.os.swap.size.free", 0, "gte")

            expect_value(self, self.k, "k.os.swap.size.pfree", 0.0, "gte")
            expect_value(self, self.k, "k.os.swap.size.pfree", 101.0, "lte")

            expect_value(self, self.k, "k.os.memory.size.total", 0, "gte")
            expect_value(self, self.k, "k.os.swap.size.total", 0, "gte")
            expect_value(self, self.k, "k.os.memory.size.buffers", 0, "gte")
            expect_value(self, self.k, "k.os.memory.size.cached", 0, "gte")
            expect_value(self, self.k, "k.os.memory.size.used", 0, "gte")
            expect_value(self, self.k, "k.os.swap.size.used", 0, "gte")

    @unittest.skipIf(Memory().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Memory())
    def test_Memory_mock(self):
        """
        Test
        """

        # Exec it
        mem_file = os.path.join(dirname(abspath(__file__)), 'conf/mock_mem.txt')
        self.conf_probe_override['mem_info'] = mem_file
        exec_helper(self, Memory)

        expect_value(self, self.k, "k.os.memory.size.available", 0, "gte")
        expect_value(self, self.k, "k.os.swap.size.free", 0, "gte")

        expect_value(self, self.k, "k.os.swap.size.pfree", 0.0, "gte")
        expect_value(self, self.k, "k.os.swap.size.pfree", 101.0, "lte")

        expect_value(self, self.k, "k.os.memory.size.total", 0, "gte")
        expect_value(self, self.k, "k.os.swap.size.total", 0, "gte")
        expect_value(self, self.k, "k.os.memory.size.buffers", 0, "gte")
        expect_value(self, self.k, "k.os.memory.size.cached", 0, "gte")
        expect_value(self, self.k, "k.os.memory.size.used", 0, "gte")
        expect_value(self, self.k, "k.os.swap.size.used", 0, "gte")

    @unittest.skipIf(Netstat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Netstat())
    def test_Netstat(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, Netstat)

        expect_value(self, self.k, "k.net.netstat.SYN_SENT", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.LISTEN", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.TIME_WAIT", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.SYN_RECV", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.LAST_ACK", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.CLOSE_WAIT", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.CLOSED", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.FIN_WAIT2", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.FIN_WAIT1", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.ESTABLISHED", 0, "gte")
        expect_value(self, self.k, "k.net.netstat.CLOSING", 0, "gte")

    @unittest.skipIf(Network().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Network())
    def test_Network(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, Network)

        ar = ("lo", "LoopBack")
        for cur_n, cur_type in [ar]:
            # --------------------
            # If dynamic, extract first stuff
            # --------------------
            if cur_n == "dynamic":
                # Windows, fetch first and extract
                for tu in self.k.superv_notify_value_list:
                    k = tu[0]
                    v = tu[2]
                    if k.startswith("k.net.if.type"):
                        cur_n = k.replace("k.net.if.type[", "").replace("]", "")
                        cur_type = v
                        logger.info("Got cur_n=%s, cur_type=%s", cur_n, cur_type)
                        break

            # --------------------
            # GO
            # --------------------
            dd = {"IFNAME": cur_n}
            expect_value(self, self.k, "k.net.if.status.status", "ok", "eq", dd)
            expect_value(self, self.k, "k.eth.bytes.recv", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.bytes.sent", 0, "gte", dd)
            expect_value(self, self.k, "k.net.if.status.duplex", "full", "eq", dd)
            expect_value(self, self.k, "k.net.if.status.speed", 100.0, "gte", dd)
            expect_value(self, self.k, "k.net.if.type", cur_type, "eq", dd)
            expect_value(self, self.k, "k.net.if.status.mtu", 0, "gte", dd)
            # expect_value(self, self.k, "k.net.if.status.address", None, "exists", dd)
            expect_value(self, self.k, "k.net.if.status.tx_queue_len", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.errors.recv", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.errors.sent", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.missederrors.recv", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.packet.recv", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.packet.sent", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.packetdrop.recv", 0, "gte", dd)
            expect_value(self, self.k, "k.eth.packetdrop.sent", 0, "gte", dd)
            expect_value(self, self.k, "k.net.if.collisions", 0, "gte", dd)

    @unittest.skipIf(NumberOfProcesses().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % NumberOfProcesses())
    def test_NumberOfProcesses(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, NumberOfProcesses)

        expect_value(self, self.k, "k.os.processes.total", 1, "gte")

    @unittest.skipIf(Uptime().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Uptime())
    def test_Uptime(self):
        """
        Test
        """

        # ---------------------------
        # Exec it
        # ---------------------------
        for _ in range(2):
            exec_helper(self, Uptime)

            expect_value(self, self.k, "k.os.knock", 1, "gte")
            expect_value(self, self.k, "k.os.uptime", 1, "gte")

    def test_from_buffer_apache(self):
        """
        Test
        """

        # Init
        ap = ApacheStat()
        ap.set_manager(self.k)

        # Go
        for fn in [
            "apache/apache_24.out",
        ]:
            # Path
            fn = self.sample_dir + fn

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Load
            self.assertTrue(FileUtility.is_file_exist(fn))
            buf = FileUtility.file_to_binary(fn)

            # Process
            ap.process_apache_buffer(apache_buf=buf, pool_id="default", ms_http=11)

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Check
            for _, knock_type, knock_key in ApacheStat.KEYS:
                dd = {"ID": "default"}
                if knock_type == "int":
                    expect_value(self, self.k, knock_key, 0, "gte", dd)
                elif knock_type == "float":
                    expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                elif knock_type == "str":
                    expect_value(self, self.k, knock_key, 0, "exists", dd)

    @unittest.skipIf(VarnishStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % VarnishStat())
    def test_from_buffer_rabbitmq(self):
        """
        Test
        """

        # Init
        rs = RabbitmqStat()
        rs.set_manager(self.k)

        # Go
        for f_node, f_queue in [
            ("rabbitmq/node.out", "rabbitmq/queue.out"),
        ]:
            # Path
            f_node = self.sample_dir + f_node
            f_queue = self.sample_dir + f_queue

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Load
            self.assertTrue(FileUtility.is_file_exist(f_node))
            node_buf = FileUtility.file_to_textbuffer(f_node, "utf8")
            self.assertTrue(FileUtility.is_file_exist(f_queue))
            queue_buf = FileUtility.file_to_textbuffer(f_queue, "utf8")

            # Process
            rs.process_rabbitmq_buffers(node_buf, queue_buf)

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Check
            dd = {"PORT": "default"}
            for _, knock_type, knock_key, _ in RabbitmqStat.KEYS:
                if knock_type == "int":
                    expect_value(self, self.k, knock_key, 0, "gte", dd)
                elif knock_type == "float":
                    expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                elif knock_type == "str":
                    expect_value(self, self.k, knock_key, 0, "exists", dd)

    def test_from_buffer_varnish(self):
        """
        Test
        """

        # Init
        vs = VarnishStat()
        vs.set_manager(self.k)

        # Go
        for fn in [
            "varnish/varnish_4.json",
        ]:
            # Path
            fn = self.sample_dir + fn

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Load
            self.assertTrue(FileUtility.is_file_exist(fn))
            buf = FileUtility.file_to_binary(fn)

            # Process
            vs.process_varnish_buffer(buf, "default", ms_invoke=11)

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            for _, knock_type, knock_key in VarnishStat.KEYS:
                dd = {"ID": "default"}
                if knock_type == "int":
                    expect_value(self, self.k, knock_key, 0, "gte", dd)
                elif knock_type == "float":
                    expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                elif knock_type == "str":
                    expect_value(self, self.k, knock_key, 0, "exists", dd)

    def test_from_buffer_uwsgi(self):
        """
        Test
        """

        # Init
        us = UwsgiStat()
        us.set_manager(self.k)

        # Go
        for ar_files in [
            ("uwsgi/sample.1.out", "uwsgi/sample.2.out"),
        ]:
            # Load + init dicts
            idx = 0
            d_id_to_buffer = dict()
            d_id_to_ms = dict()
            for s in ar_files:
                s = self.sample_dir + s
                self.assertTrue(FileUtility.is_file_exist(s))
                buf = FileUtility.file_to_textbuffer(s, "utf8")
                cur_id = "%s" % idx
                d_id_to_buffer[cur_id] = buf
                d_id_to_ms[cur_id] = idx
                idx += 1

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Process
            us.process_uwsgi_buffers(d_id_to_buffer, d_id_to_ms)

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Browse all ids and "ALL"
            ar = list(range(0, len(ar_files)))
            ar.append("ALL")
            for cur_p in ar:
                cur_p = str(cur_p)
                for _, knock_type, knock_key in UwsgiStat.KEYS:
                    dd = {"ID": cur_p}
                    if knock_type == "int":
                        expect_value(self, self.k, knock_key, 0, "gte", dd)
                    elif knock_type == "float":
                        expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                    elif knock_type == "str":
                        expect_value(self, self.k, knock_key, 0, "exists", dd)

    @unittest.skipIf(CheckProcess().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % CheckProcess())
    def test_CheckProcess(self):
        """
        Test
        """

        # Exec it
        exec_helper(self, CheckProcess)

        # Ar
        ar = ["nginx"]

        # Using direct
        for cur_p in ar:
            dd = {"PROCNAME": cur_p}
            expect_value(self, self.k, "k.proc.pidfile", "ok", "eq", dd)
            expect_value(self, self.k, "k.proc.running", "ok", "eq", dd)
            expect_value(self, self.k, "k.proc.io.num_fds", 0, "gte", dd)
            expect_value(self, self.k, "k.proc.memory_used", 0, "gte", dd)
            expect_value(self, self.k, "k.proc.cpu_used", 0, "gte", dd)
            expect_value(self, self.k, "k.proc.nbprocess", 0, "gte", dd)

            # Kernel too old may not support that (Couldn't find /proc/xxxx/io)
            # If OUR process has them, check them, otherwise discard
            self_pid = str(os.getpid())
            if FileUtility.is_file_exist("/proc/" + self_pid + "/io"):
                try:
                    p = psutil.Process(int(self_pid))
                    _ = p.io_counters()
                    # Working, check
                    expect_value(self, self.k, "k.proc.io.read_bytes", 0, "gte", dd)
                    expect_value(self, self.k, "k.proc.io.write_bytes", 0, "gte", dd)
                except Exception as e:
                    logger.warning("io_counters failed, bypassing checks, ex=%s", SolBase.extostr(e))

        # Using arrays
        # Ar
        ar = ["nginx_array"]
        for cur_p in ar:
            dd = {"PROCNAME": cur_p}
            expect_value(self, self.k, "k.proc.pidfile", "ok", "eq", dd)
            expect_value(self, self.k, "k.proc.running", "ok", "eq", dd)
            expect_value(self, self.k, "k.proc.io.num_fds", 0, "gte", dd)
            expect_value(self, self.k, "k.proc.memory_used", 0, "gte", dd)
            expect_value(self, self.k, "k.proc.cpu_used", 0, "gte", dd)
            expect_value(self, self.k, "k.proc.nbprocess", 0, "gte", dd)

            # Kernel too old may not support that (Couldn't find /proc/xxxx/io)
            # If OUR process has them, check them, otherwise discard
            self_pid = str(os.getpid())
            if FileUtility.is_file_exist("/proc/" + self_pid + "/io"):
                try:
                    p = psutil.Process(int(self_pid))
                    _ = p.io_counters()
                    # Working, check
                    expect_value(self, self.k, "k.proc.io.read_bytes", 0, "gte", dd)
                    expect_value(self, self.k, "k.proc.io.write_bytes", 0, "gte", dd)
                except Exception as e:
                    logger.warning("io_counters failed, bypassing checks, ex=%s", SolBase.extostr(e))

    def test_from_buffer_mysql(self):
        """
        Test
        """

        # Init
        m = Mysql()
        m.set_manager(self.k)

        # Go
        for f_status, f_variables, f_slave in [
            ("mysql/status.out", "mysql/variables.out", "mysql/slave.out"),
        ]:
            # Path
            f_status = self.sample_dir + f_status
            f_variables = self.sample_dir + f_variables
            f_slave = self.sample_dir + f_slave

            # Reset
            self.k._reset_superv_notify()
            Meters.reset()

            # Load
            self.assertTrue(FileUtility.is_file_exist(f_status))
            status_buf = FileUtility.file_to_textbuffer(f_status, "utf8")
            self.assertTrue(FileUtility.is_file_exist(f_variables))
            variables_buf = FileUtility.file_to_textbuffer(f_variables, "utf8")
            self.assertTrue(FileUtility.is_file_exist(f_slave))
            slave_buf = FileUtility.file_to_textbuffer(f_slave, "utf8")

            # Switch to arrays - status
            ar_status = list()
            for s in status_buf.split("\n"):
                s = s.strip()
                if not s.startswith("|"):
                    continue
                elif s.startswith("| Variable_name"):
                    continue
                ar = s.split("|")
                k = ar[1].strip()
                v = ar[2].strip()
                ar_status.append({"Variable_name": k, "Value": v})

            # Switch to arrays - variables
            ar_variables = list()
            for s in variables_buf.split("\n"):
                s = s.strip()
                if not s.startswith("|"):
                    continue
                elif s.startswith("| Variable_name"):
                    continue
                ar = s.split("|")
                k = ar[1].strip()
                v = ar[2].strip()
                ar_variables.append({"Variable_name": k, "Value": v})

            # Switch to arrays - slave
            d_slave = dict()
            for s in slave_buf.split("\n"):
                s = s.strip()
                if s.startswith("*"):
                    continue
                elif ":" not in s:
                    continue
                ar = s.split(":")
                k = ar[0].strip()
                v = ar[1].strip()
                d_slave[k] = v
            ar_slave = [d_slave]

            # Process
            m.process_mysql_buffers(ar_status, ar_slave, ar_variables, "default", 22)

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Check
            for _, knock_type, knock_key in Mysql.KEYS:
                dd = {"ID": "default"}
                if knock_type == "int":
                    if knock_key == "k.mysql.repli.cur.lag_sec":
                        expect_value(self, self.k, knock_key, -2, "gte", dd)
                    else:
                        expect_value(self, self.k, knock_key, 0, "gte", dd)
                elif knock_type == "float":
                    expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                elif knock_type == "str":
                    expect_value(self, self.k, knock_key, 0, "exists", dd)

    @classmethod
    def mongo_cleanup_buffer(cls, buf):
        """
        Mongo cleanup buffer
        :param buf: str
        :type buf: str
        :return: str
        :rtype str
        """

        # NumberLong(772349720)
        # NumberLong("6970055494123651073")
        # ISODate("2021-09-16T08:12:00.002Z")
        # Timestamp(1631779918, 11)
        # BinData(0,"mPIrxO2yyOyZgIXyYGL7awzFgKo="),
        ar_regex = [
            r'NumberLong\(\d+\)',
            r'NumberLong\("\d+"\)',
            r'ISODate\(".*"\)',
            r'Timestamp\(\d+, \d+\)',
            r'BinData\(.*\)',
        ]

        # Totally sub-optimal, unittests, we dont care
        for s in ar_regex:
            for ss in re.findall(s, buf):
                if 'NumberLong("' in ss:
                    buf = buf.replace(ss, ss.replace('NumberLong("', '').replace('")', ''))
                elif 'NumberLong(' in ss:
                    buf = buf.replace(ss, ss.replace('NumberLong(', '').replace(')', ''))
                elif 'ISODate("' in ss:
                    buf_dt = ss.replace('ISODate("', "").replace('")', "")
                    dt = dateutil.parser.parse(buf_dt)
                    epoch = SolBase.dt_to_epoch(SolBase.dt_ensure_utc_naive(dt))
                    buf = buf.replace(ss, str(epoch))
                elif 'Timestamp(' in ss:
                    ts = ss.replace('Timestamp(', '').replace(')', '').split(',')[0]
                    buf = buf.replace(ss, ts)
                elif 'BinData(' in ss:
                    buf = buf.replace(ss, '"bin_data"')
                else:
                    raise Exception("Invalid ss=%s" % ss)

        return buf

    def test_from_buffer_mongo(self):
        """
        Test
        """

        # Init
        md = MongoDbStat()
        md.set_manager(self.k)

        # Go
        cur_port = 27017
        for fn, d_expected in [
            (
                    "mongodb/mongo.out",
                    {
                        'k.mongodb.version': '4.2.14',
                        'k.mongodb.uptimeMillis': 772349720,
                        'k.mongodb.asserts_regular': 0,
                        'k.mongodb.asserts_warning': 0,
                        'k.mongodb.asserts_msg': 0,
                        'k.mongodb.asserts_user': 32,
                        'k.mongodb.asserts_rollovers': 0,
                        'k.mongodb.connections_current': 104,
                        'k.mongodb.connections_available': 51096,
                        'k.mongodb.connections_totalCreated': 761731,
                        'k.mongodb.extra_info_page_faults': 766,
                        'k.mongodb.network_bytesIn': 1899981047,
                        'k.mongodb.network_bytesOut': 4199415635,
                        'k.mongodb.network_numRequests': 6327819,
                        'k.mongodb.opcounters_insert': 719110,
                        'k.mongodb.opcounters_query': 58528,
                        'k.mongodb.opcounters_update': 50,
                        'k.mongodb.opcounters_delete': 4,
                        'k.mongodb.opcounters_getmore': 437,
                        'k.mongodb.opcounters_command': 6268848,
                        'k.mongodb.mem_bits': 64,
                        'k.mongodb.mem_resident': 117,
                        'k.mongodb.mem_virtual': 448,
                        'k.mongodb.mem_supported': 1,
                        'k.mongodb.metrics_cursor_timedOut': 1,
                        'k.mongodb.metrics_cursor_open_pinned': 0,
                        'k.mongodb.metrics_cursor_open_total': 0,
                        'k.mongodb.ok': 1.0,
                        'k.mongodb.metrics_commands_total': 6327813,
                        'k.mongodb.metrics_commands_failed': 30,
                    }
            ),
        ]:
            # Path
            fn = self.sample_dir + fn
            self.assertTrue(FileUtility.is_file_exist(fn))

            buf = FileUtility.file_to_textbuffer(fn, "utf8")
            buf = self.mongo_cleanup_buffer(buf)
            d_json = ujson.loads(buf)

            md.process_mongo_server_status(d_json, str(cur_port))

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Check
            dd = {'PORT': str(cur_port)}
            cur_port += 1

            for k, v in d_expected.items():
                expect_value(self, self.k, k, v, "eq", dd)
