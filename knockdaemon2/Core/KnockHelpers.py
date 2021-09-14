"""
-*- coding: utf-8 -*-
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
import ctypes
import logging
import sys

import os

logger = logging.getLogger(__name__)


class KnockHelpers(object):
    """

    """

    def __init__(self):
        """

        """
        self.is_admin = self.admin()

    @staticmethod
    def admin():
        """
        Determine whether this script is running with administrative privilege.

        :return: True if running as an administrator, False otherwise.
        :rtype: bool

        """
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        return is_admin

    def sudoize(self, cmd):
        """
        Add sudo in start of cmd if needed
        :param cmd:
        :return:
        """
        if not self.is_admin:
            return 'sudo ' + cmd
        else:
            return cmd

    @classmethod
    def trick_instant_value_to_cumulative(cls, prev_value, cur_value, cur_elapsed_sec):
        """
        Trick
        :param prev_value: float, None
        :type prev_value: float, None
        :param cur_value: float
        :type cur_value: float
        :param cur_elapsed_sec: float
        :type cur_elapsed_sec: float
        :return: new value to store and to send
        :rtype float
        """

        # Example :
        # sec 0         50% cpu                         => server receive 50       = 50 (no previous value, we store it raw)
        # sec 60        50% cpu,    60s * 50% = 30      => server receive 50 + 30  = 80      => server delta = 30        => for 60 sec : 30 / 60 = 50%
        # sec 120       50% cpu,    60s * 50% = 30      => server receive 80 + 30  = 110     => server delta = 30        => for 60 sec : 30 / 60 = 50%
        # sec 180       100% cpu,   60s * 100% = 30     => server receive 110 + 60 = 170     => server delta = 60        => for 60 sec : 60 / 60 = 100%

        if prev_value is None:
            return cur_value
        elif cur_elapsed_sec <= 0.0:
            return cur_value
        else:
            delta_per_sec = cur_elapsed_sec * cur_value / 100.0

            # Handle maximum overload
            if prev_value + delta_per_sec >= sys.float_info.max:
                return delta_per_sec
            else:
                return prev_value + delta_per_sec
