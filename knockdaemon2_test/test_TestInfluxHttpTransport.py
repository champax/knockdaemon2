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

import logging
import os
import unittest
from time import time

from pysolbase.SolBase import SolBase
SolBase.voodoo_init()
from pysolmeters.Meters import Meters

from knockdaemon2.Transport.InfluxAsyncTransport import InfluxAsyncTransport


logger = logging.getLogger(__name__)


class TestInfluxHttpTransport(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        # Reset meter
        Meters.reset()

    def tearDown(self):
        """
        Setup (called after each test)
        """

        pass

    def test_influx_transport_max_items(self):
        """
        Test
        """

        iat = InfluxAsyncTransport()
        iat._max_items_in_queue = 5
        iat._max_bytes_in_queue = 1024

        # Push ONE (56 bytes)
        iat.process_notify(
            account_hash={"acc_namespace": "test"},
            node_hash={"host": "tamer"},
            notify_values=[
                ("C1", {"T": "1"}, 1.0, time(), {}),
            ],
        )

        self.assertEqual(iat._queue_to_send.qsize(), 1)
        e = iat._queue_to_send.peek(block=True)
        self.assertTrue(e.startswith("C1,T=1,host=tamer,ns=test value=1.0 "))
        self.assertEqual(iat._current_queue_bytes, 56)

        # Push 5 (must hit max items)
        for i in range(1, 6):
            iat.process_notify(
                account_hash={"acc_namespace": "test"},
                node_hash={"host": "tamer"},
                notify_values=[
                    ("C%s" % i, {"T": "1"}, 1.0, time(), {}),
                ],
            )
        self.assertEqual(iat._queue_to_send.qsize(), 5)
        self.assertEqual(iat._current_queue_bytes, 56 * 5)
        self.assertEqual(Meters.aig(iat.meters_prefix + "knock_stat_transport_queue_discard"), 1)
        self.assertEqual(Meters.aig(iat.meters_prefix + "knock_stat_transport_queue_discard_bytes"), 0)

    def test_influx_transport_max_bytes(self):
        """
        Test
        """

        iat = InfluxAsyncTransport()
        iat._max_items_in_queue = 100
        iat._max_bytes_in_queue = 105

        # Push ONE (56 bytes)
        iat.process_notify(
            account_hash={"acc_namespace": "test"},
            node_hash={"host": "tamer"},
            notify_values=[
                ("C1", {"T": "1"}, 1.0, time(), {}),
            ],
        )

        self.assertEqual(iat._queue_to_send.qsize(), 1)
        e = iat._queue_to_send.peek(block=True)
        self.assertTrue(e.startswith("C1,T=1,host=tamer,ns=test value=1.0 "))
        self.assertEqual(iat._current_queue_bytes, 56)

        # Push 2 (must hit max bytes)
        for i in range(1, 3):
            logger.info("PUSH, i=%s", i)
            iat.process_notify(
                account_hash={"acc_namespace": "test"},
                node_hash={"host": "tamer"},
                notify_values=[
                    ("C%s" % i, {"T": "1"}, 1.0, time(), {}),
                ],
            )
        self.assertEqual(iat._queue_to_send.qsize(), 2)
        self.assertEqual(iat._current_queue_bytes, 56 * 2)
        self.assertEqual(Meters.aig(iat.meters_prefix + "knock_stat_transport_queue_discard"), 0)
        self.assertEqual(Meters.aig(iat.meters_prefix + "knock_stat_transport_queue_discard_bytes"), 1)

