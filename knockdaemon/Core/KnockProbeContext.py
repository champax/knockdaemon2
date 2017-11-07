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

logger = logging.getLogger(__name__)


class KnockProbeContext(object):
    """
    A probe context
    """

    def __init__(self):
        """
        Constructor
        """
        self.initial_ms_start = 0.0
        self.exec_count_so_far = 0.0

    def __str__(self):
        """
        To string override
        :return: A string
        :rtype string
        """

        return "kctx:*in=%.0f*ex=%.0f" % (self.initial_ms_start, self.exec_count_so_far)
