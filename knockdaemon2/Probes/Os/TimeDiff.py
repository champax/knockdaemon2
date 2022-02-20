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

import ntplib
from gevent import monkey
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe

monkey.patch_all()

logger = logging.getLogger(__name__)


def get_ntp_offset(server_host):
    """
    Get ntp offset
    :param server_host: str
    :type server_host: str
    :return: float
    :rtype float
    """
    ntp = ntplib.NTPClient()
    response = ntp.request(server_host, version=2, timeout=3)
    value = round(response.offset, ndigits=6)
    return value


class TimeDiff(KnockProbe):
    """
    Doc
    """

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.server_host = None

        self.category = "/os/misc"

    def init_from_config(self, k, d_yaml_config, d):
        """
        Initialize from configuration
        :param k: str
        :type k: str
        :param d_yaml_config: full conf
        :type d_yaml_config: d
        :param d: local conf
        :type d: dict
        """

        # Base
        KnockProbe.init_from_config(self, k, d_yaml_config, d)

        # Go
        self.server_host = d["time_target_server"]

    def _execute_linux(self):
        """
        Execute
        """

        try:
            self.notify_value_n("k.os.timediff", None, abs(get_ntp_offset(self.server_host)))
        except ntplib.NTPException as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
        except Exception as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
