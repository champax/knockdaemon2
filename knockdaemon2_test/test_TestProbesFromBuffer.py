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
import json

from pysolbase.SolBase import SolBase

SolBase.voodoo_init()

import glob
from unittest.mock import patch

# noinspection PyProtectedMember
from psutil._pslinux import pmem, pcputimes, pio

import logging
import os
import shutil
import sys
import unittest
from os.path import dirname, abspath

import distro
from pysolbase.FileUtility import FileUtility
from pysolmeters.Meters import Meters

from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Probes.Apache.ApacheStat import ApacheStat
from knockdaemon2.Probes.Haproxy.Haproxy import Haproxy
from knockdaemon2.Probes.Inventory.Inventory import Inventory
from knockdaemon2.Probes.Mongodb.MongoDbStat import MongoDbStat
from knockdaemon2.Probes.Mysql.Mysql import Mysql
from knockdaemon2.Probes.Nginx.NGinxStat import NginxStat
from knockdaemon2.Probes.Os.CheckDns import CheckDns, get_resolv
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


def get_zpool_io_buffer_mocked(file_name):
    """
    Get zpool io
    :param file_name: str
    :type file_name: str
    :return: str
    :rtype str
    """
    current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
    sample_dir = current_dir + "../z_docs/samples/"

    with open(sample_dir + file_name) as f:
        return f.read()


class MockProcessForCheckProcess(object):
    """
    Mock process
    """

    def __init__(self):
        """
        Init
        """
        self.name = None
        self.pid = 0
        self._pid = 0
        self.ppid = 0


class MockProcessForService(object):
    """
    Mock process
    """

    def __init__(self):
        """
        Init
        """
        self.cmd_line = None
        self.pid = 0
        self._pid = 0
        self.v_ppid = 0

    def cmdline(self):
        """
        Get
        :return: str
        :rtype str
        """
        return self.cmd_line

    def ppid(self):
        """
        Get
        :return: int
        :rtype int
        """
        return self.v_ppid


def get_service_running_services_mocked():
    """
    Get
    :return: set of str
    :rtype set
    """
    return {
        "systemd_01_running",
        "sysv_03_running",
    }


def get_service_systemd_services_mocked():
    """
    Get
    :return: set of str
    :rtype set
    """
    return {
        "systemd_01_running",
        "systemd_02_not_running",
    }


def get_service_sysv_services_mocked():
    """
    Get
    :return: set of str
    :rtype set
    """
    return {
        "sysv_03_running",
        "sysv_04_not_running",
    }


def get_service_process_stat_mocked():
    """
    Get process stats
    :return: dict
    :rtype dict
    """
    return get_checkprocess_process_stat_mocked()


def get_service_get_process_list_mocked():
    """
    Get process iter
    :return: list
    :rtype list
    """
    ar = list()

    m = MockProcessForService()
    m.cmd_line = "/usr/bin/uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/a01.ini --daemonize /var/log/uwsgi/app/a01.log"
    m.cmd_line = m.cmd_line.split(" ")
    m.pid = m._pid = 1
    m.v_ppid = 1
    ar.append(m)

    m = MockProcessForService()
    m.cmd_line = "/usr/bin/uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/a02.ini --daemonize /var/log/uwsgi/app/a02.log"
    m.cmd_line = m.cmd_line.split(" ")
    m.pid = m._pid = 1
    m.v_ppid = 1
    ar.append(m)

    m = MockProcessForService()
    m.cmd_line = "/usr/bin/toto"
    m.cmd_line = m.cmd_line.split(" ")
    m.pid = m._pid = 1
    m.v_ppid = 1
    ar.append(m)

    return ar


def get_service_process_child_mocked():
    """
    Get process child
    :return: list of Process
    :rtype list
    """
    ar = list()

    m = MockProcessForService()
    m.cmd_line = "/aaa"
    m.pid = 1
    m.v_ppid = 0
    ar.append(m)

    return ar


def get_service_io_counters_mocked():
    """
    Get io counters
    :return: psutil._pslinux.pio
    :rtype psutil._pslinux.pio
    """
    return get_checkprocess_io_counters_mocked()


def get_checkprocess_process_list_mocked():
    """
    Get process list
    :return: list of Process
    :rtype list
    """
    p1 = MockProcessForCheckProcess()
    p1.name = "nginx"
    p1.pid = p1._pid = 0
    p1.ppid = 99999

    p2 = MockProcessForCheckProcess()
    p2.name = "nginx"
    p2.pid = p2._pid = 99999
    p2.ppid = 0

    p3 = MockProcessForCheckProcess()
    p3.name = "tamer"
    p3.pid = p3._pid = 0
    p3.ppid = 88888
    return [p1, p2, p3]


def get_checkprocess_io_counters_mocked():
    """
    Get io counters
    :return: psutil._pslinux.pio
    :rtype psutil._pslinux.pio
    """
    return pio(read_count=3, write_count=0, read_bytes=77, write_bytes=88, read_chars=1377, write_chars=0)


