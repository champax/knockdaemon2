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

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockManager import KnockManager

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class TestDynamicLoading(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")
        self.current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        self.ar_file_to_delete = list()

        ps = SolBase.get_pathseparator()
        if FileUtility.is_file_exist(self.current_dir + "conf" + ps + "dynamicload" + ps + "probed" + ps + "__init__.py"):
            os.remove(self.current_dir + "conf" + ps + "dynamicload" + ps + "probed" + ps + "__init__.py")

    def tearDown(self):
        """
        Setup (called after each test)
        """

        for s in self.ar_file_to_delete:
            os.remove(s)
            pass

    @unittest.skip("To re-enable later")
    def test_base(self):
        """
        Test
        """

        # https://stackoverflow.com/questions/301134/dynamic-module-import-in-python
        # https://stackoverflow.com/questions/2259427/load-python-code-at-runtime
        # https://stackoverflow.com/questions/3178285/list-classes-in-directory-python

        ps = SolBase.get_pathseparator()
        ar_probes, ar_files = KnockManager.try_dynamic_load_probe(self.current_dir + "conf" + ps + "dynamicload" + ps + "probed" + ps)

        # Store
        self.ar_file_to_delete.extend(ar_files)

        # Check
        self.assertEqual(len(ar_files), 1)
        self.assertEqual(len(ar_probes), 2)

        for p in ar_probes:
            # Check both
            if SolBase.get_classname(p).find("P1") >= 0:
                self.assertIn("c=P1", str(p))
                # noinspection PyUnresolvedReferences
                self.assertTrue(p.p1)
            elif SolBase.get_classname(p).find("P2") >= 0:
                self.assertIn("c=P2", str(p))
                # noinspection PyUnresolvedReferences
                self.assertTrue(p.p2)
            else:
                self.fail("Failed, need P1 or P2")
