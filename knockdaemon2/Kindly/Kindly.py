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


class Kindly(object):
    """
    Fix for world wide kindly people
    """

    @classmethod
    def clean_string(cls, s):
        """
        fix
        :param s: str,unicode
        :type s: str,unicode
        :rtype str,unicode
        """

        return s.replace("\"", "")

    @classmethod
    def kindly_anyconfig_fix_ta_shitasse(cls, d):
        """
        kindly_anyconfig_fix_ta_shitasse.

        :param d: dict
        :type d: dict
        """

        for k, v in d.iteritems():
            if isinstance(v, dict):
                Kindly.kindly_anyconfig_fix_ta_shitasse(v)
            elif isinstance(v, (str, unicode)):
                f = Kindly.clean_string(v)
                d[k] = f

        return d
