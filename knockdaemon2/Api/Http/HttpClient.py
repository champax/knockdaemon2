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

import gevent
import urllib3
from gevent.timeout import Timeout
from gevent.threading import Lock
from geventhttpclient.client import PROTO_HTTPS, HTTPClient
from geventhttpclient.url import URL
from pythonsol.SolBase import SolBase
from urllib3 import PoolManager, ProxyManager, Retry
from knockdaemon2.Api.Http.HttpResponse import HttpResponse

logger = logging.getLogger(__name__)

# Suppress warnings
urllib3.disable_warnings()


class HttpClient(object):
    """
    Http client
    """

    HTTP_IMPL_AUTO = None
    HTTP_IMPL_GEVENT = 1
    HTTP_IMPL_URLLIB3 = 3

    def __init__(self):
        """
        Const
        """

        # Gevent
        self._gevent_pool_max = 1024
        self._gevent_locker = Lock()
        self._gevent_pool = dict()

        # urllib3
        # Force underlying fifo queue to 1024 via maxsize
        self._u3_basic_pool = PoolManager(num_pools=1024, maxsize=1024)
        self._u3_proxy_pool_max = 1024
        self._u3_proxy_locker = Lock()
        self._u3_proxy_pool = dict()

    # ====================================
    # GEVENT HTTP POOL
    # ====================================

    def gevent_from_pool(self, url, http_request):
        """
        Get a gevent client from url and request
        :param url: URL
        :type url: URL
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :return HTTPClient
        :rtype HTTPClient
        """

        # Compute key
        key = "{0}#{1}#{2}#{3}#{4}#{5}#{6}#{7}#{8}#{9}#".format(
            # host and port
            url.host,
            url.port,
            # Ssl
            url.scheme == PROTO_HTTPS,
            # Other dynamic stuff
            http_request.https_insecure,
            http_request.disable_ipv6,
            http_request.connection_timeout_ms / 1000,
            http_request.network_timeout_ms / 1000,
            http_request.http_concurrency,
            http_request.http_proxy_host,
            http_request.http_proxy_port,
        )

        # Check
        if key in self._gevent_pool:
            return self._gevent_pool[key]

        # Allocate (in lock)
        with self._gevent_locker:
            # Check maxed
            if len(self._gevent_pool) >= self._gevent_pool_max:
                raise Exception("gevent pool maxed, cur={0}, max={1}".format(
                    len(self._gevent_pool), self._gevent_pool_max
                ))

            # Ok, allocate
            http = HTTPClient.from_url(
                url,
                insecure=http_request.https_insecure,
                disable_ipv6=http_request.disable_ipv6,
                connection_timeout=http_request.connection_timeout_ms / 1000,
                network_timeout=http_request.network_timeout_ms / 1000,
                concurrency=http_request.http_concurrency,
                proxy_host=http_request.http_proxy_host,
                proxy_port=http_request.http_proxy_port,
                headers={},
            )

            self._gevent_pool[key] = http
            logger.info("Started new pool for key=%s", key)
            return http

    # ====================================
    # URLLIB3 HTTP PROXY POOL
    # ====================================

    def urllib3_from_pool(self, http_request):
        """
        Get a u3 pool from url and request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :return Object
        :rtype Object
        """

        if not http_request.http_proxy_host:
            return self._u3_basic_pool

        # Compute key
        key = "{0}#{1}#".format(
            http_request.http_proxy_host,
            http_request.http_proxy_port,
        )

        # Check
        if key in self._u3_proxy_pool:
            return self._u3_proxy_pool[key]

        # Allocate (in lock)
        with self._u3_proxy_locker:
            # Check maxed
            if len(self._u3_proxy_pool) >= self._u3_proxy_pool_max:
                raise Exception("u3 pool maxed, cur={0}, max={1}".format(
                    len(self._u3_proxy_pool), self._u3_proxy_pool_max
                ))

            # Uri
            proxy_url = "http://{0}:{1}".format(
                http_request.http_proxy_host,
                http_request.http_proxy_port)

            # Ok, allocate
            # Force underlying fifo queue to 1024 via maxsize
            p = ProxyManager(num_pools=1024, maxsize=1024, proxy_url=proxy_url)
            self._u3_proxy_pool[key] = p
            logger.info("Started new pool for key=%s", key)
            return p

    # ====================================
    # HTTP EXEC
    # ====================================

    def go_http(self, http_request):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :return HttpResponse
        :rtype HttpResponse
        """

        ms = SolBase.mscurrent()
        http_response = HttpResponse()
        try:
            # Assign request
            http_response.http_request = http_request

            # Fire
            gevent.with_timeout(
                http_request.general_timeout_ms / 1000,
                self._go_http_internal,
                http_request, http_response)
        except Timeout:
            # Failed
            http_response.exception = Exception("Timeout while processing")
        finally:
            # Assign ms
            http_response.elapsed_ms = SolBase.msdiff(ms)

        # Return
        return http_response

    def _go_http_internal(self, http_request, http_response):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :param http_response: HttpResponse
        :type http_response: HttpResponse
        """

        try:
            # Default to gevent
            impl = http_request.force_http_implementation
            if impl == HttpClient.HTTP_IMPL_AUTO:
                # Fallback gevent (urllib3 issue with lastest uwsgi, gevent 1.1.1)
                impl = HttpClient.HTTP_IMPL_URLLIB3
                # impl = HttpClient.HTTP_IMPL_GEVENT

            # Uri
            url = URL(http_request.uri)

            # If proxy and https => urllib3
            if http_request.http_proxy_host and url.scheme == PROTO_HTTPS:
                # Fallback gevent (urllib3 issue with lastest uwsgi, gevent 1.1.1)
                impl = HttpClient.HTTP_IMPL_URLLIB3
                # impl = HttpClient.HTTP_IMPL_GEVENT

            # Log
            logger.debug("Http using impl=%s", impl)

            # Fire
            if impl == HttpClient.HTTP_IMPL_GEVENT:
                self._go_gevent(http_request, http_response)
            elif impl == HttpClient.HTTP_IMPL_URLLIB3:
                self._go_urllib3(http_request, http_response)
            else:
                raise Exception("Invalid force_http_implementation")
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            http_response.exception = e
            raise

    # ====================================
    # GEVENT
    # ====================================

    def _go_gevent(self, http_request, http_response):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :param http_response: HttpResponse
        :type http_response: HttpResponse
        """

        # Implementation
        http_response.http_implementation = HttpClient.HTTP_IMPL_GEVENT

        # Uri
        url = URL(http_request.uri)

        # Patch for path attribute error
        try:
            _ = url.path
        except AttributeError:
            url.path = "/"

        # Get instance
        logger.debug("Get pool")
        http = self.gevent_from_pool(url, http_request)
        logger.debug("Get pool done, pool=%s", http)
        SolBase.sleep(0)

        # Fire
        ms_start = SolBase.mscurrent()
        logger.debug("Http now")
        if http_request.post_data:
            # Post
            response = http.post(url.request_uri,
                                 body=http_request.post_data,
                                 headers=http_request.headers)
        else:
            # Get
            response = http.get(url.request_uri,
                                headers=http_request.headers)

        logger.debug("Http done, ms=%s", SolBase.msdiff(ms_start))
        SolBase.sleep(0)

        # Check
        if not response:
            raise Exception("No response from http")

        # Process it
        http_response.status_code = response.status_code

        # Read
        ms_start = SolBase.mscurrent()
        logger.debug("Read now")
        http_response.buffer = response.read()
        SolBase.sleep(0)
        logger.debug("Read done, ms=%s", SolBase.msdiff(ms_start))
        if response.content_length:
            http_response.content_length = response.content_length
        else:
            if http_response.buffer:
                http_response.content_length = len(http_response.buffer)
            else:
                http_response.content_length = 0

        # noinspection PyProtectedMember
        for k, v in response._headers_index.iteritems():
            http_response.headers[k] = v

        response.should_close()

        # Over
        SolBase.sleep(0)

    # ====================================
    # URLLIB3
    # ====================================

    def _go_urllib3(self, http_request, http_response):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :param http_response: HttpResponse
        :type http_response: HttpResponse
        """

        # Implementation
        http_response.http_implementation = HttpClient.HTTP_IMPL_URLLIB3

        # Get pool
        logger.debug("From pool")
        cur_pool = self.urllib3_from_pool(http_request)
        logger.debug("From pool ok")

        # From pool
        logger.debug("From pool2")
        if http_request.http_proxy_host:
            # ProxyManager : direct
            conn = cur_pool
        else:
            # Get connection from basic pool
            conn = cur_pool.connection_from_url(http_request.uri)
        logger.debug("From pool2 ok")

        # Retries
        retries = Retry(total=0,
                        connect=0,
                        read=0,
                        redirect=0)

        # Fire
        logger.debug("urlopen")
        if http_request.post_data:
            r = conn.urlopen(
                method='POST',
                url=http_request.uri,
                body=http_request.post_data,
                headers=http_request.headers,
                redirect=False,
                retries=retries,
            )
        else:
            r = conn.urlopen(
                method='GET',
                url=http_request.uri,
                headers=http_request.headers,
                redirect=False,
                retries=retries,
            )
        logger.debug("urlopen ok")

        # Ok
        http_response.status_code = r.status
        for k, v in r.headers.iteritems():
            http_response.headers[k] = v
        http_response.buffer = r.data
        http_response.content_length = len(http_response.buffer)

        # Over
        pass
