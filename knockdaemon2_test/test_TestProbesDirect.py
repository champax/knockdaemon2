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
import glob
import logging
import platform
import shutil
import sys
import ujson
import unittest
from datetime import datetime

import os
import psutil
# noinspection PyPackageRequirements
from dns.resolver import Resolver
# noinspection PyPackageRequirements,PyUnresolvedReferences
from nose.plugins.attrib import attr
from os.path import dirname, abspath
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Probes.Apache.ApacheStat import ApacheStat
from knockdaemon2.Probes.Haproxy.Haproxy import Haproxy
from knockdaemon2.Probes.Inventory.Inventory import Inventory
from knockdaemon2.Probes.MemCached.MemCachedStat import MemCachedStat
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
from knockdaemon2.Probes.PhpFpm.PhpFpmStat import PhpFpmStat
from knockdaemon2.Probes.Rabbitmq.RabbitmqStat import RabbitmqStat
from knockdaemon2.Probes.Redis.RedisStat import RedisStat
from knockdaemon2.Probes.Uwsgi.UwsgiStat import UwsgiStat
from knockdaemon2.Probes.Varnish.VarnishStat import VarnishStat
# noinspection PyProtectedMember
from knockdaemon2.Tests.TestHelpers import expect_disco, _exec_helper
from knockdaemon2.Tests.TestHelpers import expect_value

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class TestProbesDirect(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.config_file = \
            self.current_dir + "conf" + SolBase.get_pathseparator() \
            + "realall" + SolBase.get_pathseparator() + "knockdaemon2.yaml"

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

        # If windows, perform a WMI initial refresh to get datas
        if PTools.get_distribution_type() == "windows":
            from knockdaemon2.Windows.Wmi.Wmi import Wmi
            Wmi._wmi_fetch_all()
            Wmi._flush_props(Wmi._WMI_DICT, Wmi._WMI_DICT_PROPS)

    def tearDown(self):
        """
        Setup (called after each test)
        """

        if self.debug_stat:
            Meters.write_to_logger()

    @unittest.skipIf(NginxStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % NginxStat())
    @unittest.skip("TODO : Re-enable later")
    def test_NginxStat(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, NginxStat)

        # Validate results - disco

        dd = {"ID": "default"}
        expect_disco(self, self.k, "k.nginx.discovery", dd)

        # Validate results - data
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
        _exec_helper(self, Service)

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
                self.assertIsInstance(k, basestring)
                self.assertTrue(k.startswith("uwsgi_"))
                self.assertIsInstance(v, int)

    @unittest.skipIf(Service().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Service())
    def test_Mdstat(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, Mdstat)

        # Validate results - disco
        pass

    @unittest.skipIf(Haproxy().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % NginxStat())
    @unittest.skip("TODO : Re-enable later")
    def test_Haproxy(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, Haproxy)

        # Validate results - disco
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
        logger.info('self.k._superv_notify_value_list=%s', ujson.dumps(self.k._superv_notify_value_list))

        # expect_value(self, self.k, "k.haproxy.backend", 0.0, "exists", {"PROXY": "nodes"})
        # expect_value(self, self.k, "k.haproxy.frontend", 0.0, "exists", {"PROXY": "localnodes"})

    @unittest.skipIf(CheckDns().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % CheckDns())
    def test_CheckDns(self):
        """
        Test
        """

        # Exec it

        _exec_helper(self, CheckDns)
        ns = Resolver().nameservers[0]

        # Validate results - disco
        dd = {"HOST": "knock.center", "SERVER": ns}
        expect_disco(self, self.k, "k.dns.discovery", dd)

        # Validate results - data
        expect_value(self, self.k, "k.dns.resolv", "198.27.81.204", "eq", dd)
        expect_value(self, self.k, "k.dns.time", 0, "gte", dd)

    @unittest.skipIf(TimeDiff().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % TimeDiff())
    def test_TimeDiff(self):
        """
        Test
        """

        # Exec it

        _exec_helper(self, TimeDiff)

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
        (distribution, dversion, _) = platform.linux_distribution()

        # Exec it
        _exec_helper(self, Inventory)

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
    def test_HddStatus(self):
        """
        Test
        """

        # Requires SUDO :
        # user ALL=(ALL:ALL) NOPASSWD: /usr/sbin/smartctl

        # Exec it
        _exec_helper(self, HddStatus)

        # CANNOT VALIDATE ON vm, requires a PHYSICAL server (need /dev/sd*)
        hds = glob.glob('/dev/sd[a-z]')
        hds.extend(glob.glob('/dev/sd[a-z][a-z]'))
        if len(hds) == 0:
            logger.info("Assuming VM, lightweight checks")
            dd = {"HDD": "ALL"}
            expect_value(self, self.k, "k.hard.hd.status", "OK", "eq", dd)
            expect_value(self, self.k, "k.hard.hd.user_capacity", "ALL", "eq", dd)
            expect_value(self, self.k, "k.hard.hd.reallocated_sector_ct", 0, "eq", dd)
            expect_value(self, self.k, "k.hard.hd.user_capacity", "ALL", "eq", dd)
            expect_value(self, self.k, "k.hard.hd.serial_number", "ALL", "eq", dd)
            expect_value(self, self.k, "k.hard.hd.model_family", "ALL", "eq", dd)
            expect_value(self, self.k, "k.hard.hd.total_lbas_written", 0, "eq", dd)
            expect_value(self, self.k, "k.hard.hd.health", "KNOCKOK", "eq", dd)
            expect_value(self, self.k, "k.hard.hd.device_model", "ALL", "eq", dd)

            expect_disco(self, self.k, "k.hard.hd.discovery", dd)
        else:
            # Try invoke on first sdX
            ec, so, se = ButcherTools.invoke("smartctl -q errorsonly -H -l selftest -b " + hds[0], timeout_ms=120000)
            logger.info("Got ec=%s, so=%s, se=%s", ec, so, se)
            if ec == 0:
                logger.info("Assuming PHYSICAL, heavy checks")
                self.assertFalse("Physical server heavy checks NOT implemented")
                # TODO : Implement unittest on a physical server please
            else:
                logger.info("smartctl invoke failed, bypassing checks")

    @unittest.skipIf(Load().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Load())
    def test_Load(self):
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
        # VALIDATE WINDOWS LOAD API
        # ----------------------------

        # Keep current ms
        ms_cur = 1489440100000

        # Validate windows queue length processing
        ar = list()
        for min_back in range(20, 0, -1):
            ms_back = min_back * 60 * 1000
            ms_set = ms_cur - ms_back
            ar.append({"ms": ms_set, "q": min_back * 10})
        logger.info("ar_in=%s", ar)
        len_in = len(ar)

        # Get load
        load1, load5, load15 = Load.process_ar_queue(ar, ms_cur)
        logger.info("ar_out=%s", ar)
        len_out = len(ar)

        # We must have evictions
        self.assertLess(len_out, len_in)
        for d in ar:
            # All items must be less than 15 minutes
            self.assertLessEqual(SolBase.msdiff(d["ms"], ms_cur), 15 * 60 * 1000)

        # Check load
        self.assertEqual(load1, 10.0)
        self.assertEqual(load5, 10.0)
        self.assertEqual(load15, 80.0)

        # ---------------------------
        # Parse datetime (windows)
        # ---------------------------
        # noinspection PyArgumentList
        for ar in [
            # Offset -420 (ie -7H based on utc : Hour=4 => +7 : Hour=11 in utc)
            ["20170312044209.003363-420", datetime(year=2017, month=3, day=12, hour=11, minute=42, second=9, microsecond=3363)],
        ]:
            # GO
            s_dt = ar[0]
            c_dt = ar[1]
            d_dt = Load.parse_time(s_dt)
            logger.info("Got c_dt=%s", c_dt)
            logger.info("Got d_dt=%s", d_dt)
            self.assertEqual(c_dt, d_dt)

        # ----------------------------
        # Exec it
        # ----------------------------
        for _ in range(2):
            _exec_helper(self, Load)
            expect_value(self, self.k, "k.os.cpu.load.percpu.avg1", None, "exists")
            expect_value(self, self.k, "k.os.cpu.load.percpu.avg5", None, "exists")
            expect_value(self, self.k, "k.os.cpu.load.percpu.avg15", None, "exists")
            expect_value(self, self.k, "k.os.cpu.core", 1, "gte")
            expect_value(self, self.k, "k.os.cpu.util.softirq", None, "exists")
            expect_value(self, self.k, "k.os.cpu.util.iowait", None, "exists")
            expect_value(self, self.k, "k.os.cpu.util.system", None, "exists")
            expect_value(self, self.k, "k.os.cpu.util.idle", None, "exists")
            expect_value(self, self.k, "k.os.cpu.util.user", None, "exists")
            expect_value(self, self.k, "k.os.cpu.util.interrupt", None, "exists")
            expect_value(self, self.k, "k.os.cpu.util.steal", None, "exists")
            expect_value(self, self.k, "k.os.cpu.util.nice", None, "exists")
            expect_value(self, self.k, "k.os.cpu.switches", None, "exists")
            expect_value(self, self.k, "k.os.cpu.intr", None, "exists")
            expect_value(self, self.k, "k.os.boottime", None, "exists")
            expect_value(self, self.k, "k.os.processes.running", None, "exists")
            expect_value(self, self.k, "k.os.hostname", None, "exists")
            expect_value(self, self.k, "k.os.localtime", None, "exists")
            expect_value(self, self.k, "k.os.maxfiles", None, "exists")
            expect_value(self, self.k, "k.os.openfiles", None, "exists")
            expect_value(self, self.k, "k.os.maxproc", None, "exists")
            expect_value(self, self.k, "k.os.users.connected", 0, "gte")

    @unittest.skipIf(RedisStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % RedisStat())
    @unittest.skip("TODO : Re-enable later")
    def test_RedisStat(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, RedisStat)

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

                expect_disco(self, self.k, "k.redis.discovery", dd)

    @unittest.skipIf(MemCachedStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % MemCachedStat())
    @attr('prov')
    def test_MemCachedStat(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, MemCachedStat)

        # Validate KEYS
        for cur_connect_to in ["11211", "ALL"]:
            dd = {"MC": cur_connect_to}
            for _, knock_type, knock_key, _ in MemCachedStat.KEYS:
                if knock_type == "int":
                    expect_value(self, self.k, knock_key, -1, "gte", dd)
                elif knock_type == "float":
                    expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                elif knock_type == "str":
                    expect_value(self, self.k, knock_key, 0, "exists", dd)

            expect_disco(self, self.k, "k.memcached.discovery", dd)

    @unittest.skipIf(DiskSpace().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % DiskSpace())
    def test_DiskSpace(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, DiskSpace)
        SolBase.sleep(1000)
        _exec_helper(self, DiskSpace)
        if PTools.get_distribution_type() == "windows":
            ar = ["C:", "ALL"]
        else:
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
        _exec_helper(self, IpvsAdm)

    @unittest.skipIf(Memory().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Memory())
    def test_Memory(self):
        """
        Test
        """

        # Exec it
        for _ in range(2):
            _exec_helper(self, Memory)

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
        _exec_helper(self, Memory)

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
        _exec_helper(self, Netstat)

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
        _exec_helper(self, Network)

        if PTools.get_distribution_type() == "windows":
            ar = ("dynamic", "dynamic")
        else:
            ar = ("lo", "LoopBack")
        for cur_n, cur_type in [ar]:
            # --------------------
            # If dynamic, extract first stuff
            # --------------------
            if cur_n == "dynamic":
                # Windows, fetch first and extract
                for tu in self.k._superv_notify_value_list:
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
        _exec_helper(self, NumberOfProcesses)

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
            _exec_helper(self, Uptime)

            expect_value(self, self.k, "k.os.knock", 1, "gte")
            expect_value(self, self.k, "k.os.uptime", 1, "gte")

    @unittest.skipIf(PhpFpmStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % PhpFpmStat())
    @attr('prov')
    def test_PhpFpmStat(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, PhpFpmStat)

        for _, knock_type, knock_key in PhpFpmStat.KEYS:
            for pool_id in ["www", "ALL"]:
                dd = {"ID": pool_id}
                if knock_type == "int":
                    expect_value(self, self.k, knock_key, 0, "gte", dd)
                elif knock_type == "float":
                    expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                elif knock_type == "str":
                    expect_value(self, self.k, knock_key, 0, "exists", dd)

                expect_disco(self, self.k, "k.phpfpm.discovery", dd)

    @unittest.skipIf(ApacheStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    @attr('prov')
    def test_Apache(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, ApacheStat)

        for _, knock_type, knock_key in ApacheStat.KEYS:
            dd = {"ID": "default"}
            if knock_type == "int":
                expect_value(self, self.k, knock_key, 0, "gte", dd)
            elif knock_type == "float":
                expect_value(self, self.k, knock_key, 0.0, "gte", dd)
            elif knock_type == "str":
                expect_value(self, self.k, knock_key, 0, "exists", dd)

            expect_disco(self, self.k, "k.apache.discovery", dd)

    @unittest.skipIf(ApacheStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    @attr('prov')
    def test_Apache_from_dict_1(self):
        """
        Test
        """
        d = {'k.apache.status.ms': 100, 'k.apache.sc.send_reply': 3, 'Uptime': 599634.0, 'IdleWorkers': 12.0, 'k.apache.sc.waiting_for_connection': 12, 'k.apache.sc.keepalive': 0,
             'k.apache.sc.dns_lookup': 0, 'Total Accesses': 11934709.0, 'k.apache.sc.closing': 1, 'Total kBytes': 33635364.0, 'BytesPerReq': 2885.92, 'k.apache.sc.reading_request': 0, 'CPULoad': 0.06,
             'BytesPerSec': 57439.4, 'k.apache.sc.gracefully': 0, 'k.apache.sc.starting_up': 0, 'ReqPerSec': 19.9, 'k.apache.sc.open': 240, 'k.apache.sc.idle': 0, 'k.apache.sc.logging': 0,
             'BusyWorkers': 4.0}
        ap = ApacheStat()
        ap.set_manager(self.k)
        ap.process_apache_dict(d, "default")

        # Log
        for tu in self.k._superv_notify_value_list:
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

        # Discovery is fired outside this, do not check it here
        pass

    @unittest.skipIf(VarnishStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % VarnishStat())
    @attr('prov')
    def test_Rabbitmq(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, RabbitmqStat)

        for _, knock_type, knock_key, _ in RabbitmqStat.KEYS:
            dd = {"PORT": "default"}
            if knock_type == "int":
                expect_value(self, self.k, knock_key, 0, "gte", dd)
            elif knock_type == "float":
                expect_value(self, self.k, knock_key, 0.0, "gte", dd)
            elif knock_type == "str":
                expect_value(self, self.k, knock_key, 0, "exists", dd)

            expect_disco(self, self.k, "k.rabbitmq.discovery", dd)

    @unittest.skipIf(VarnishStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % VarnishStat())
    @attr('prov')
    def test_Varnish(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, VarnishStat)

        for _, knock_type, knock_key in VarnishStat.KEYS:
            dd = {"ID": "default"}
            if knock_type == "int":
                expect_value(self, self.k, knock_key, 0, "gte", dd)
            elif knock_type == "float":
                expect_value(self, self.k, knock_key, 0.0, "gte", dd)
            elif knock_type == "str":
                expect_value(self, self.k, knock_key, 0, "exists", dd)

            expect_disco(self, self.k, "k.varnish.discovery", dd)

    @unittest.skipIf(VarnishStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % VarnishStat())
    @attr('prov')
    def test_Varnish_via_invoke_json(self):
        """
        Test
        """

        vp = VarnishStat()
        vp.set_manager(self.k)

        # ---------
        # JSON
        # ---------
        d_json = vp.try_load_json()
        vp.process_json(d_json, "default")
        # Log
        for tu in self.k._superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        for _, knock_type, knock_key in VarnishStat.KEYS:
            dd = {"ID": "default"}
            if knock_type == "int":
                expect_value(self, self.k, knock_key, 0, "gte", dd)
            elif knock_type == "float":
                expect_value(self, self.k, knock_key, 0.0, "gte", dd)
            elif knock_type == "str":
                expect_value(self, self.k, knock_key, 0, "exists", dd)

        # Discovery is fired outside this, do not check it here
        pass

    @unittest.skipIf(VarnishStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % VarnishStat())
    @attr('prov')
    def test_Varnish_via_invoke_text(self):
        """
        Test
        """

        vp = VarnishStat()
        vp.set_manager(self.k)

        # ---------
        # JSON
        # ---------
        d_json = vp.try_load_text()
        vp.process_json(d_json, "default")
        # Log
        for tu in self.k._superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        for _, knock_type, knock_key in VarnishStat.KEYS:
            dd = {"ID": "default"}
            if knock_type == "int":
                expect_value(self, self.k, knock_key, 0, "gte", dd)
            elif knock_type == "float":
                expect_value(self, self.k, knock_key, 0.0, "gte", dd)
            elif knock_type == "str":
                expect_value(self, self.k, knock_key, 0, "exists", dd)

        # Discovery is fired outside this, do not check it here
        pass

    @unittest.skipIf(UwsgiStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % UwsgiStat())
    @attr('prov')
    def test_UwsgiStat(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, UwsgiStat)

        for cur_p in [
            'z_frontends',
            'ALL'
        ]:
            for _, knock_type, knock_key in UwsgiStat.KEYS:
                dd = {"ID": cur_p}
                if knock_type == "int":
                    expect_value(self, self.k, knock_key, 0, "gte", dd)
                elif knock_type == "float":
                    expect_value(self, self.k, knock_key, 0.0, "gte", dd)
                elif knock_type == "str":
                    expect_value(self, self.k, knock_key, 0, "exists", dd)

                expect_disco(self, self.k, "k.uwsgi.discovery", dd)

    @unittest.skipIf(CheckProcess().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % CheckProcess())
    def test_CheckProcess(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, CheckProcess)

        # Ar
        if PTools.get_distribution_type() == "windows":
            ar = ["win_idle_process"]
        else:
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
                    logger.warn("io_counters failed, bypassing checks, ex=%s", SolBase.extostr(e))

        # Using arrays
        # Ar
        if PTools.get_distribution_type() == "windows":
            ar = ["win_idle_process_array"]
        else:
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
                    logger.warn("io_counters failed, bypassing checks, ex=%s", SolBase.extostr(e))

    @unittest.skipIf(Mysql().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Mysql())
    @attr('prov')
    def test_Mysql(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, Mysql)

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

            expect_disco(self, self.k, "k.mysql.discovery", dd)

    @unittest.skipIf(MongoDbStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % MongoDbStat())
    # @unittest.skip("zzz")
    @attr('prov')
    def test_MongoDbStat(self):
        """
        Test
        """

        # Exec it
        _exec_helper(self, MongoDbStat)
