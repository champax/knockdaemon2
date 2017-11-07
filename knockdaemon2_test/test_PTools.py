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
import platform
import unittest

import os

from pythonsol.SolBase import SolBase

from knockdaemon2.Platform.PTools import PTools

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class TestPTools(unittest.TestCase):
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

    def test_get_distribution_type(self):
        """
        Test
        """

        # Internal method check
        self.assertEqual("windows", PTools._get_distribution_type("Windows", platform.dist(), platform.linux_distribution()))
        self.assertEqual("windows", PTools._get_distribution_type("Windows xxx", platform.dist(), platform.linux_distribution()))

        self.assertEqual("debian", PTools._get_distribution_type(None, platform.dist(), platform.linux_distribution()))
        self.assertEqual("debian", PTools._get_distribution_type("debian", platform.dist(), platform.linux_distribution()))
        self.assertEqual("debian", PTools._get_distribution_type("Debian", platform.dist(), platform.linux_distribution()))
        self.assertEqual("debian", PTools._get_distribution_type("invalid", platform.dist(), platform.linux_distribution()))
        self.assertEqual("debian", PTools._get_distribution_type("Ubuntu", platform.dist(), platform.linux_distribution()))

        self.assertEqual("redhat", PTools._get_distribution_type("CentOs", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("CentOs xxx", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("redhat", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("redhat xxx", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("Redhat xxx", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("red hat", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("red hat xxx", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("Red hat xxx", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("rehl", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("rehl xxx", platform.dist(), platform.linux_distribution()))
        self.assertEqual("redhat", PTools._get_distribution_type("REhl xxx", platform.dist(), platform.linux_distribution()))

        # Current stuff
        self.assertIn(PTools.get_distribution_type(), ["debian", "redhat", "windows"])

    def test_is_os_64(self):
        """
        Test
        """

        # Just check we dont explode
        logger.info("is_os_64=%s", PTools.is_os_64())

    def test_is_cpu_arm(self):
        """
        Test
        """

        # Just check we dont explode
        logger.info("is_cpu_arm=%s", PTools.is_cpu_arm())
