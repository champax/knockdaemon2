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
import shutil
import unittest
from os.path import dirname, abspath

import redis
# noinspection PyUnresolvedReferences,PyPackageRequirements
from nose.plugins.attrib import attr
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.HttpMock.HttpMock import HttpMock
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Probes.Apache.ApacheStat import ApacheStat
from knockdaemon2.Probes.Mysql.Mysql import Mysql
from knockdaemon2.Probes.Nginx.NGinxStat import NginxStat
from knockdaemon2.Probes.Os.CheckDns import CheckDns
from knockdaemon2.Probes.Os.DiskSpace import DiskSpace
from knockdaemon2.Probes.Os.Load import Load
from knockdaemon2.Probes.Os.Memory import Memory
from knockdaemon2.Probes.Os.NetStat import Netstat
from knockdaemon2.Probes.Os.Network import Network
from knockdaemon2.Probes.Os.ProcNum import NumberOfProcesses
from knockdaemon2.Probes.Os.UpTime import Uptime
from knockdaemon2.Probes.PhpFpm.PhpFpmStat import PhpFpmStat
from knockdaemon2.Probes.Uwsgi.UwsgiStat import UwsgiStat
from knockdaemon2.Probes.Varnish.VarnishStat import VarnishStat
from knockdaemon2.Transport.InfluxAsyncTransport import InfluxAsyncTransport

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


