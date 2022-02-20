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

from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Core.systemd import SystemdManager

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class TestSystemd(unittest.TestCase):
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

    def test_get_pid(self):
        """
        Test
        """

        manager = SystemdManager()
        is_active = manager.is_active('nginx.service')
        self.assertTrue(is_active)
        pid = manager.get_pid('nginx.service')
        logger.info("Nginx pid=%s", pid)
        self.assertGreater(pid, 0)
