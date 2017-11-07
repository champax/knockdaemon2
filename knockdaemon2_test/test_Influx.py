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
import unittest

import os
import datetime
import random
import time

from gevent import Timeout
from gevent.pool import Pool
from influxdb import InfluxDBClient
from influxdb.resultset import ResultSet
from influxdb.tests.server_tests.base import SingleTestCaseWithServerMixin

from pythonsol.SolBase import SolBase

from knockdaemon2.Transport.InfluxAsyncTransport import InfluxAsyncTransport

SolBase.voodoo_init()
SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file=None,
                     log_to_syslog=False, log_to_console=True)
logger = logging.getLogger(__name__)

ON_DEV = False
if os.environ.get('PYCHARM_HOSTED', 'TAMER') == '1':
    ON_DEV = True

THIS_DIR = os.path.abspath(os.path.dirname(__file__))


@unittest.skip("zzz")
class TestInflux(SingleTestCaseWithServerMixin, unittest.TestCase):
    """
    Test description
    """
    influxdb_template_conf = os.path.join(THIS_DIR, 'ForTest', 'influxd',
                                          'influxdb.conf.template')

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")
        super(self.__class__, self).setUp()

    @unittest.skipIf(not ON_DEV, "PYCHARM")
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

        json_body = [
            {
                "measurement": "cpu_load_short",
                "tags": {"host": "server01", "region": "us-west"},
                "time": "2009-11-10T23:00:00Z",
                "fields": {"value": 0.64}
            }
        ]
        database = 'zzz'
        try:
            with Timeout(5):
                self.assertIsInstance(self.cli, InfluxDBClient)
                self.cli.create_database(database)

                self.assertEqual(self.cli.get_list_database(),
                                 [{u'name': u'zzz'}])
                self.assertEqual(None, self.cli.switch_database(database))
                # noinspection PyUnresolvedReferences
                self.assertTrue(self.cli.http_handler._database == database)
                self.cli.write_points(json_body)

                result = self.cli.query('SELECT value FROM cpu_load_short;')
                self.assertIsInstance(result, ResultSet)
                logger.info("result=%s", result)
        except Timeout as e:
            # noinspection PyTypeChecker
            logger.warning(SolBase.extostr(e))
            self.assertTrue(False)

    def test_to_influx_format_single_disco(self):
        """
        Test
        """
        account_hash = {'acc_key': 'tamereenshort',
                        'acc_namespace': 'unittest'}
        node_hash = {'host': 'klchgui01'}
        notify_hash = {'test.dummy|TYPE|one': ('test.dummy', 'TYPE', 'one'),
                       'test.dummy|TYPE|all': ('test.dummy', 'TYPE', 'all'),
                       'test.dummy|TYPE|two': ('test.dummy', 'TYPE', 'two')}
        notify_values = [('test.dummy.count', 'all', 100, 1503045097.626604),
                         ('test.dummy.count', 'one', 90, 1503045097.626629),
                         (
                             'test.dummy.count[two]', None, 10, 1503045097.626639),
                         ('test.dummy.error', 'all', 5, 1503045097.62668),
                         ('test.dummy.error', 'one', 3, 1503045097.626704),
                         ('test.dummy.error', 'two', 2, 1503045097.626728)]

        ar_i = InfluxAsyncTransport.to_influx_format(account_hash, node_hash,
                                                     notify_hash,
                                                     notify_values)
        logger.info("ar_i=%s", ar_i)

        # TODO : Check multiple diso : k.dns.resolv

    @unittest.skipIf(not ON_DEV, "PYCHARM")
    def test_little_bench(self):
        """
        Test bench 10.000 writes
        """
        database = 'zzz'
        iter_count = 200
        pool = Pool(10)

        def iter_body(count):
            """

            """
            epoch = datetime.datetime.now()
            generated = list()

            for _ in range(count):
                epoch = epoch - datetime.timedelta(0, 60)
                json_body = [
                    {
                        "measurement": "cpu_load_short",
                        "tags": {"host": "server01", "region": "us-west"},
                        "time": epoch.isoformat(),
                        "fields": {"value": random.uniform(0, 1)}
                    }
                ]
                generated.append(json_body)
            while True:
                yield generated.pop()

        iterator = iter_body(iter_count)
        try:
            with Timeout(60):

                self.assertIsInstance(self.cli, InfluxDBClient)

                self.cli.create_database(database)
                self.cli.switch_database(database)
                result = self.cli.query('SELECT count(*) FROM cpu_load_short;')
                logger.info(result)
                if len(result.items()) == 0:
                    count_before = 0
                else:
                    count_before = list(result)[0][0]['count_value']
                start_time = time.time()
                for i in range(iter_count):
                    pool.spawn(self.cli.write_points, iterator.next())
                pool.join()
                end_time = time.time()
                logger.info('BENCH RESULT INSERT BY SEC: %s',
                            iter_count / (end_time - start_time))

                result = self.cli.query('SELECT value FROM cpu_load_short;')
                self.assertIsInstance(result, ResultSet)

                result = self.cli.query('SELECT count(*) FROM cpu_load_short;')
                count_value = list(result)[0][0]['count_value']
                logger.info('count_value=%s', count_value)
                self.assertEqual(count_value,
                                 count_before + iter_count)
        except Exception as e:
            logger.warning(SolBase.extostr(e))
            self.assertTrue(False)
