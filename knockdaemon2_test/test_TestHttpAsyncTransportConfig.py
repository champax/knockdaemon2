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
from os.path import dirname, abspath

# noinspection PyUnresolvedReferences,PyPackageRequirements
from nose.plugins.attrib import attr
from pysolbase.SolBase import SolBase

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
        self.config_file_ok = self.current_dir + "conf" + SolBase.get_pathseparator() + "check" + SolBase.get_pathseparator() + "knockdaemon2.yaml"

        self.config_file_nothing = self.current_dir + "conf" + SolBase.get_pathseparator() + "check" + SolBase.get_pathseparator() + "knockdaemon2_nothing.yaml"

    def tearDown(self):
        """
        Setup (called after each test)
        """

    def test_dummy(self):
        """
        Test
        """
        pass
