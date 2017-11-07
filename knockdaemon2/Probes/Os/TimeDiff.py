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
import ntplib
from datetime import datetime
import email.utils as eut
from pythonsol.SolBase import SolBase

from knockdaemon2.Api.Http.HttpClient import HttpClient
from knockdaemon2.Api.Http.HttpRequest import HttpRequest
from knockdaemon2.Core.KnockProbe import KnockProbe
from gevent import monkey
monkey.patch_all()

logger = logging.getLogger(__name__)


class TimeDiff(KnockProbe):
    """
    Doc
    """

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.serverhost = None
        self.server_http = None

        self.category = "/os/misc"

    def init_from_config(self, config_parser, section_name):
        """
        Initialize from configuration
        :param config_parser: dict
        :type config_parser: dict
        :param section_name: Ini file section for our probe
        :type section_name: str
        """

        # Base
        KnockProbe.init_from_config(self, config_parser, section_name)

        # Go
        self.serverhost = config_parser[section_name]["time_target_server"]
        self.server_http = config_parser[section_name]["time_http_target_server"]

    def _execute_linux(self):
        """
        Doc
        """

        try:
            ntp = ntplib.NTPClient()
            response = ntp.request(self.serverhost, version=2, timeout=3)
            value = round(response.offset, ndigits=3)
        except ntplib.NTPException as e:
            logger.debug(SolBase.extostr(e))
            value = self.get_time_from_http()
        except Exception as e:
            logger.warn("Exception=%s", SolBase.extostr(e))
            value = self.get_time_from_http()
        self.notify_value_n("k.os.timediff", None, abs(value))

    def _execute_windows(self):
        """
        Exec
        """
        return self._execute_linux()

    def get_time_from_http(self):
        """
        Get net time over http
        :return:
        """

        hc = HttpClient()

        for _ in range(0, 2):
            try:
                # Setup request
                hreq = HttpRequest()
                hreq.force_http_implementation = HttpClient.HTTP_IMPL_URLLIB3
                hreq.uri = self.server_http

                hresp = hc.go_http(hreq)

                remote_date = hresp.headers["Date"]
                remote_date = datetime(*eut.parsedate(remote_date)[:6])
                timediff = (remote_date - datetime.utcnow()).total_seconds()
                return timediff
            except Exception as e:
                logger.debug("Ex=%s", SolBase.extostr(e))
