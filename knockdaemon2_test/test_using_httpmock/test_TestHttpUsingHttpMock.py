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
import ujson
import unittest
import urllib

import os
from geventhttpclient import HTTPClient, URL
from nose.plugins.attrib import attr
from pythonsol.meter.MeterManager import MeterManager

from knockdaemon2.HttpMock.HttpMock import HttpMock

from pythonsol.SolBase import SolBase
SolBase.voodoo_init()
logger = logging.getLogger(__name__)


@attr('prov')
class TestHttp(unittest.TestCase):
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

    def tearDown(self):
        """
        Setup (called after each test)
        """
        if self.h:
            logger.warn("h set, stopping, not normal")
            self.h.stop()
            self.h = None

        if self.debug_stat:
            pass

    def test_start_stop(self):
        """
        Test
        """

        self.h = HttpMock()

        self.assertIsNotNone(self.h)
        self.assertFalse(self.h._is_running)
        self.assertIsNone(self.h._wsgi_server)
        self.assertIsNone(self.h._server_greenlet)

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

        self.h.stop()
        self.assertFalse(self.h._is_running)
        self.assertIsNone(self.h._wsgi_server)
        self.assertIsNone(self.h._server_greenlet)

        self.h = None

    def test_http_request(self):
        """
        Test
        """

        self.h = HttpMock()

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

        # Param
        v = urllib.urlencode({"p1": "v1 2.3/4"})

        # Http get
        url = URL("http://localhost:7900/unittest?" + v)
        http = HTTPClient.from_url(url, concurrency=10)
        response = http.get(url.request_uri)
        logger.info("Got=%s", response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.read(),
                         "OK\nfrom_qs={'p1': 'v1 2.3/4'} -EOL\nfrom_post={} -EOL\n")

        # Http post
        url = URL('http://localhost:7900/unittest')
        http = HTTPClient.from_url(url, concurrency=10)
        response = http.post(url.request_uri, v)
        logger.info("Got=%s", response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.read(),
                         "OK\nfrom_qs={} -EOL\nfrom_post={'p1': 'v1 2.3/4'} -EOL\n")

        # Http get toward invalid
        url = URL("http://localhost:7900/invalid")
        http = HTTPClient.from_url(url, concurrency=10)
        response = http.get(url.request_uri)
        logger.info("Got=%s", response)
        self.assertEqual(response.status_code, 400)

        # Over
        self.h.stop()
        self.assertFalse(self.h._is_running)
        self.assertIsNone(self.h._wsgi_server)
        self.assertIsNone(self.h._server_greenlet)

        self.h = None

    def test_json_basic(self):
        """
        Test
        """

        self.h = HttpMock()

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

        # Data
        d = dict()
        d["h"] = {"a": 1}
        d["v"] = {"b": 2}

        # Http post
        url = URL('http://localhost:7900/junittest')
        http = HTTPClient.from_url(url, concurrency=10)
        response = http.post(url.request_uri, ujson.dumps(d))
        logger.info("Got=%s", response)
        self.assertEqual(response.status_code, 200)

        # Over
        self.h.stop()
        self.assertFalse(self.h._is_running)
        self.assertIsNone(self.h._wsgi_server)
        self.assertIsNone(self.h._server_greenlet)

        self.h = None

    def test_json_log(self):
        """
        Test
        """

        self.h = HttpMock()

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

        # ----------------------
        # Data
        # ----------------------

        # PUSH
        d = dict()
        d["main_type"] = "MT1"
        d["logs"] = list()
        d["logs"].append({"type": "type1", "data": "data1"})
        d["logs"].append({"type": "type2", "data": "data2"})
        d["logs"].append({"type": "type3", "data": {"k1": "v1", "k2": "v2"}})

        # Http post
        url = URL('http://localhost:7900/logv1')
        http = HTTPClient.from_url(url, concurrency=10)
        response = http.post(url.request_uri, ujson.dumps(d))
        logger.info("Got=%s", response)
        buf = response.read()
        buf = buf.decode("zlib")
        d = ujson.loads(buf)
        logger.info("Got=%s", d)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(d["st"], 200)

        # ----------------------
        # Data (with stuff)
        # ----------------------

        d = dict()
        d["main_type"] = "MT1"
        d["namespace"] = "duchmoll"
        d["host"] = "duchmollH"
        d["logs"] = list()
        d["logs"].append({"type": "type1", "data": "data1"})
        d["logs"].append({"type": "type2", "data": "data2"})
        d["logs"].append({"type": "type3", "data": {"k1": "v1", "k2": "v2"}})

        # Http post
        url = URL('http://localhost:7900/logv1')
        http = HTTPClient.from_url(url, concurrency=10)
        response = http.post(url.request_uri, ujson.dumps(d))
        logger.info("Got=%s", response)
        buf = response.read()
        buf = buf.decode("zlib")
        d = ujson.loads(buf)
        logger.info("Got=%s", d)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(d["st"], 200)

        # ----------------------
        # Data (without MT) => FAILURE
        # ----------------------
        d = dict()
        d["namespace"] = "duchmoll"
        d["host"] = "duchmollH"
        d["logs"] = list()
        d["logs"].append({"type": "type1", "data": "data1"})
        d["logs"].append({"type": "type2", "data": "data2"})
        d["logs"].append({"type": "type3", "data": {"k1": "v1", "k2": "v2"}})

        # Http post
        url = URL('http://localhost:7900/logv1')
        http = HTTPClient.from_url(url, concurrency=10)
        response = http.post(url.request_uri, ujson.dumps(d))
        logger.info("Got=%s", response)
        buf = response.read()
        buf = buf.decode("zlib")
        d = ujson.loads(buf)
        logger.info("Got=%s", d)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(d["st"], 500)

        # Over
        self.h.stop()
        self.assertFalse(self.h._is_running)
        self.assertIsNone(self.h._wsgi_server)
        self.assertIsNone(self.h._server_greenlet)

        self.h = None
