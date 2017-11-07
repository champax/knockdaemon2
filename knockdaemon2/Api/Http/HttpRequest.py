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
from knockdaemon2.Api.Http.HttpClient import HttpClient


class HttpRequest(object):
    """
    Http client
    """

    def __init__(self):
        """
        Const
        """

        # Uri
        self.uri = None

        # Post data
        self.post_data = None

        # Request headers
        self.headers = dict()

        # General timeout
        self.general_timeout_ms = 30000

        # Connection timeout
        self.connection_timeout_ms = 10000

        # Network timeout
        self.network_timeout_ms = 10000

        # Keep alive on/off
        self.keep_alive = True

        # Http concurrency
        self.http_concurrency = 8192

        # Https insecure
        self.https_insecure = True

        # Ip v6
        self.disable_ipv6 = True

        # Proxy
        self.http_proxy_host = None
        self.http_proxy_port = None

        # Socks5
        self.socks5_proxy_host = None
        self.socks5_proxy_port = None

        # Force implementation
        self.force_http_implementation = HttpClient.HTTP_IMPL_AUTO

    def __str__(self):
        """
        To string override
        :return: A string
        :rtype string
        """

        return "hreq:uri={0}*pd={1}*ka={2}*cc={3}*httpsi={4}*prox={5}*socks={6}*force={7}*h={8}*to.c/n/g={9}/{10}/{11}".format(
            self.uri,
            len(self.post_data) if self.post_data else "None",
            self.keep_alive,
            self.http_concurrency,
            self.https_insecure,
            "{0}:{1}".format(self.http_proxy_host, self.http_proxy_port),
            "{0}:{1}".format(self.socks5_proxy_host, self.socks5_proxy_port),
            self.force_http_implementation,
            self.headers,
            self.connection_timeout_ms, self.network_timeout_ms, self.general_timeout_ms,
        )
