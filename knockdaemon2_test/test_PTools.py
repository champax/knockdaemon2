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

import distro
from pysolbase.SolBase import SolBase

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
        self.assertEqual("windows", PTools._get_distribution_type("Windows", distro.id(), distro.codename()))
        self.assertEqual("windows", PTools._get_distribution_type("Windows xxx", distro.id(), distro.codename()))

        self.assertEqual("debian", PTools._get_distribution_type(None, distro.id(), distro.codename()))
        self.assertEqual("debian", PTools._get_distribution_type("debian", distro.id(), distro.codename()))
        self.assertEqual("debian", PTools._get_distribution_type("Debian", distro.id(), distro.codename()))
        self.assertEqual("debian", PTools._get_distribution_type("invalid", distro.id(), distro.codename()))
        self.assertEqual("debian", PTools._get_distribution_type("Ubuntu", distro.id(), distro.codename()))

        self.assertEqual("redhat", PTools._get_distribution_type("CentOs", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("CentOs xxx", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("redhat", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("redhat xxx", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("Redhat xxx", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("red hat", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("red hat xxx", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("Red hat xxx", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("rehl", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("rehl xxx", distro.id(), distro.codename()))
        self.assertEqual("redhat", PTools._get_distribution_type("REhl xxx", distro.id(), distro.codename()))

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
