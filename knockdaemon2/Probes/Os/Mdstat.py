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

import mdstat

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    pass

logger = logging.getLogger(__name__)


# noinspection PyMethodMayBeStatic
class Mdstat(KnockProbe):
    """
    Doc
    """

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.category = "/os/disk"

    def _execute_linux(self):
        """
        Exec
        """
        if not os.path.isfile('/proc/mdstat'):
            return
        for md, result in Mdstat.parse():
            self.notify_value_n("k.os.disk.mdstat", {'md': md}, result)

    @classmethod
    def parse(cls, mdjson=False):
        """
        result :
            0: ok
            1: info checking
            2: warning rebuild
            3: critical degraded or broken

        :param mdjson: fake data for unittest
        :type mdjson: dict
        :return: md_name, result
        :rtype: list of tuple
        """
        if not mdjson:
            mdjson = mdstat.parse()
        for device_name, device in mdjson['devices'].items():

            # search for faulty disk
            faulty = False
            for disk in device['disks'].values():
                faulty = faulty or disk.get('faulty')

            if faulty:
                yield device_name, 3

            # Rebuild
            elif device['resync'] is not None and device['resync'].get('operation', '') == 'recovery':
                yield device_name, 2

            elif False in device['status']['synced']:
                yield device_name, 3

            elif device['resync'] is not None and device['resync'].get('operation', '') == 'check':
                yield device_name, 1

            else:
                yield device_name, 0
            pass