@attr('prov')
class TestRealAll(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.k = None
        self.h = None

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.manager_config_file = self.current_dir + "conf" + SolBase.get_pathseparator() + "realall" + SolBase.get_pathseparator() + "knockdaemon2.yaml"
        self.k = None

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
        self.manager_config_file = PTools.get_tmp_dir() + SolBase.get_pathseparator() + "knockdaemon2.yaml"

        # Reset meter
        Meters.reset()

        # Debug stat on exit ?
        self.debug_stat = False

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

    def tearDown(self):
        """
        Setup (called after each test)
        """
        if self.k:
            logger.warning("k set, stopping, not normal")
            self.k.stop()
            self.k = None

        if self.h:
            logger.warning("h set, stopping, not normal")
            self.h.stop()
            self.h = None

        if self.debug_stat:
            Meters.write_to_logger()

    def _stop_all(self):
        """
        Test
        """

        if self.h:
            self.h.stop()
            self.h = None

        if self.k:
            self.k = None

    def _start_all(self):
        """
        Test
        """

        # Meters.reset()
        self._start_http_mock()
        self._start_manager()

    def _start_http_mock(self):
        """
        Test
        """
        self.h = HttpMock()
        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

    def _start_manager(self):
        """
        Test
        """

        # Init manager
        self.k = KnockManager(self.manager_config_file)

        # Do NOT Start
        pass

    # noinspection PyMethodMayBeStatic
    def fullname(self, o):
        """
        Test
        :param o: test
        :return: test
        """
        return o.__module__ + "." + o.__class__.__name__

    def _validate_internal(self, p, timeout_ms=90000):
        """
        Test
        :param p: KnockProbe
        :param timeout_ms: int
        :return:
        """

        # Start, without starting manager, then cleanup manager probe list
        self._start_all()
        self.h._paranoid_enabled = True
        self.k._probe_list = list()
        self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_send_min_interval_ms = 1000
        self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_network_timeout_ms = 60000

        # Meters prefix, first transport
        self.ft_meters_prefix = self.k.get_first_meters_prefix_by_type(InfluxAsyncTransport)

        # Init our probes
        i_count = 0
        for k, d in self.k._d_yaml_config["probes"].items():
            class_name = d["class_name"]
            f_name = self.fullname(p)
            if class_name == f_name:
                self.k._init_probe_internal(k, d, p)
                i_count += 1
        self.assertEqual(i_count, 1)

        # Ok, probe ready, manager started by executing nothing : execute our probe
        # The probe will notify manager
        loop_idx = -1
        ms_start_loop = SolBase.mscurrent()
        while SolBase.msdiff(ms_start_loop) < timeout_ms:
            loop_idx += 1
            logger.info("***** EXEC PASS ONE [%s]", loop_idx)

            # Reset all counters
            Meters.reset()

            # Execute
            p.execute()

            # Check how many disco do we have
            disco_count = len(self.k._superv_notify_disco_hash)
            for (superv_key, dd, v, timestamp, d_opt_tags) in self.k._superv_notify_value_list:
                if superv_key.find(".discovery") >= 0:
                    disco_count += 1

            # Manager : request a send
            self.k._process_superv_notify()

            # Wait for everything pushed and processed
            logger.info("***** WAITING PASS ONE [%s]", loop_idx)
            timeout_ms = timeout_ms
            ms_start = SolBase.mscurrent()
            while SolBase.msdiff(ms_start) < timeout_ms:
                if self.k.get_first_transport_by_type(InfluxAsyncTransport)._queue_to_send.qsize() == 0 \
                        and not self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_pending:
                    break
                else:
                    SolBase.sleep(100)

            # If we got at least disco_count + 1 ok, we are fine
            processed_ok = Meters.aig(self.ft_meters_prefix + "knock_stat_transport_spv_processed")
            if processed_ok > disco_count:
                logger.info(
                    "Success, having=%s, target=%s, delay=%s",
                    processed_ok,
                    disco_count + 1,
                    SolBase.msdiff(ms_start_loop)
                )
                break

            # NOT OK
            logger.warning(
                "Re-looping, having=%s, target=%s",
                processed_ok,
                disco_count + 1
            )

        self.assertGreaterEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_ok_count"), 1)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_exception_count"), 0)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_failed_count"), 0)
        self.assertEqual(self.k.get_first_transport_by_type(InfluxAsyncTransport)._queue_to_send.qsize(), 0)
        self.assertFalse(self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_pending)

        # Ok, here.... let's play... we reset ALL counters
        logger.info("***** EXEC PASS TWO")
        Meters.reset()

        # Fire LAST execution
        p.execute()
        self.k._process_superv_notify()

        # Wait for transport
        logger.info("***** WAITING PASS TWO")
        timeout_ms = timeout_ms
        ms_start = SolBase.mscurrent()
        while SolBase.msdiff(ms_start) < timeout_ms:
            if Meters.aig(self.ft_meters_prefix + "knock_stat_transport_ok_count") == 1 \
                    and self.k.get_first_transport_by_type(InfluxAsyncTransport)._queue_to_send.qsize() == 0 \
                    and not self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_pending:
                break
            else:
                SolBase.sleep(100)

        # Validate the stuff
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_ok_count"), 1)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_exception_count"), 0)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_failed_count"), 0)
        self.assertEqual(self.k.get_first_transport_by_type(InfluxAsyncTransport)._queue_to_send.qsize(), 0)
        self.assertFalse(self.k.get_first_transport_by_type(InfluxAsyncTransport)._http_pending)
        self.assertGreaterEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_spv_processed"), 1)
        self.assertEqual(Meters.aig(self.ft_meters_prefix + "knock_stat_transport_spv_failed"), 0)
        self.assertEqual(
            Meters.aig(self.ft_meters_prefix + "knock_stat_transport_spv_total"),
            Meters.aig(self.ft_meters_prefix + "knock_stat_transport_spv_processed"))

        self.assertGreaterEqual(
            Meters.aig(self.ft_meters_prefix + "knock_stat_transport_spv_processed"),
            Meters.aig(self.ft_meters_prefix + "knock_stat_notify_simple_value") +
            Meters.aig(self.ft_meters_prefix + "knock_stat_notify_value")
        )

        logger.info("***** SUCCESS PASS TWO")

    @unittest.skipIf(Netstat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_netstat(self):
        """
        Test
        :return:
        """

        logger.info("GO")

        self._validate_internal(Netstat())

    @unittest.skipIf(VarnishStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_varnish(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        self._validate_internal(VarnishStat())

    @unittest.skipIf(UwsgiStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_uwsgi(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        self._validate_internal(UwsgiStat())

    @unittest.skipIf(Mysql().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_mysql(self):
        """
        Test
        :return:
        """

        logger.info("GO")

        self._validate_internal(Mysql())

    @unittest.skipIf(Load().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_load(self):
        """
        Test
        :return:
        """

        logger.info("GO")

        self._validate_internal(Load())

    @unittest.skipIf(Memory().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_memory(self):
        """
        Test
        :return:
        """

        logger.info("GO")

        self._validate_internal(Memory())

    @unittest.skipIf(Network().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_network(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        self._validate_internal(Network())

    @unittest.skipIf(NumberOfProcesses().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_procnum(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        self._validate_internal(NumberOfProcesses())

    @unittest.skipIf(Uptime().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_uptime(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        self._validate_internal(Uptime())

    @unittest.skipIf(DiskSpace().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_diskspace(self):
        """
        Test
        :return:
        """

        logger.info("GO")

        self._validate_internal(DiskSpace())

    @unittest.skipIf(CheckDns().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_checkdns(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        self._validate_internal(CheckDns())

    @unittest.skipIf(ApacheStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_apache(self):
        """
        Test
        :return:
        """

        logger.info("GO")

        from gevent import pywsgi

        def http_process(request, response):
            """
            Internal http method
            :param request:
            :param response
            :return:
            """
            status_buffer = "Total Accesses: 95\n" + \
                            "Total kBytes: 65\n" + \
                            "CPULoad: .00304122\n" + \
                            "Uptime: 65763\n" + \
                            "ReqPerSec: .00144458\n" + \
                            "BytesPerSec: 1.01212\n" + \
                            "BytesPerReq: 700.632\n" + \
                            "BusyWorkers: 1\n" + \
                            "IdleWorkers: 49\n" + \
                            "ConnsTotal: 0\n" + \
                            "ConnsAsyncWriting: 0\n" + \
                            "ConnsAsyncKeepAlive: 0\n" + \
                            "ConnsAsyncClosing: 0\n" + \
                            "Scoreboard: ___________________________________W______________.................\n"

            if request['PATH_INFO'].endswith('/server-status'):
                response("200 OK", [('Content-Type', 'text/html')])
                return status_buffer

        # start Web server
        http_server = pywsgi.WSGIServer(('127.0.0.1', 0), http_process)
        http_server.start()
        server_port = http_server.server_port

        # start Unit test
        self._validate_internal(ApacheStat(
            url='http://127.0.0.1:' + str(server_port) + '/server-status?auto',
        ))

        # stop server
        http_server.stop(timeout=2)

    @unittest.skipIf(NginxStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_nginx(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        from gevent import pywsgi

        def http_process(request, response):
            """
            Internal http method
            :param request:
            :param response
            :return:
            """
            status_buffer = "Active connections: 1\n" + \
                            "server accepts handled requests\n" + \
                            " 1 1 1\n" + \
                            "Reading: 0 Writing: 1 Waiting: 0\n"

            if request['PATH_INFO'].endswith('/nginx_status'):
                response("200 OK", [('Content-Type', 'text/html')])
                return status_buffer

        # start Web server
        http_server = pywsgi.WSGIServer(('127.0.0.1', 0), http_process)
        http_server.start()
        server_port = http_server.server_port

        # start Unit test
        self._validate_internal(NginxStat(url='http://127.0.0.1:' + str(server_port) + '/nginx_status'))

        # stop server
        http_server.stop(timeout=2)

    @unittest.skipIf(PhpFpmStat().is_supported_on_platform() is False, "Not support on current platform, probe=%s" % ApacheStat())
    def test_probe_full_phpfpm(self):
        """
        Test
        :return:
        """
        logger.info("GO")

        from gevent import pywsgi

        def http_process(request, response):
            """
            Internal http method
            :param request:
            :param response
            :return:
            """
            status_buffer = '{' \
                            '"pool":"www",' \
                            '"process manager":"dynamic",' \
                            '"start time":1415829290,' \
                            '"start since":2615,' \
                            '"accepted conn":271839,' \
                            '"listen queue":0,' \
                            '"max listen queue":0,' \
                            '"listen queue len":0,' \
                            '"idle processes":2,' \
                            '"active processes":1,' \
                            '"total processes":3,' \
                            '"max active processes":5,' \
                            '"max children reached":6,' \
                            '"slow requests":0}'

            # request['PATH_INFO'] => 'http://127.0.0.1:48168/status'
            if request['PATH_INFO'].endswith('/status'):
                logger.info("/status CALLED")
                response("200 OK", [('Content-Type', 'application/json')])
                return status_buffer
            else:
                self.fail("No /status CALLED")

        # start Web server
        http_server = pywsgi.WSGIServer(('127.0.0.1', 0), http_process)
        http_server.start()
        server_port = http_server.server_port

        # start Unit test
        self._validate_internal(PhpFpmStat(
            d_pool_from_url={'www': ['http://127.0.0.1:' + str(server_port) + '/status?json']}
        ))

        # stop server
        http_server.stop(timeout=2)
