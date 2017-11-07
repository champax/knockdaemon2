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
import os
import unittest
import urllib

import redis
from nose.plugins.attrib import attr
from pythonsol.SolBase import SolBase
from pythonsol.meter.MeterManager import MeterManager

from knockdaemon.Api.Http.HttpClient import HttpClient
from knockdaemon.Api.Http.HttpRequest import HttpRequest
from knockdaemon.Api.Http.HttpResponse import HttpResponse
from knockdaemon.HttpMock.HttpMock import HttpMock

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
        MeterManager._hash_meter = dict()

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

    def test_get_basic_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT)

    def test_get_basic_urllib3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3)

    @unittest.skip("geventhttpclient broken in https : ImportError: cannot import name SSLConnectionPool")
    def test_get_basic_https_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT, https=True)

    def test_get_basic_https_urllib3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3, https=True)

    def test_get_proxy_squid_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT, proxy=True)

    def test_get_proxy_squid_urllib3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3, proxy=True)

    def test_get_proxy_squid_https_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT, proxy=True, https=True)

    def test_get_proxy_squid_https_squid3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3, proxy=True, https=True)

    def _http_basic_internal(self, force_implementation, proxy=False, https=False):
        """
        Test
        """

        logger.info("Starting, impl=%s", force_implementation)

        hc = HttpClient()

        for _ in range(0, 8):

            # Setup request
            hreq = HttpRequest()
            hreq.force_http_implementation = force_implementation

            if https:
                hreq.uri = "https://s.knock.center/static/k/k.notif.sample.png"
            else:
                # This will redirect https
                hreq.uri = "http://s.knock.center/static/k/k.notif.sample.png"

            # Http proxy
            if proxy:
                hreq.http_proxy_host = "127.0.0.1"
                hreq.http_proxy_port = 1180

            hresp = hc.go_http(hreq)

            self.assertIsNotNone(hresp)
            self.assertIsInstance(hresp, HttpResponse)

            self.assertIsNotNone(hresp.http_request)
            self.assertEqual(id(hreq), id(hresp.http_request))

            self.assertIsNotNone(hresp.elapsed_ms)

            self.assertIsNone(hresp.exception)

            if proxy and https:
                # Force to urllib3
                self.assertEqual(hresp.http_implementation, HttpClient.HTTP_IMPL_URLLIB3)
            else:
                self.assertEqual(hresp.http_implementation, force_implementation)

            self.assertIsNotNone(hresp.content_length)
            self.assertIsNotNone(hresp.buffer)
            self.assertEqual(hresp.content_length, len(hresp.buffer))

            self.assertGreater(len(hresp.headers), 0)

            self.assertIn(hresp.status_code, [200, 302, 301])

            self.assertEqual(hresp.headers["User-Agent"], "unittest")

            SolBase.sleep(250)

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

    def test_httpmock_proxy_squid_gevent(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_GEVENT, proxy=True)

    def test_httpmock_proxy_squid_urllib3(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_URLLIB3, proxy=True)

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