def get_checkprocess_process_stat_mocked():
    """
    Get process stats
    :return: dict
    :rtype dict
    """
    return {
        # 3.0 = cpu_used
        "cpu_times": pcputimes(1.0, 2.0, 3.0, 4.0, 5.0),
        "memory_info": pmem(1736704, 67235840, 49152, 847872, 0, 1757184, 0),
        "num_fds": 10,
    }


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

    @patch('knockdaemon2.Probes.Os.Service.get_process_list', return_value=get_service_get_process_list_mocked())
    @patch('knockdaemon2.Probes.Os.Service.get_io_counters', return_value=get_service_io_counters_mocked())
    @patch('knockdaemon2.Probes.Os.Service.get_process_child', return_value=get_service_process_child_mocked())
    @patch('knockdaemon2.Probes.Os.Service.get_running_services', return_value=get_service_running_services_mocked())
    @patch('knockdaemon2.Probes.Os.Service.get_systemd_services', return_value=get_service_systemd_services_mocked())
    @patch('knockdaemon2.Probes.Os.Service.get_sysv_services', return_value=get_service_sysv_services_mocked())
    @patch('knockdaemon2.Probes.Os.Service.get_process_stat', return_value=get_service_process_stat_mocked())
    @patch('knockdaemon2.Probes.Os.Service.systemd_is_active', return_value=True)
    @patch('knockdaemon2.Probes.Os.Service.systemd_get_pid', return_value=999901)
    def test_from_buffer_service_with_mock(self, m1, m2, m3, m4, m5, m6, m7, m8, m9):
        """
        Test
        """

        self.assertIsNotNone(m1)
        self.assertIsNotNone(m2)
        self.assertIsNotNone(m3)
        self.assertIsNotNone(m4)
        self.assertIsNotNone(m5)
        self.assertIsNotNone(m6)
        self.assertIsNotNone(m7)
        self.assertIsNotNone(m8)
        self.assertIsNotNone(m9)

        # Init
        s = Service()
        s.set_manager(self.k)
        s.patern_list = [".*"]

        # Exec
        s.execute()

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Validate results
        expect_value(self, self.k, "k.os.service.running", 0, 'eq', {"SERVICE": "systemd_02_not_running"})
        expect_value(self, self.k, "k.os.service.running", 0, 'eq', {"SERVICE": "sysv_04_not_running"})
        expect_value(self, self.k, "k.os.service.running_count", 4, 'eq', None)

        # Validate results : uwsgi
        for s in ["systemd_01_running", "sysv_03_running", "uwsgi_default_a01", "uwsgi_default_a02"]:
            expect_value(self, self.k, "k.os.service.running", 1, 'eq', {"SERVICE": s})
            expect_value(self, self.k, "k.proc.io.read_bytes", 154, 'eq', {"PROCNAME": s})
            expect_value(self, self.k, "k.proc.io.write_bytes", 176, 'eq', {"PROCNAME": s})
            expect_value(self, self.k, "k.proc.io.num_fds", 20, 'eq', {"PROCNAME": s})
            expect_value(self, self.k, "k.proc.memory_used", 3473408, 'eq', {"PROCNAME": s})
            expect_value(self, self.k, "k.proc.cpu_used", 6.0, 'eq', {"PROCNAME": s})

    def test_from_mem_uwsgi_get_type(self):
        """
        Test
        """

        ar = "/usr/bin/uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/toto.ini --daemonize /var/log/uwsgi/app/toto.log".split(" ")
        s_uwsgi = Service.uwsgi_get_type(ar)
        self.assertEquals(s_uwsgi, "uwsgi_default_toto")

        ar = "/usr/bin/uwsgi".split(" ")
        s_uwsgi = Service.uwsgi_get_type(ar)
        self.assertEquals(s_uwsgi, "uwsgi_na")

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

    def test_from_buffer_checkdns(self):
        """
        Test
        """

        # Init
        cd = CheckDns()
        cd.set_manager(self.k)

        # Set
        cd.host_to_check = "www.google.com,knock.center".split(",")

        # Exec
        cd.execute()

        # Get nameserver
        ar_ns = get_resolv()
        logger.info("Using ar_ns=%s", ar_ns)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        for ns in ar_ns:
            for hn in ["www.google.com", "knock.center"]:
                dd = {"HOST": hn, "SERVER": ns}
                if hn == "knock.center":
                    expect_value(self, self.k, "k.dns.resolv", "198.27.81.204", "eq", dd)
                    expect_value(self, self.k, "k.dns.time", 0, "gte", dd)
                else:
                    expect_value(self, self.k, "k.dns.resolv", "198.27.81.204", "exists", dd)
                    expect_value(self, self.k, "k.dns.time", 0, "gte", dd)

    @patch('knockdaemon2.Probes.Os.TimeDiff.get_ntp_offset', return_value=88.7)
    def test_from_buffer_timediff_with_mock(self, m1):
        """
        Test
        """

        self.assertIsNotNone(m1)

        # Init
        td = TimeDiff()
        td.set_manager(self.k)

        # Exec
        td._execute_linux()

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.os.timediff", 88.7, "eq", None, cast_to_float=True)

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
        expect_value(self, self.k, "k.hard.hd.user_capacity_f", 500107862016.0, "eq", dd)
        expect_value(self, self.k, "k.hard.hd.reallocated_sector_ct", 0, "eq", dd)
        expect_value(self, self.k, "k.hard.hd.serial_number", "WD-WCC1U0437567", "eq", dd)
        expect_value(self, self.k, "k.hard.hd.health", "KNOCKOK", "eq", dd)
        expect_value(self, self.k, "k.hard.hd.device_model", "WDC WD5000AZRX-00A8LB0", "eq", dd)

        # Check sdb
        dd = {"HDD": "sdb"}
        expect_value(self, self.k, "k.hard.hd.status", None, "exists", dd)
        expect_value(self, self.k, "k.hard.hd.user_capacity_f", 512110190592.0, "eq", dd)
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
        expect_value(self, self.k, "k.os.cpu.util.softirq", int(523697.75), "eq")
        expect_value(self, self.k, "k.os.cpu.util.iowait", int(46485.333333333336), "eq")
        expect_value(self, self.k, "k.os.cpu.util.system", int(737093.5), "eq")
        expect_value(self, self.k, "k.os.cpu.util.idle", int(53666677.5), "eq")
        expect_value(self, self.k, "k.os.cpu.util.user", int(3414344.6666666665), "eq")
        expect_value(self, self.k, "k.os.cpu.util.interrupt", int(0.0), "eq")
        expect_value(self, self.k, "k.os.cpu.util.steal", int(0.0), "eq")
        expect_value(self, self.k, "k.os.cpu.util.nice", int(185.58333333333334), "eq")
        expect_value(self, self.k, "k.os.cpu.switches", int(4943625465), "eq")
        expect_value(self, self.k, "k.os.cpu.intr", int(2495152497), "eq")
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

    @patch('os.statvfs', return_value=os.statvfs_result((4096, 4096, 3920499, 2485124, 2281041, 1001712, 840635, 840635, 4096, 255)))
    @patch('os.stat', return_value=os.stat_result((25008, 12343, 6, 1, 0, 6, 0, 1644476999, 1644476947, 1644476947)))
    @patch('os.major', return_value=254)
    @patch('os.minor', return_value=0)
    def test_from_buffer_diskspace_with_mock(self, mock_statvfs, mock_stat, mock_os_major, mock_os_minor):
        """
        Test
        """
        self.assertIsNotNone(mock_statvfs)
        self.assertIsNotNone(mock_stat)
        self.assertIsNotNone(mock_os_major)
        self.assertIsNotNone(mock_os_minor)

        # Check the mocks
        self.assertEqual(os.statvfs("/tamer").f_blocks, 3920499)
        self.assertEqual(os.stat("/tamer").st_atime, 1644476999)
        self.assertEqual(os.major(0), 254)
        self.assertEqual(os.minor(0), 0)

        # ------------------------------------
        # We must mock
        # - statvfs
        # - os.stat
        # - os.major and os.minor (os.stat mock badly set st_rdev)
        # - stat.S_ISLNK => not in our case
        # - os.path.realpath
        # ------------------------------------

        # Init
        ds = DiskSpace()
        ds.set_manager(self.k)

        # Load files
        fn = self.sample_dir + "diskspace/cmdline.txt"
        with open(fn) as f:
            buf_cmdline = f.read()

        fn = self.sample_dir + "diskspace/diskstats.txt"
        with open(fn) as f:
            buf_diskstats = f.read()

        fn = self.sample_dir + "diskspace/mtab.txt"
        with open(fn) as f:
            buf_mtab = f.read()

        # Process (with mocks)
        ds.process_from_buffer(buf_cmdline, buf_diskstats, buf_mtab)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        ar = ["/var/log", "/var/lib/vbox", "/tmp", "/var", "/home", "/boot", "/usr", "/"]
        for cur_p in ar:
            logger.info("*** Checking, cur_p=%s", cur_p)
            dd = {"FSNAME": cur_p}
            expect_value(self, self.k, "k.vfs.fs.size.free", 9343143936, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.pfree", 58.18, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.inode.pfree", 83.91982925232003, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.total", 16058363904, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.used", 5879296000, "eq", dd)

            expect_value(self, self.k, "k.vfs.dev.read.totalcount", 15843, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalsectorcount", 149362, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalbytes", 76473344, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalms", 10712, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalcount", 985, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalsectorcount", 7840, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalbytes", 4014080, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalms", 464, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.currentcount", 0, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.totalms", 3516, "eq", dd)

        # Check ALL
        for cur_p in ["ALL"]:
            factor = len(ar)
            logger.info("*** Checking, cur_p=%s, factor=%s", cur_p, factor)
            dd = {"FSNAME": cur_p}
            expect_value(self, self.k, "k.vfs.dev.read.totalcount", 15843 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalsectorcount", 149362 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalbytes", 76473344 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalms", 10712 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalcount", 985 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalsectorcount", 7840 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalbytes", 4014080 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalms", 464 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.currentcount", 0 * factor, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.totalms", 3516 * factor, "eq", dd)

    @patch('os.statvfs', return_value=os.statvfs_result((4096, 4096, 3920499, 2485124, 2281041, 1001712, 840635, 840635, 4096, 255)))
    @patch('os.stat', return_value=os.stat_result((25008, 12343, 6, 1, 0, 6, 0, 1644476999, 1644476947, 1644476947)))
    @patch('os.major', return_value=254)
    @patch('os.minor', return_value=0)
    @patch('knockdaemon2.Probes.Os.DiskSpace.get_zpool_io_buffer', return_value=get_zpool_io_buffer_mocked("diskspace/zfs/ZPOOL01_io.txt"))
    def test_from_buffer_diskspace_zfs_with_mock(self, mock_statvfs, mock_stat, mock_os_major, mock_os_minor, mock_get_zpool_io_buffer):
        """
        Test
        """

        self.assertIsNotNone(mock_statvfs)
        self.assertIsNotNone(mock_stat)
        self.assertIsNotNone(mock_os_major)
        self.assertIsNotNone(mock_os_minor)
        self.assertIsNotNone(mock_get_zpool_io_buffer)

        # Check the mocks
        self.assertEqual(os.statvfs("/tamer").f_blocks, 3920499)
        self.assertEqual(os.stat("/tamer").st_atime, 1644476999)
        self.assertEqual(os.major(0), 254)
        self.assertEqual(os.minor(0), 0)

        # ------------------------------------
        # We must mock
        # - statvfs
        # - os.stat
        # - os.major and os.minor (os.stat mock badly set st_rdev)
        # - stat.S_ISLNK => not in our case
        # - os.path.realpath
        # ------------------------------------

        # Init
        ds = DiskSpace()
        ds.set_manager(self.k)

        # Load files
        fn = self.sample_dir + "diskspace/zfs/cmdline.txt"
        with open(fn) as f:
            buf_cmdline = f.read()

        fn = self.sample_dir + "diskspace/zfs/diskstats.txt"
        with open(fn) as f:
            buf_diskstats = f.read()

        fn = self.sample_dir + "diskspace/zfs/mtab.txt"
        with open(fn) as f:
            buf_mtab = f.read()

        # Process (with mocks)
        ds.process_from_buffer(buf_cmdline, buf_diskstats, buf_mtab)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        ar = ["/", "/opt", "/home", "/var", "/boot", "/tmp", "/var/log"]
        for cur_p in ar:
            logger.info("*** Checking, cur_p=%s", cur_p)
            dd = {"FSNAME": cur_p}
            expect_value(self, self.k, "k.vfs.fs.size.free", 9343143936, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.pfree", 58.18, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.inode.pfree", 83.91982925232003, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.total", 16058363904, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.used", 5879296000, "eq", dd)

            expect_value(self, self.k, "k.vfs.dev.read.totalcount", 83794, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalsectorcount", 2267426, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalbytes", 1160922112, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalms", 48884, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalcount", 6942111, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalsectorcount", 57400744, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalbytes", 29389180928, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalms", 7249412, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.currentcount", 0, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.totalms", 2633332, "eq", dd)

        # Check ZFS
        ar_zfs = ["/var/zzz", "/ZPOOL01", "/var/lib/rsyslog"]
        for cur_p in ar_zfs:
            logger.info("*** Checking, cur_p=%s", cur_p)
            dd = {"FSNAME": cur_p}
            expect_value(self, self.k, "k.vfs.fs.size.free", 9343143936, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.pfree", 58.18, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.inode.pfree", 83.91982925232003, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.total", 16058363904, "eq", dd)
            expect_value(self, self.k, "k.vfs.fs.size.used", 5879296000, "eq", dd)

            expect_value(self, self.k, "k.vfs.dev.read.totalcount", 110382657, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalbytes", 6891006030848, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalcount", 609136971, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalbytes", 20120417043456, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.currentcount", 0, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.totalms", 441702066, "eq", dd)

        # Check ALL
        for cur_p in ["ALL"]:
            factor = len(ar)
            factor_zfs = len(ar_zfs)
            logger.info("*** Checking, cur_p=%s, factor=%s", cur_p, factor)
            dd = {"FSNAME": cur_p}
            expect_value(self, self.k, "k.vfs.dev.read.totalcount", 83794 * factor + 110382657 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalsectorcount", 2267426 * factor + 0 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalbytes", 1160922112 * factor + 6891006030848 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.read.totalms", 48884 * factor + 0 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalcount", 6942111 * factor + 609136971 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalsectorcount", 57400744 * factor + 0 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalbytes", 29389180928 * factor + 20120417043456 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.write.totalms", 7249412 * factor + 0 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.currentcount", 0 * factor + 0 * factor_zfs, "eq", dd)
            expect_value(self, self.k, "k.vfs.dev.io.totalms", 2633332 * factor + 441702066 * factor_zfs, "eq", dd)

    @unittest.skipIf(Memory().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % Memory())
    def test_from_buffer_memory(self):
        """
        Test
        """

        # Init
        us = Memory()
        us.set_manager(self.k)

        # Load
        s = self.sample_dir + "memory/meminfo.txt"
        self.assertTrue(FileUtility.is_file_exist(s))
        buf = FileUtility.file_to_textbuffer(s, "utf8")

        # Get
        memory_total, memory_used, swap_total, swap_used, memory_free, swap_free, memory_buffers, memory_cached, memory_available = us.get_mem_info_from_buffer(buf)

        # Notify
        us.notify_mem_info(
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

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.os.swap.size.free", 0, "eq")
        expect_value(self, self.k, "k.os.swap.size.total", 0, "eq")
        expect_value(self, self.k, "k.os.swap.size.used", 0, "eq")
        expect_value(self, self.k, "k.os.swap.size.pfree", 100.0, "eq")

        expect_value(self, self.k, "k.os.memory.size.total", 33538961408, "eq")
        expect_value(self, self.k, "k.os.memory.size.available", 6242091008, "eq")
        expect_value(self, self.k, "k.os.memory.size.buffers", 900038656, "eq")
        expect_value(self, self.k, "k.os.memory.size.cached", 4487995392, "eq")
        expect_value(self, self.k, "k.os.memory.size.used", 26628276224, "eq")
        expect_value(self, self.k, "k.os.memory.size.free", 1522651136, "eq")

        # With override
        self.conf_probe_override["mem_info_file"] = s

        # Exec
        exec_helper(self, Memory)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.os.swap.size.free", 0, "eq")
        expect_value(self, self.k, "k.os.swap.size.total", 0, "eq")
        expect_value(self, self.k, "k.os.swap.size.used", 0, "eq")
        expect_value(self, self.k, "k.os.swap.size.pfree", 100.0, "eq")

        expect_value(self, self.k, "k.os.memory.size.total", 33538961408, "eq")
        expect_value(self, self.k, "k.os.memory.size.available", 6242091008, "eq")
        expect_value(self, self.k, "k.os.memory.size.buffers", 900038656, "eq")
        expect_value(self, self.k, "k.os.memory.size.cached", 4487995392, "eq")
        expect_value(self, self.k, "k.os.memory.size.used", 26628276224, "eq")
        expect_value(self, self.k, "k.os.memory.size.free", 1522651136, "eq")

    @patch('knockdaemon2.Probes.Os.ProcNum.get_proc_list', return_value=["1", "2", "3", "zzz"])
    @patch('knockdaemon2.Probes.Os.ProcNum.is_dir', return_value=True)
    @patch('knockdaemon2.Probes.Os.ProcNum.read_file_line', return_value="z")
    def test_from_buffer_numberofprocesses_with_mock(self, m1, m2, m3):
        """
        Test
        """
        self.assertIsNotNone(m1)
        self.assertIsNotNone(m2)
        self.assertIsNotNone(m3)

        # Init
        np = NumberOfProcesses()
        np.set_manager(self.k)

        # Go
        np.execute()

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.os.processes.total", 3, "eq")

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

    def test_from_buffer_netstat(self):
        """
        Test
        """

        # Init
        ns = Netstat()
        ns.set_manager(self.k)

        # Load files
        fn = self.sample_dir + "netstat/proc_net_tcp.txt"
        self.assertTrue(FileUtility.is_file_exist(fn))
        proc_net_tcp = FileUtility.file_to_textbuffer(fn, "utf8")
        ar_proc_net_tcp = proc_net_tcp.split("\n")

        fn = self.sample_dir + "netstat/nf_conntrack_count.txt"
        self.assertTrue(FileUtility.is_file_exist(fn))
        nf_conntrack_count = float(FileUtility.file_to_textbuffer(fn, "utf8"))
        self.assertEqual(nf_conntrack_count, 100.0)

        fn = self.sample_dir + "netstat/nf_conntrack_max.txt"
        self.assertTrue(FileUtility.is_file_exist(fn))
        nf_conntrack_max = float(FileUtility.file_to_textbuffer(fn, "utf8"))
        self.assertEqual(nf_conntrack_max, 200.0)

        ns.process_net_tcp_from_list(ar_proc_net_tcp)
        ns.process_conntrack(nf_conntrack_count, nf_conntrack_max)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        expect_value(self, self.k, "k.net.netstat.SYN_SENT", 0, "eq")
        expect_value(self, self.k, "k.net.netstat.LISTEN", 58, "eq")
        expect_value(self, self.k, "k.net.netstat.TIME_WAIT", 58, "eq")
        expect_value(self, self.k, "k.net.netstat.SYN_RECV", 0, "eq")
        expect_value(self, self.k, "k.net.netstat.LAST_ACK", 0, "eq")
        expect_value(self, self.k, "k.net.netstat.CLOSE_WAIT", 16, "eq")
        expect_value(self, self.k, "k.net.netstat.CLOSED", 0, "eq")
        expect_value(self, self.k, "k.net.netstat.FIN_WAIT2", 0, "eq")
        expect_value(self, self.k, "k.net.netstat.FIN_WAIT1", 0, "eq")
        expect_value(self, self.k, "k.net.netstat.ESTABLISHED", 84, "eq")
        expect_value(self, self.k, "k.net.netstat.CLOSING", 0, "eq")

        expect_value(self, self.k, "k.net.conntrack.count", 100.0, "eq")
        expect_value(self, self.k, "k.net.conntrack.max", 200.0, "eq")
        expect_value(self, self.k, "k.net.conntrack.used", 50.0, "eq")

    @patch('knockdaemon2.Probes.Os.Network.Network.get_interface_status_from_socket', return_value="up")
    def test_from_buffer_network(self, m1):
        """
        Test
        """
        self.assertIsNotNone(m1)

        # Init
        ns = Network()
        ns.set_manager(self.k)

        d_expect = {
            "wlo1": {
                "k.net.if.status.status": "ok",
                "k.net.if.status.speed": 1000,
                "k.eth.bytes.recv": 363777128,
                "k.eth.bytes.sent": 72638640,
                "k.net.if.status.duplex": "full",
                "k.net.if.type": "Ethernet",
                "k.net.if.status.mtu": 1500,
                "k.net.if.status.tx_queue_len": 1000,
                "k.eth.errors.recv": 0,
                "k.eth.errors.sent": 0,
                "k.eth.missederrors.recv": 0,
                "k.eth.packet.recv": 520883,
                "k.eth.packet.sent": 293213,
                "k.eth.packetdrop.recv": 0,
                "k.eth.packetdrop.sent": 0,
                "k.net.if.collisions": 0,
            },
            "eno2": {
                "k.net.if.status.status": "ok",
                "k.net.if.status.speed": -1,
                "k.eth.bytes.recv": 0,
                "k.eth.bytes.sent": 0,
                "k.net.if.status.duplex": "unknown",
                "k.net.if.type": "Ethernet",
                "k.net.if.status.mtu": 1500,
                "k.net.if.status.tx_queue_len": 1000,
                "k.eth.errors.recv": 0,
                "k.eth.errors.sent": 0,
                "k.eth.missederrors.recv": 0,
                "k.eth.packet.recv": 0,
                "k.eth.packet.sent": 0,
                "k.eth.packetdrop.recv": 0,
                "k.eth.packetdrop.sent": 0,
                "k.net.if.collisions": 0,
            },
            "docker0": {
                "k.net.if.status.status": "ok",
                "k.net.if.status.speed": 1000,
                "k.eth.bytes.recv": 0,
                "k.eth.bytes.sent": 0,
                "k.net.if.status.duplex": "full",
                "k.net.if.type": "Ethernet",
                "k.net.if.status.mtu": 1500,
                "k.net.if.status.tx_queue_len": 0,
                "k.eth.errors.recv": 0,
                "k.eth.errors.sent": 0,
                "k.eth.missederrors.recv": 0,
                "k.eth.packet.recv": 0,
                "k.eth.packet.sent": 0,
                "k.eth.packetdrop.recv": 0,
                "k.eth.packetdrop.sent": 0,
                "k.net.if.collisions": 0,
            },
            "lo": {
                "k.net.if.status.status": "ok",
                "k.net.if.status.speed": 1000,
                "k.eth.bytes.recv": 265052542,
                "k.eth.bytes.sent": 265054283,
                "k.net.if.status.duplex": "full",
                "k.net.if.type": "LoopBack",
                "k.net.if.status.mtu": 65536,
                "k.net.if.status.tx_queue_len": 1000,
                "k.eth.errors.recv": 0,
                "k.eth.errors.sent": 0,
                "k.eth.missederrors.recv": 0,
                "k.eth.packet.recv": 1671728,
                "k.eth.packet.sent": 1671736,
                "k.eth.packetdrop.recv": 0,
                "k.eth.packetdrop.sent": 0,
                "k.net.if.collisions": 0,
            }
        }

        # Browse samples
        interfaces = glob.glob(self.sample_dir + "network/sys/class/net/*")
        for interface_dir in interfaces:
            # GET : name
            interface_name = os.path.basename(interface_dir)
            logger.info("*** Testing, name=%s, dir=%s", interface_name, interface_dir)

            # RESET
            self.k._reset_superv_notify()
            Meters.reset()

            # READ : /type
            n_local_type = int(ns.try_read(interface_dir + "/type", default=-1))

            # READ : operstate
            operstate = ns.try_read(interface_dir + "/operstate", default="")

            # READ : address
            address = ns.try_read(interface_dir + "/address", default=None)

            # READ : carrier
            carrier = ns.try_read(interface_dir + "/carrier", default=None)

            # READ : rx_bytes / tx_bytes
            recv = int(ns.try_read(interface_dir + "/statistics/rx_bytes", default=0))
            sent = int(ns.try_read(interface_dir + "/statistics/tx_bytes", default=0))

            # READ : duplex
            duplex = ns.try_read(interface_dir + "/duplex", default="full")

            # READ : speed
            speed = int(ns.try_read(interface_dir + "/speed", default="1000"))

            # READ : mtu
            mtu = int(ns.try_read(interface_dir + "/mtu", default="0"))

            # READ : tx_queue_len
            tx_queue_len = int(ns.try_read(interface_dir + "/tx_queue_len", default="0"))

            # READ : statistics
            rx_errors = int(ns.try_read(interface_dir + "/statistics/rx_errors", default="0"))
            tx_errors = int(ns.try_read(interface_dir + "/statistics/tx_errors", default="0"))
            rx_packets = int(ns.try_read(interface_dir + "/statistics/rx_packets", default="0"))
            tx_packets = int(ns.try_read(interface_dir + "/statistics/tx_packets", default="0"))
            rx_dropped = int(ns.try_read(interface_dir + "/statistics/rx_dropped", default="0"))
            tx_dropped = int(ns.try_read(interface_dir + "/statistics/tx_dropped", default="0"))
            collisions = int(ns.try_read(interface_dir + "/statistics/collisions", default="0"))
            rx_missed_errors = int(ns.try_read(interface_dir + "/statistics/rx_missed_errors", default="0"))

            # READ VIA SOCKET if not UP
            if operstate != "up":
                operstate = ns.get_interface_status_from_socket(interface_name)

            # PROCESS IT
            ns.process_interface_from_datas(
                interface_name=interface_name,
                carrier=carrier,
                n_local_type=n_local_type,
                address=address,
                operstate=operstate,
                speed=speed,
                recv=recv,
                sent=sent,
                duplex=duplex,
                mtu=mtu,
                tx_queue_len=tx_queue_len,
                rx_errors=rx_errors, tx_errors=tx_errors,
                rx_missed_errors=rx_missed_errors,
                rx_packets=rx_packets, tx_packets=tx_packets,
                rx_dropped=rx_dropped, tx_dropped=tx_dropped,
                collisions=collisions,
            )

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Check
            dd = {"IFNAME": interface_name}
            for k, v in d_expect[interface_name].items():
                expect_value(self, self.k, k, v, "eq", dd)

    def test_from_buffer_inventory(self):
        """
        Test
        """

        # Get
        (sysname, nodename, kernel, version, machine) = os.uname()
        distribution = distro.id()
        dversion = distro.version()

        # Load
        fn = self.sample_dir + "inventory/dmidecode.txt"
        self.assertTrue(FileUtility.is_file_exist(fn))
        buf_dmidecode = FileUtility.file_to_textbuffer(fn, "utf8")

        fn = self.sample_dir + "inventory/dmesg.txt"
        self.assertTrue(FileUtility.is_file_exist(fn))
        buf_dmesg = FileUtility.file_to_textbuffer(fn, "utf8")

        # Init
        iv = Inventory()
        iv.set_manager(self.k)

        # Process
        iv.process_from_data(buf_dmidecode, buf_dmesg)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.inventory.os", "%s %s %s" % (sysname, distribution, dversion), "eq", cast_to_float=False)
        expect_value(self, self.k, "k.inventory.kernel", kernel, "eq")
        expect_value(self, self.k, "k.inventory.name", nodename, "eq")
        expect_value(self, self.k, "k.inventory.vendor", "Dell Inc.", "eq")
        expect_value(self, self.k, "k.inventory.mem", "2 memory stick(s), 32768 MB in total, Max 32 GB", "eq")
        expect_value(self, self.k, "k.inventory.system", "Dell Inc. Latitude 5591 (SN: TAMER, UUID: TAMER)", "eq")
        expect_value(self, self.k, "k.inventory.chassis", "Notebook", "eq")
        expect_value(self, self.k, "k.inventory.serial", "TAMER", "eq")
        expect_value(self, self.k, "k.inventory.cpu", "Intel(R) Corporation Core i7 4300 MHz (Core: 6, Thead: 12)", "eq")

    def test_from_buffer_uptime(self):
        """
        Test
        """

        # Init
        ut = Uptime()
        ut.set_manager(self.k)

        # Load
        fn = self.sample_dir + "uptime/uptime.txt"
        self.assertTrue(FileUtility.is_file_exist(fn))
        buf = FileUtility.file_to_textbuffer(fn, "utf8")

        # Process
        ut.process_uptime_buffer(buf)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.os.knock", 1, "eq")
        expect_value(self, self.k, "k.os.uptime", 24625, "eq")

    def test_from_buffer_mdstat(self):
        """
        Test
        """

        # Init
        ms = Mdstat()
        ms.set_manager(self.k)

        # Process from path
        ms.process_from_path(self.sample_dir + "mdstat/mdstat.txt")

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        expect_value(self, self.k, "k.os.disk.mdstat", 0, "eq", {"md": "md1"})
        expect_value(self, self.k, "k.os.disk.mdstat", 0, "eq", {"md": "md5"})

    def test_from_buffer_ipvsadm(self):
        """
        Test
        """

        # Init
        ia = IpvsAdm()
        ia.set_manager(self.k)

        # Load
        fn = self.sample_dir + "ipvsadm/ip_vs.txt"
        self.assertTrue(FileUtility.is_file_exist(fn))
        buf = FileUtility.file_to_textbuffer(fn, "utf8")

        # Process it
        ia.process_ipvsadm_buffer(buf)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        dd = {"VIP": "10.4.103.40:11406"}
        expect_value(self, self.k, "knock.ipvsadm.activerip", "10.66.103.21:11406 - 10.66.103.20:11406", "eq", dd)
        expect_value(self, self.k, "knock.ipvsadm.weightRip", 2, "eq", dd)
        expect_value(self, self.k, "knock.ipvsadm.activeConRip", 0, "eq", dd)
        expect_value(self, self.k, "knock.ipvsadm.InActConnRip", 0, "eq", dd)
        dd = {"VIP": "ALL"}
        expect_value(self, self.k, "knock.ipvsadm.activerip", "10.66.103.21:11406 - 10.66.103.20:11406", "eq", dd)
        expect_value(self, self.k, "knock.ipvsadm.weightRip", 2, "eq", dd)
        expect_value(self, self.k, "knock.ipvsadm.activeConRip", 0, "eq", dd)
        expect_value(self, self.k, "knock.ipvsadm.InActConnRip", 0, "eq", dd)

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

    @patch('knockdaemon2.Probes.Os.CheckProcess.read_pid', return_value=99999)
    @patch('knockdaemon2.Probes.Os.CheckProcess.call_psutil_process', return_value=None)
    @patch('knockdaemon2.Probes.Os.CheckProcess.get_process_stat', return_value=get_checkprocess_process_stat_mocked())
    @patch('knockdaemon2.Probes.Os.CheckProcess.get_io_counters', return_value=get_checkprocess_io_counters_mocked())
    @patch('knockdaemon2.Probes.Os.CheckProcess.get_process_list', return_value=get_checkprocess_process_list_mocked())
    def test_from_buffer_checkprocess_with_mock(self, m1, m2, m3, m4, m5):
        """
        Test
        """
        self.assertIsNotNone(m1)
        self.assertIsNotNone(m2)
        self.assertIsNotNone(m3)
        self.assertIsNotNone(m4)
        self.assertIsNotNone(m5)

        # Init
        cp = CheckProcess()
        cp.set_manager(self.k)
        cp.load_json_config(self.current_dir + "/conf/realall/k.CheckProcess.json")

        # Go
        cp.execute()

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # Check
        for cur_p in ["nginx", "nginx_array"]:
            dd = {"PROCNAME": cur_p}
            expect_value(self, self.k, "k.proc.pidfile", "ok", "eq", dd)
            expect_value(self, self.k, "k.proc.running", "ok", "eq", dd)
            expect_value(self, self.k, "k.proc.io.read_bytes", 77, "eq", dd)
            expect_value(self, self.k, "k.proc.io.write_bytes", 88, "eq", dd)
            expect_value(self, self.k, "k.proc.io.num_fds", 10 * 2, "eq", dd)
            expect_value(self, self.k, "k.proc.memory_used", 1736704 * 2, "eq", dd)
            expect_value(self, self.k, "k.proc.cpu_used", 3.0 * 2, "eq", dd)
            expect_value(self, self.k, "k.proc.nbprocess", 2, "eq", dd)

    def test_from_buffer_mysql(self):
        """
        Test
        """

        # Init
        m = Mysql()
        m.set_manager(self.k)

        # Go
        for f_status, f_variables, f_slave, f_user_stat, f_table_stat, f_index_stat, f_inno_table_stat in [
            (
                    "mysql/status.out", "mysql/variables.out", "mysql/slave.out",
                    "mysql/USER_STATISTICS.out", "mysql/TABLE_STATISTICS.out", "mysql/INDEX_STATISTICS.out", "mysql/innodb_table_stats.out",
            ),
        ]:
            # Path
            f_status = self.sample_dir + f_status
            f_variables = self.sample_dir + f_variables
            f_slave = self.sample_dir + f_slave

            f_user_stat = self.sample_dir + f_user_stat
            f_table_stat = self.sample_dir + f_table_stat
            f_index_stat = self.sample_dir + f_index_stat
            f_inno_table_stat = self.sample_dir + f_inno_table_stat

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

            self.assertTrue(FileUtility.is_file_exist(f_user_stat))
            user_stat_buf = FileUtility.file_to_textbuffer(f_user_stat, "utf8")
            self.assertTrue(FileUtility.is_file_exist(f_table_stat))
            table_stat_buf = FileUtility.file_to_textbuffer(f_table_stat, "utf8")
            self.assertTrue(FileUtility.is_file_exist(f_index_stat))
            index_stat_buf = FileUtility.file_to_textbuffer(f_index_stat, "utf8")
            self.assertTrue(FileUtility.is_file_exist(f_inno_table_stat))
            inno_table_stat_buf = FileUtility.file_to_textbuffer(f_inno_table_stat, "utf8")

            # Switch to list - status
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

            # Switch to list - variables
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

            # Switch to list - slave
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

            # Switch to list - user_stat_buf / table_stat_buf / index_stat_buf / inno_table_stat_buf
            ar_user_stats = list()
            ar_table_stats = list()
            ar_index_stats = list()
            ar_innodb_table_stats = list()
            for s_type, header, ar_out, buf_in in [
                ("ar_user_stats", "| USER", ar_user_stats, user_stat_buf),
                ("ar_table_stats", "| TABLE_SCHEMA ", ar_table_stats, table_stat_buf),
                ("ar_index_stats", "| TABLE_SCHEMA ", ar_index_stats, index_stat_buf),
                ("ar_innodb_table_stats", "| database_name", ar_innodb_table_stats, inno_table_stat_buf),
            ]:
                ar_fields = None
                for s in buf_in.split("\n"):
                    s = s.strip()
                    if not s.startswith("|"):
                        continue
                    elif s.startswith(header):
                        # headers / fields
                        ar_fields = s.split("|")
                        for i in range(0, len(ar_fields) - 1):
                            ar_fields[i] = ar_fields[i].strip()
                    else:
                        if ar_fields is None:
                            raise Exception("ar_fields None, cannot process (bug), type=%s" % s_type)
                        # data
                        d = dict()
                        ar = s.split("|")
                        for i in range(0, len(ar) - 1):
                            field_name = ar_fields[i]
                            v = ar[i].strip()
                            d[field_name] = v
                        ar_out.append(d)

            # Process
            m.process_mysql_buffers(
                ar_status, ar_slave, ar_variables,
                ar_table_stats, ar_user_stats, ar_index_stats,
                ar_innodb_table_stats,
                "default",
                22)

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

            # Check, stat, table
            for schema, table, rows_read, rows_changed, rows_changed_index in [
                ("db01", "ta", 1565, 3, 6),
                ("db01", "tb", 1566, 4, 7),
                ("db02", "tc", 16156788, 174, 348),
                ("db02", "td", 16156789, 175, 349),
            ]:
                dd = {"ID": "default", "schema": schema, "table": table}
                expect_value(self, self.k, "k.mysql.stats.table.ROWS_READ", float(rows_read), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.table.ROWS_CHANGED", float(rows_changed), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.table.ROWS_CHANGED_X_INDEXES", float(rows_changed_index), "eq", dd, )

            # Check, stat, user
            for user, total_connections, concurrent_connections, connected_time, busy_time, cpu_time, \
                bytes_received, bytes_sent, \
                binlog_bytes_written, rows_read, rows_sent, rows_deleted, rows_inserted, rows_updated, \
                select_commands, update_commands, other_commands, commit_transactions, rollback_transactions, \
                denied_connections, lost_connections, access_denied, \
                empty_queries, total_ssl_connections, max_statement_time_exceeded in \
                    [
                        ("zzzz", 11, 0, 3210, 0.07573099999999999, 0.05983699999999998, 28856, 382005, 0, 20077, 2700, 0, 0, 0, 111, 0, 116, 32, 2, 1, 0, 1, 25, 0, 0,),
                        ("user01", 911622, 0, 51057853, 103307.76056384486, 86972.37930978586, 256376400310, 508652204841, 660864536, 1663804892, 475976244, 130374, 207514, 701465, 384027899, 1480665, 300725032, 959443523, 39760, 0, 0, 0, 241005297, 0, 0,),
                        ("user02", 69, 0, 1202740, 58.081382000000936, 57.86767730000072, 1791136, 547008082, 0, 0, 12555625, 0, 0, 0, 0, 0, 112, 0, 0, 0, 0, 0, 0, 0, 0,),

                    ]:
                dd = {"ID": "default", "user": user}
                expect_value(self, self.k, "k.mysql.stats.user.TOTAL_CONNECTIONS", float(total_connections), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.CONCURRENT_CONNECTIONS", float(concurrent_connections), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.CONNECTED_TIME", float(connected_time), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.BUSY_TIME", float(busy_time), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.CPU_TIME", float(cpu_time), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.BYTES_RECEIVED", float(bytes_received), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.BYTES_SENT", float(bytes_sent), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.BINLOG_BYTES_WRITTEN", float(binlog_bytes_written), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.ROWS_READ", float(rows_read), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.ROWS_SENT", float(rows_sent), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.ROWS_DELETED", float(rows_deleted), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.ROWS_INSERTED", float(rows_inserted), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.ROWS_UPDATED", float(rows_updated), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.SELECT_COMMANDS", float(select_commands), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.UPDATE_COMMANDS", float(update_commands), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.OTHER_COMMANDS", float(other_commands), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.COMMIT_TRANSACTIONS", float(commit_transactions), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.ROLLBACK_TRANSACTIONS", float(rollback_transactions), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.DENIED_CONNECTIONS", float(denied_connections), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.LOST_CONNECTIONS", float(lost_connections), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.ACCESS_DENIED", float(access_denied), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.EMPTY_QUERIES", float(empty_queries), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.TOTAL_SSL_CONNECTIONS", float(total_ssl_connections), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.user.MAX_STATEMENT_TIME_EXCEEDED", float(max_statement_time_exceeded), "eq", dd, )

            # Check, stat, index
            for schema, table, index, rows_read in [
                ("db01", "ta", "PRIMARY", 8,),
                ("db01", "ta", "idxa", 56027,),
                ("db01", "tb", "PRIMARY", 9,),
                ("db01", "tb", "idxb", 56028,),
                ("db02", "tc", "PRIMARY", 10,),
                ("db02", "tc", "idxc", 56029,),
                ("db02", "td", "PRIMARY", 11,),
                ("db02", "td", "idxd", 56030,),
            ]:
                dd = {"ID": "default", "schema": schema, "table": table, "index": index}
                expect_value(self, self.k, "k.mysql.stats.index.ROWS_READ", float(rows_read), "eq", dd, )

            # Check, stat, innodb, table
            for schema, table, _, n1, n2, n3 in [
                ("db01", "ta", "2022-07-27 22:10:29", 8, 1, 10),
                ("db01", "ta", "2022-07-27 22:10:29", 37, 2, 11),
                ("db02", "tb", "2022-07-27 22:10:29", 9, 3, 12),
                ("db02", "tb", "2022-07-27 22:10:29", 38, 4, 13),
            ]:
                dd = {"ID": "default", "schema": schema, "table": table}
                expect_value(self, self.k, "k.mysql.stats.innodb_table.n_rows", float(n1), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.innodb_table.clustered_index_size", float(n2), "eq", dd, )
                expect_value(self, self.k, "k.mysql.stats.innodb_table.sum_of_other_index_sizes", float(n3), "eq", dd, )

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
            buf = MongoDbStat.mongo_cleanup_buffer(buf)
            d_json = json.loads(buf)

            md.process_mongo_server_status(d_json, str(cur_port))

            # Log
            for tu in self.k.superv_notify_value_list:
                logger.info("Having tu=%s", tu)

            # Check
            dd = {'PORT': str(cur_port)}
            cur_port += 1

            for k, v in d_expected.items():
                expect_value(self, self.k, k, v, "eq", dd)

        # Per db / col
        self.k._reset_superv_notify()
        for db in ["my_db"]:
            # db
            fn = self.sample_dir + "mongodb/mongo_dbstats.out"
            self.assertTrue(FileUtility.is_file_exist(fn))
            buf = FileUtility.file_to_textbuffer(fn, "utf8")
            md.process_from_buffer_db(cur_port, db, buf)

            for col in ["my_col"]:
                # col
                fn = self.sample_dir + "mongodb/mongo_collstats.out"
                self.assertTrue(FileUtility.is_file_exist(fn))
                buf = FileUtility.file_to_textbuffer(fn, "utf8")
                md.process_from_buffer_col(cur_port, db, col, buf)

        # Log
        for tu in self.k.superv_notify_value_list:
            logger.info("Having tu=%s", tu)

        # CHECK DB
        dd = {'PORT': str(cur_port), "DB": "my_db"}
        for k_expected, v_expected in {
            "k.mongodb.db.collections": 1.0,
            "k.mongodb.db.objects": 400000.0,
            "k.mongodb.db.avgObjSize": 58.0,
            "k.mongodb.db.dataSize": 23200000.0,
            "k.mongodb.db.storageSize": 15179776.0,
            "k.mongodb.db.indexes": 3.0,
            "k.mongodb.db.indexSize": 17924096.0,
            "k.mongodb.db.fsUsedSize": 26165620736.0,
            "k.mongodb.db.fsTotalSize": 33756561408.0,
        }.items():
            expect_value(self, self.k, k_expected, v_expected, "eq", dd)

        # CHECK COL
        dd = {'PORT': str(cur_port), "DB": "my_db", "COL": "my_col"}
        for k_expected, v_expected in {
            "k.mongodb.col.size": 23200000.0,
            "k.mongodb.col.count": 400000.0,
            "k.mongodb.col.avgObjSize": 58.0,
            "k.mongodb.col.storageSize": 15179776.0,
            "k.mongodb.col.totalIndexSize": 17924096.0,
            "k.mongodb.col.nindexes": 3.0,
        }.items():
            expect_value(self, self.k, k_expected, v_expected, "eq", dd)

        # CHECK COL, IDX
        for k_expected, v_expected in {
            "k.mongodb.col.idx.indexSizes": 3764224.0,

            "k.mongodb.col.idx.detail.bytes_currently_in_the_cache": 101.0,
            "k.mongodb.col.idx.detail.bytes_read_into_cache": 102.0,
            "k.mongodb.col.idx.detail.bytes_written_from_cache": 103.0,
            "k.mongodb.col.idx.detail.pages_read_into_cache": 104.0,
            "k.mongodb.col.idx.detail.pages_requested_from_the_cache": 105.0,
            "k.mongodb.col.idx.detail.pages_written_from_cache": 106.0,
            "k.mongodb.col.idx.detail.internal_pages_evicted": 107.0,
            "k.mongodb.col.idx.detail.modified_pages_evicted": 108.0,
            "k.mongodb.col.idx.detail.unmodified_pages_evicted": 109.0,

            "k.mongodb.col.idx.cursor.create_calls": 201.0,
            "k.mongodb.col.idx.cursor.insert_calls": 202.0,
            "k.mongodb.col.idx.cursor.insert_key_and_value_bytes": 203.0,
            "k.mongodb.col.idx.cursor.next_calls": 204.0,
            "k.mongodb.col.idx.cursor.prev_calls": 205.0,
            "k.mongodb.col.idx.cursor.remove_calls": 206.0,
            "k.mongodb.col.idx.cursor.remove_key_bytes_removed": 207.0,
            "k.mongodb.col.idx.cursor.reserve_calls": 208.0,
            "k.mongodb.col.idx.cursor.reset_calls": 209.0,
            "k.mongodb.col.idx.cursor.search_calls": 210.0,
            "k.mongodb.col.idx.cursor.search_near_calls": 211.0,
            "k.mongodb.col.idx.cursor.truncate_calls": 212.0,
            "k.mongodb.col.idx.cursor.update_calls": 213.0,
            "k.mongodb.col.idx.cursor.update_key_and_value_bytes": 214.0,

        }.items():
            # _id_
            dd = {'PORT': str(cur_port), "DB": "my_db", "COL": "my_col", "IDX": "_id_"}
            expect_value(self, self.k, k_expected, v_expected, "eq", dd)

            # other ones (don't check values)
            for idx in ["IDX_a_1_b_1_", "IDX_a_1_b_1_d_1_"]:
                dd = {'PORT': str(cur_port), "DB": "my_db", "COL": "my_col", "IDX": idx}
                expect_value(self, self.k, k_expected, v_expected, "exists", dd)

        self.k._reset_superv_notify()
