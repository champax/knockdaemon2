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
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Transport.Dedup import Dedup
from knockdaemon2.Transport.InfluxAsyncTransport import InfluxAsyncTransport

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class TestTransportInflux(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")
        Meters.reset()

    def tearDown(self):
        """
        Setup (called after each test)
        """

        pass

    def test_dedup(self):
        """
        Test
        """

        dd = Dedup()

        # Build our stuff
        ar_notify_values = [
            ("probe_a", {"tag1": "tagv1", "tag2": "tagv2"}, 100, SolBase.dt_to_epoch(SolBase.datecurrent()), {"otagz": "vtagz", "otagx": "vtagx"}, {'v': 1}),
            ("probe_b", {"tag1": "tagv1", "tag2": "tagv2"}, 100, SolBase.dt_to_epoch(SolBase.datecurrent()), {"otagz": "vtagz", "otagx": "vtagx"}, {'v': 2}),
        ]

        # Dedup and check (BYPASS purge)
        ar_check = dd.dedup(notify_values=ar_notify_values, limit_ms=SolBase.mscurrent() - 60000)
        self.assertEqual(ar_notify_values, ar_check)
        self.assertEqual(len(dd.d_dedup), 2)
        for probe_name, d_tags, value, timestamp, d_values, _ in ar_notify_values:
            in_dedup_key = Dedup.get_dedup_key(probe_name, d_tags)
            in_window = Dedup.epoch_to_dt_without_sec(timestamp)
            self.assertIn(in_dedup_key, dd.d_dedup)
            self.assertIn(in_window, dd.d_dedup[in_dedup_key])

        # Dedup and check (FULL purge)
        ar_check = dd.dedup(notify_values=ar_notify_values, limit_ms=SolBase.mscurrent() + 60000)
        self.assertEqual(ar_notify_values, ar_check)
        self.assertEqual(len(dd.d_dedup), 2)
        for probe_name, d_tags, value, timestamp, d_values in ar_notify_values:
            in_dedup_key = Dedup.get_dedup_key(probe_name, d_tags)
            in_window = Dedup.epoch_to_dt_without_sec(timestamp)
            self.assertIn(in_dedup_key, dd.d_dedup)
            self.assertIn(in_window, dd.d_dedup[in_dedup_key])

        # Call purge
        dd._purge(SolBase.mscurrent() + 60000)
        self.assertEqual(len(dd.d_dedup), 0)

        # Dedup check (no purge, so dedup ON)
        ar_check = dd.dedup(notify_values=ar_notify_values, limit_ms=SolBase.mscurrent() - 60000)
        self.assertEqual(ar_notify_values, ar_check)
        ar_check = dd.dedup(notify_values=ar_notify_values, limit_ms=SolBase.mscurrent() - 60000)
        self.assertEqual(len(ar_check), 0)

        # Logs
        Meters.write_to_logger()

    @unittest.skipIf(SolBase.get_machine_name().find("lchgui") < 0, "lchgui pc")
    def test_base(self):
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

        client = InfluxDBClient(host='127.0.0.1', port=8286, username='admin', password='duchmol', database='zzz', retries=0, )
        client.drop_database("zzz")

        # Transport
        ti = InfluxAsyncTransport()
        ti._influx_host = "127.0.0.1"
        ti._influx_port = 8286
        ti._influx_login = "admin"
        ti._influx_password = "duchmol"
        ti._influx_database = "zzz"
        ti._influx_db_created = False

        # Running
        ti._is_running = True

        # Force a send right now
        ti._http_send_min_interval_ms = 0

        # Push one stuff
        ti.process_notify(
            account_hash={'acc_key': 'tamereenshort', 'acc_namespace': 'unittest'},
            node_hash={'host': 'ut_host'},
            notify_values=[
                ("dummy.count", {"TYPE": "type1", "opt_key": "va"}, 10, 1503045097.626604, {"value2": 1}),
                ("dummy.count", {"TYPE": "type1", "opt_key": "vb"}, 20, 1503045197.626629, {"value2": 1}),
            ]
        )

        # Fire
        ti._try_send_to_http()

        # Reload
        client = InfluxDBClient(host='127.0.0.1', port=8286, username='admin', password='duchmol', database='zzz', retries=0, )
        result = client.query("select * from \"dummy.count\";")
        logger.info("raw=%s", result.raw)
        for m, g in result.items():
            for r in g:
                logger.info("m=%s, r=%s", m, r)
