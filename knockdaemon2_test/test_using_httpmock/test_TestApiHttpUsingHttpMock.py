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
import urllib

import redis
# noinspection PyUnresolvedReferences,PyPackageRequirements
from nose.plugins.attrib import attr
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest
from pysolmeters.Meters import Meters

from knockdaemon2.HttpMock.HttpMock import HttpMock

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


@attr('prov')
class TestApiHttpUsingHttpMock(unittest.TestCase):
    """
    Test description
    """

    def setUp(self):
        """
        Setup (called before each test)
        """

        os.environ.setdefault("KNOCK_UNITTEST", "yes")

        self.h = None

        # Reset meter
        Meters.reset()

        # Debug stat on exit ?
        self.debug_stat = False

        # Temp redis : clear ALL
        r = redis.Redis()
        r.flushall()
        del r

    def tearDown(self):
        """
        Setup (called after each test)
        """

        if self.h:
            logger.warn("h set, stopping, not normal")
            self.h.stop()
            self.h = None

    def test_httpmock_noproxy_gevent(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_GEVENT, proxy=False)

    def test_httpmock_noproxy_urllib3(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_URLLIB3, proxy=False)

    def _http_basic_internal_to_httpmock(self, force_implementation, proxy=False):
        """
        Test
        """

        logger.info("impl=%s, proxy=%s", force_implementation, proxy)

        self.h = HttpMock()

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

        # Param
        v = urllib.urlencode({"p1": "v1 2.3/4"})

        # Client
        hc = HttpClient()

        # SolBase.logging_init(log_level="DEBUG", force_reset=True)

        # Http get
        hreq = HttpRequest()
        hreq.force_http_implementation = force_implementation
        if proxy:
            hreq.http_proxy_host = "127.0.0.1"
            hreq.http_proxy_port = 1180
        hreq.uri = "http://127.0.0.1:7900/unittest?" + v
        hresp = hc.go_http(hreq)
        logger.info("Got=%s", hresp)
        self.assertEqual(hresp.status_code, 200)
        self.assertEqual(hresp.buffer,
                         "OK\nfrom_qs={'p1': 'v1 2.3/4'} -EOL\nfrom_post={} -EOL\n")

        # Http post
        hreq = HttpRequest()
        hreq.force_http_implementation = force_implementation
        if proxy:
            hreq.http_proxy_host = "127.0.0.1"
            hreq.http_proxy_port = 1180
        hreq.uri = "http://127.0.0.1:7900/unittest"
        hreq.post_data = v
        hresp = hc.go_http(hreq)
        logger.info("Got=%s", hresp)
        self.assertEqual(hresp.status_code, 200)
        self.assertEqual(hresp.buffer,
                         "OK\nfrom_qs={} -EOL\nfrom_post={'p1': 'v1 2.3/4'} -EOL\n")

        # Http get toward invalid
        hreq = HttpRequest()
        hreq.force_http_implementation = force_implementation
        if proxy:
            hreq.http_proxy_host = "127.0.0.1"
            hreq.http_proxy_port = 1180
        hreq.uri = "http://127.0.0.1:7900/invalid"
        hresp = hc.go_http(hreq)
        logger.info("Got=%s", hresp)
        self.assertEqual(hresp.status_code, 400)

        # Over
        self.h.stop()
        self.assertFalse(self.h._is_running)
        self.assertIsNone(self.h._wsgi_server)
        self.assertIsNone(self.h._server_greenlet)
