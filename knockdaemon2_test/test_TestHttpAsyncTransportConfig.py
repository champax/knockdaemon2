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

import anyconfig
import os
# noinspection PyUnresolvedReferences,PyPackageRequirements
from nose.plugins.attrib import attr
from os.path import dirname, abspath
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockConfigurationKeys import KnockConfigurationKeys
from knockdaemon2.Kindly.Kindly import Kindly
from knockdaemon2.Transport.HttpAsyncTransport import HttpAsyncTransport

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


@attr('prov')
class TestHttpAsyncTransportConfig(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.config_file_ok = \
            self.current_dir + "conf" + SolBase.get_pathseparator() \
            + "check" + SolBase.get_pathseparator() + "knockdaemon2.ini"

        self.config_file_nothing = \
            self.current_dir + "conf" + SolBase.get_pathseparator() \
            + "check" + SolBase.get_pathseparator() + "knockdaemon2_nothing.ini"

    def tearDown(self):
        """
        Setup (called after each test)
        """

    def test_config_ok(self):
        """
        Test
        """

        h = HttpAsyncTransport()

        # Go
        config_parser = anyconfig.load(self.config_file_ok)
        config_parser = Kindly.kindly_anyconfig_fix_ta_shitasse(config_parser)
        h.init_from_config(config_parser, KnockConfigurationKeys.INI_TRANSPORT_TAG,
                           auto_start=False)

        self.assertEqual(h.http_uri, "theuri")
        self.assertEqual(h._max_items_in_queue, 1)
        self.assertEqual(h._http_ko_interval_ms, 2)
        self.assertEqual(h._http_send_min_interval_ms, 3)
        self.assertEqual(h._http_send_max_bytes, 4)
        self.assertEqual(h._http_send_bypass_wait_ms, 5)
        self.assertEqual(h._lifecycle_interval_ms, 6)

    def test_config_nothing(self):
        """
        Test
        """

        h = HttpAsyncTransport()
        h2 = HttpAsyncTransport()

        # Go
        config_parser = anyconfig.load(self.config_file_nothing)
        config_parser = Kindly.kindly_anyconfig_fix_ta_shitasse(config_parser)
        h.init_from_config(config_parser, KnockConfigurationKeys.INI_TRANSPORT_TAG,
                           auto_start=False)

        self.assertEqual(h._max_items_in_queue, h2._max_items_in_queue)
        self.assertEqual(h._http_ko_interval_ms, h2._http_ko_interval_ms)
        self.assertEqual(h._http_send_min_interval_ms, h2._http_send_min_interval_ms)
        self.assertEqual(h._http_send_max_bytes, h2._http_send_max_bytes)
        self.assertEqual(h._http_send_bypass_wait_ms, h2._http_send_bypass_wait_ms)
        self.assertEqual(h._lifecycle_interval_ms, h2._lifecycle_interval_ms)
