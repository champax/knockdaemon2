# -*- coding: utf-8 -*-
"""
===============================================================================

Copyright (C) 2013/2021 Laurent Labatut / Laurent Champagnac



 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2
 of the License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 ===============================================================================
"""
import logging
import unittest

from pysolbase.SolBase import SolBase

from knockdaemon2.Probes.Haproxy.Haproxy import Haproxy

logger = logging.getLogger(__name__)

SolBase.voodoo_init()
SolBase.logging_init(log_level="DEBUG", force_reset=True, log_to_file=None, log_to_syslog=False, log_to_console=True)


class TestHaproxy(unittest.TestCase):
    """

    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        self.buffer = open("/home/llabatut/tmp/haproxy_unix.csv").read()

    @unittest.skipIf(SolBase.get_machine_name().find("lla") < 0, "lla pc")
    def test_parse_csv(self):
        """

        :return:
        """
        logger.debug("len buffer=%s", len(self.buffer))
        result = Haproxy.csv_parse(self.buffer)

        logger.info("result len =%s", result.line_num)
        for line in result:
            logger.debug("pxname={# pxname} svname={svname} status={status}".format(**line))
