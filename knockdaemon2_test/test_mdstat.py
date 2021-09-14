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
import glob
import logging
import os
import ujson
import unittest
from os.path import dirname, abspath

from pysolbase.SolBase import SolBase

from knockdaemon2.Probes.Os.Mdstat import Mdstat

logger = logging.getLogger(__name__)

SolBase.voodoo_init()
SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file=None, log_to_syslog=False, log_to_console=True)


class TestMdstat(unittest.TestCase):
    """

    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        json_path = os.path.join(current_dir, 'ForTest', 'mockData', 'mdstat')
        self.mdstat_results = {}

        json_file_patern = json_path + "/*.json"
        logger.info("Loading %s", json_file_patern)

        for filename in glob.glob(json_file_patern):
            logging.info("Loading %s", filename)
            data = open(filename).read()
            json_data = ujson.loads(data)
            self.mdstat_results.update({os.path.basename(filename).split('.')[0]: json_data})

    def test_rebuild(self):
        """

        :return:
        """
        result = Mdstat.parse(self.mdstat_results['rebuild'])
        result = list(result)
        logger.info("result=%s", result)
        self.assertEquals(result, [(u'md0', 2), (u'md127', 2)])

    def test_check(self):
        """

        :return:
        """
        result = Mdstat.parse(self.mdstat_results['check'])
        result = list(result)
        logger.info("result=%s", result)
        self.assertEquals(result, [(u'md0', 1), (u'md127', 1)])

    def test_failed(self):
        """

        :return:
        """
        result = Mdstat.parse(self.mdstat_results['failed'])
        result = list(result)
        logger.info("result=%s", result)
        self.assertEquals(result, [(u'md0', 3), (u'md127', 3)])

    def test_missing(self):
        """

        :return:
        """
        result = Mdstat.parse(self.mdstat_results['missing'])
        result = list(result)
        logger.info("result=%s", result)
        self.assertEquals(result, [(u'md0', 3), (u'md127', 3)])

    def test_ok(self):
        """

        :return:
        """
        result = Mdstat.parse(self.mdstat_results['ok'])
        result = list(result)
        logger.info("result=%s", result)
        self.assertEquals(result, [(u'md0', 0)])
