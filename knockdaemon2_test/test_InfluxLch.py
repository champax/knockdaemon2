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
import unittest

from influxdb import InfluxDBClient
from influxdb.line_protocol import make_lines
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient

from knockdaemon2.Core.Tools import Tools

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


# noinspection SqlNoDataSourceInspection
class TestInfluxLch(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

    def tearDown(self):
        """
        Setup (called after each test)
        """

        pass

    @unittest.skipIf(SolBase.get_machine_name().find("lchgui") < 0, "lchgui pc")
    def test_base_json(self):
        """
        Test
        # Requires:
        - influxdb installed and configured with AUTH on

        # Option
        - may have to redirect logs from syslog to file
        cat /etc/rsyslog.d/influxdb.conf
        if $programname == "influxd" then {
            action(type="omfile" file="/var/log/influxdb/influxdb.log" fileOwner="root" fileGroup="root")
            stop
        }

        # Requires:
        $ influx -precision rfc3339 -host 127.0.0.1 -port 8286
        Connected to http://127.0.0.1:8286 version 1.3.2
        InfluxDB shell version: 1.3.2
        > CREATE USER admin WITH PASSWORD [REDACTED] WITH ALL PRIVILEGES
        """

        json_body = [
            {
                "measurement": "cpu_load_short",
                "tags": {"host": "server01", "region": "us-west"},
                "time": "2009-11-10T23:00:00Z",
                "fields": {"value": 0.64}
            }
        ]

        client = InfluxDBClient(host='127.0.0.1', port=8286, username='admin', password='duchmol', database='zzz', retries=0, )

        client.drop_database("zzz")
        client.create_database("zzz")
        client.write_points(json_body)

        result = client.query('select value from cpu_load_short;')

        logger.info("result=%s", result)

    @unittest.skipIf(SolBase.get_machine_name().find("lchgui") < 0, "lchgui pc")
    def test_base_line(self):
        """
        Test
        # Requires:
        - influxdb installed and configured with AUTH on

        # Option
        - may have to redirect logs from syslog to file
        cat /etc/rsyslog.d/influxdb.conf
        if $programname == "influxd" then {
            action(type="omfile" file="/var/log/influxdb/influxdb.log" fileOwner="root" fileGroup="root")
            stop
        }

        # Requires:
        $ influx -precision rfc3339 -host 127.0.0.1 -port 8286
        Connected to http://127.0.0.1:8286 version 1.3.2
        InfluxDB shell version: 1.3.2
        > CREATE USER admin WITH PASSWORD [REDACTED] WITH ALL PRIVILEGES
        """

        d_body = {"points": [
            {
                "measurement": "cpu_load_short_line",
                "tags": {"host": "server01", "region": "us-west"},
                "time": "2010-11-10T23:00:00Z",
                "fields": {"value": 0.64}
            },
            {
                "measurement": "cpu_load_short_line",
                "tags": {"host": "server01", "region": "us-west"},
                "time": "2012-11-10T23:00:00Z",
                "fields": {"value": 0.65}
            }
        ]}

        client = InfluxDBClient(host='127.0.0.1', port=8286, username='admin', password='duchmol', database='zzz2', retries=0, )

        client.drop_database("zzz2")
        client.create_database("zzz2")
        line_buf = make_lines(d_body, precision=None).encode('utf8')
        logger.info("line_buf=%s", line_buf)
        client.write_points([line_buf], protocol="line")

        result = client.query('select value from cpu_load_short_line;')

        logger.info("result=%s", result)
        self.assertEqual(len(result), 1)

    def test_to_influx_format_single_disco(self):
        """
        Test
        """
        account_hash = {"acc_key": "tamereenshort", "acc_namespace": "unittest"}
        node_hash = {"host": "klchgui01"}
        notify_values = [
            ("test.dummy.count", {"TYPE": "all"}, 100, 1503045097.626604, {"category": "testc"}),
            ("test.dummy.count", {"TYPE": "one"}, 90, 1503045097.626629, {"category": "testc"}),
            ("test.dummy.count", {"TYPE": "two"}, 10, 1503045097.626639, {"category": "testc"}),
            ("test.dummy.error", {"TYPE": "all"}, 5, 1503045097.62668, {"category": "testc"}),
            ("test.dummy.error", {"TYPE": "one"}, 3, 1503045097.626704, {"category": "testc"}),
            ("test.dummy.error", {"TYPE": "two", "ZZ": "zzv"}, 2, 1503045097.626728, {"category": "testc"})
        ]

        ar_i = Tools.to_influx_format(account_hash, node_hash, notify_values)
        logger.info("ar_i=%s", ar_i)
        idx = 0
        for cur_probe, cur_dd, cur_v, cur_ts, cur_opt_tags in notify_values:
            d_influx = ar_i[idx]
            idx += 1

            self.assertEqual(d_influx["time"], SolBase.dt_ensure_utc_naive(SolBase.epoch_to_dt(cur_ts)).strftime('%Y-%m-%dT%H:%M:%SZ'))
            self.assertEqual(d_influx["measurement"], cur_probe)
            self.assertEqual(d_influx["fields"]["value"], cur_v)

            self.assertEqual(len(d_influx["tags"]), len(cur_dd) + len(cur_opt_tags) + 2)
            self.assertEqual(d_influx["tags"]["host"], "klchgui01")
            self.assertEqual(d_influx["tags"]["ns"], "unittest")
            for k, v in cur_dd.items():
                self.assertEqual(v, d_influx["tags"][k])
            for k, v in cur_opt_tags.items():
                self.assertEqual(v, d_influx["tags"][k])

                # TODO : Check multiple diso : k.dns.resolv

    def test_auth_encode(self):
        """
        Test
        """

        d = Tools.influx_get_auth_header("admin", "duchmol")
        self.assertEqual(d["Authorization"], "Basic YWRtaW46ZHVjaG1vbA==")

    @unittest.skipIf(SolBase.get_machine_name().find("lchgui") < 0, "lchgui pc")
    def test_base_line_custom(self):
        """
        Test
        # Requires:
        - influxdb installed and configured with AUTH on

        # Option
        - may have to redirect logs from syslog to file
        cat /etc/rsyslog.d/influxdb.conf
        if $programname == "influxd" then {
            action(type="omfile" file="/var/log/influxdb/influxdb.log" fileOwner="root" fileGroup="root")
            stop
        }

        # Requires:
        $ influx -precision rfc3339 -host 127.0.0.1 -port 8286
        Connected to http://127.0.0.1:8286 version 1.3.2
        InfluxDB shell version: 1.3.2
        > CREATE USER admin WITH PASSWORD [REDACTED] WITH ALL PRIVILEGES
        """

        db_name = "zzz2custom"
        d_body = {"points": [
            {
                "measurement": "cpu_load_short_line",
                "tags": {"host": "server01", "region": "us-west"},
                "time": "2010-11-10T23:00:00Z",
                "fields": {"value": 0.64}
            },
            {
                "measurement": "cpu_load_short_line",
                "tags": {"host": "server01", "region": "us-west"},
                "time": "2012-11-10T23:00:00Z",
                "fields": {"value": 0.65}
            }
        ]}

        # Go
        http_client = HttpClient()

        # Drop twice
        http_rep = Tools.influx_drop_database(http_client, host='127.0.0.1', port=8286, username='admin', password='duchmol', database=db_name, timeout_ms=10000, ssl=False, verify_ssl=False)
        self.assertEqual(http_rep.status_code, 200)
        http_rep = Tools.influx_drop_database(http_client, host='127.0.0.1', port=8286, username='admin', password='duchmol', database=db_name, timeout_ms=10000, ssl=False, verify_ssl=False)
        self.assertEqual(http_rep.status_code, 200)

        # Create twice
        http_rep = Tools.influx_create_database(http_client, host='127.0.0.1', port=8286, username='admin', password='duchmol', database=db_name, timeout_ms=10000, ssl=False, verify_ssl=False)
        self.assertEqual(http_rep.status_code, 200)
        http_rep = Tools.influx_create_database(http_client, host='127.0.0.1', port=8286, username='admin', password='duchmol', database=db_name, timeout_ms=10000, ssl=False, verify_ssl=False)
        self.assertEqual(http_rep.status_code, 200)

        # Build lines
        line_buf = make_lines(d_body, precision=None).encode('utf8')
        logger.info("line_buf=%s", repr(line_buf))

        # Insert
        http_rep = Tools.influx_write_data(http_client, host='127.0.0.1', port=8286, username='admin', password='duchmol', database=db_name, ar_data=[line_buf], timeout_ms=10000, ssl=False, verify_ssl=False)
        self.assertIn(http_rep.status_code, [200, 204])

        # Re-read
        client = InfluxDBClient(host='127.0.0.1', port=8286, username='admin', password='duchmol', database=db_name, retries=0, )
        result = client.query('select value from cpu_load_short_line;')

        logger.info("result=%s", result)
        self.assertEqual(len(result), 1)
