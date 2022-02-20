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
from base64 import b64encode
from urllib.parse import urlencode

from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

logger = logging.getLogger(__name__)


class Tools(object):
    """
    Tools
    """

    # ==========================================
    # INFLUX CONVERT
    # ==========================================

    @classmethod
    def to_influx_format(cls, account_hash, node_hash, notify_values):
        """
        Process notify
        :param account_hash: Hash str to value
        :type account_hash; dict
        :param node_hash: Hash str to value
        :type node_hash; dict
        :param notify_values: List of (counter_key, d_tags, value, d_values). Cleared upon success.
        :type notify_values; list
        :return list of dict
        :rtype list
        """

        # We receive :
        # dict string/string
        # account_hash => {'acc_key': 'tamereenshort', 'acc_namespace': 'unittest'}
        #
        # dict string/string
        # node_hash => {'host': 'klchgui01'}
        #
        # dict string (formatted) => tuple (disco_name, disco_id, disco_value)
        # notify_hash => {'test.dummy|TYPE|one': ('test.dummy', 'TYPE', 'one'), 'test.dummy|TYPE|all': ('test.dummy', 'TYPE', 'all'), 'test.dummy|TYPE|two': ('test.dummy', 'TYPE', 'two')}
        #
        # list : List of (counter_key, d_tags, value, d_values). Cleared upon success.

        # We must send blocks like :
        # [
        #     {
        #         "measurement": "cpu_load_short",
        #         "tags": {"host": "server01", "region": "us-west"},
        #         "time": "2009-11-10T23:00:00Z",
        #         "fields": {"value": 0.64}
        #     },
        #     ...
        #     {....}
        # ]

        # Get host
        if not len(node_hash) == 1:
            raise Exception("len(node_hash) must be 1, got node_hash={0}".format(node_hash))
        c_host = node_hash["host"]
        logger.debug("Processing c_host=%s", c_host)

        # Process data and build output dict
        ar_out = list()
        for counter_key, d_tags, value, timestamp, d_values in notify_values:

            # We got a unix timestamp (1503045097.626604)
            # Convert it to required date format
            dt_temp = SolBase.dt_ensure_utc_naive(SolBase.epoch_to_dt(timestamp))
            s_dt_temp = dt_temp.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Tags dict
            d_tags_effective = {"host": c_host, "ns": account_hash["acc_namespace"]}
            d_tags_effective.update(d_tags)

            # Value dict
            f_dict = {"value": value}
            if d_values:
                if "value" in d_values:
                    raise Exception("Got 'value' key in d_value (will lost it - not allowed)")
                f_dict.update(d_values)

            # Build
            d_temp = {
                "measurement": counter_key,
                "tags": d_tags_effective,
                "time": s_dt_temp,
                "fields": f_dict
            }
            logger.debug("Built, d_temp=%s", d_temp)
            ar_out.append(d_temp)

        # Over
        return ar_out

    @classmethod
    def influx_get_auth_header(cls, username, password):
        """
        Get auth header
        :param username: str
        :type username: str
        :param password: str
        :type password: str
        :return dict "Authorization" : "Basic ..."
        :rtype dict
        """

        buf = ':'.join((username, password))
        bin_buf = buf.encode("utf8")
        bin_b64 = b64encode(bin_buf)
        b64 = bin_b64.decode("utf8")
        return {
            "Authorization": "Basic " + b64
        }

    @classmethod
    def influx_create_database(cls, http_client, host, port, username, password, database, timeout_ms, ssl, verify_ssl):
        """
        Influx create database
        :param http_client: pysolhttpclient.Http.HttpClient.HttpClient
        :type http_client: pysolhttpclient.Http.HttpClient.HttpClient
        :param host: str
        :type host: str
        :param port: int
        :type port: int
        :param username: str
        :type username: str
        :param password: str
        :type password: str
        :param database: str
        :type database: str
        :param timeout_ms: int
        :type timeout_ms: int
        :param ssl: bool
        :type ssl: bool
        :param verify_ssl: bool
        :type verify_ssl: bool
        :return pysolhttpclient.Http.HttpResponse.HttpResponse
        :rtype pysolhttpclient.Http.HttpResponse.HttpResponse
        """

        # Build request
        http_req = HttpRequest()
        http_req.force_http_implementation = HttpClient.HTTP_IMPL_GEVENT
        http_req.general_timeout_ms = timeout_ms
        http_req.connection_timeout_ms = timeout_ms
        http_req.network_timeout_ms = timeout_ms
        http_req.headers = {
            "Accept-Encoding": "gzip",
            "Accept": "text / plain",
            'Content-type': 'application/json'
        }
        d_auth = cls.influx_get_auth_header(username, password)
        http_req.headers.update(d_auth)

        # Need 'http://127.0.0.1:8286/query?q=CREATE+DATABASE+%22zzz2%22&db=zzz2'
        d_qs = {
            "q": "CREATE DATABASE " + database,
            "db": database
        }
        s_qs = urlencode(d_qs)
        if ssl:
            http_req.uri = "https://{0}:{1}/query?{2}".format(host, port, s_qs)
            if verify_ssl:
                http_req.https_insecure = True
            else:
                http_req.https_insecure = False
        else:
            # noinspection HttpUrlsUsage
            http_req.uri = "http://{0}:{1}/query?{2}".format(host, port, s_qs)
        http_req.method = "POST"

        # Go
        logger.debug("Influx, http go, req=%s", http_req)
        logger.debug("Influx, http go, post_data=%s", repr(http_req.post_data))
        http_rep = http_client.go_http(http_req)

        # Ok
        logger.debug("Influx, http reply, rep=%s", http_rep)
        logger.debug("Influx, http reply, buf=%s", repr(http_rep.buffer))
        return http_rep

    @classmethod
    def influx_drop_database(cls, http_client, host, port, username, password, database, timeout_ms, ssl, verify_ssl):
        """
        Influx drop database
        :param http_client: pysolhttpclient.Http.HttpClient.HttpClient
        :type http_client: pysolhttpclient.Http.HttpClient.HttpClient
        :param host: str
        :type host: str
        :param port: int
        :type port: int
        :param username: str
        :type username: str
        :param password: str
        :type password: str
        :param database: str
        :type database: str
        :param timeout_ms: int
        :type timeout_ms: int
        :param ssl: bool
        :type ssl: bool
        :param verify_ssl: bool
        :type verify_ssl: bool
        :return pysolhttpclient.Http.HttpResponse.HttpResponse
        :rtype pysolhttpclient.Http.HttpResponse.HttpResponse
        """

        # Build request
        http_req = HttpRequest()
        http_req.force_http_implementation = HttpClient.HTTP_IMPL_GEVENT
        http_req.general_timeout_ms = timeout_ms
        http_req.connection_timeout_ms = timeout_ms
        http_req.network_timeout_ms = timeout_ms
        http_req.headers = {
            "Accept-Encoding": "gzip",
            "Accept": "text / plain",
            'Content-type': 'application/json'
        }
        d_auth = cls.influx_get_auth_header(username, password)
        http_req.headers.update(d_auth)

        # Need 'http://127.0.0.1:8286/query?q=DROP+DATABASE+%22zzz2%22&db=zzz2'
        d_qs = {
            "q": "DROP DATABASE " + database,
            "db": database
        }
        s_qs = urlencode(d_qs)
        if ssl:
            http_req.uri = "https://{0}:{1}/query?{2}".format(host, port, s_qs)
            if verify_ssl:
                http_req.https_insecure = True
            else:
                http_req.https_insecure = False
        else:
            # noinspection HttpUrlsUsage
            http_req.uri = "http://{0}:{1}/query?{2}".format(host, port, s_qs)
        http_req.method = "POST"

        # Go
        logger.debug("Influx, http go, req=%s", http_req)
        logger.debug("Influx, http go, post_data=%s", repr(http_req.post_data))
        http_rep = http_client.go_http(http_req)

        # Ok
        logger.debug("Influx, http reply, rep=%s", http_rep)
        logger.debug("Influx, http reply, buf=%s", repr(http_rep.buffer))
        return http_rep

    @classmethod
    def influx_write_data(cls, http_client, host, port, username, password, database, ar_data, timeout_ms, ssl, verify_ssl):
        """
        Influx write data
        :param http_client: pysolhttpclient.Http.HttpClient.HttpClient
        :type http_client: pysolhttpclient.Http.HttpClient.HttpClient
        :param host: str
        :type host: str
        :param port: int
        :type port: int
        :param username: str
        :type username: str
        :param password: str
        :type password: str
        :param database: str
        :type database: str
        :param ar_data: list of str
        :type ar_data: list
        :param timeout_ms: int
        :type timeout_ms: int
        :param ssl: bool
        :type ssl: bool
        :param verify_ssl: bool
        :type verify_ssl: bool
        :return pysolhttpclient.Http.HttpResponse.HttpResponse
        :rtype pysolhttpclient.Http.HttpResponse.HttpResponse
        """

        # Build request
        http_req = HttpRequest()
        http_req.force_http_implementation = HttpClient.HTTP_IMPL_GEVENT
        http_req.general_timeout_ms = timeout_ms
        http_req.connection_timeout_ms = timeout_ms
        http_req.network_timeout_ms = timeout_ms
        http_req.headers = {
            "Accept-Encoding": "gzip",
            "Accept": "text / plain",
            'Content-type': 'application/octet-stream'
        }
        d_auth = cls.influx_get_auth_header(username, password)
        http_req.headers.update(d_auth)

        # Need 'http://127.0.0.1:8286/write?db=zzz2'
        d_qs = {
            "db": database
        }
        s_qs = urlencode(d_qs)
        if ssl:
            http_req.uri = "https://{0}:{1}/write?{2}".format(host, port, s_qs)
            if verify_ssl:
                http_req.https_insecure = True
            else:
                http_req.https_insecure = False
        else:
            # noinspection HttpUrlsUsage
            http_req.uri = "http://{0}:{1}/write?{2}".format(host, port, s_qs)
        http_req.method = "POST"
        http_req.post_data = ('\n'.join(ar_data) + '\n').encode('utf8')
        if not http_req.post_data.decode("utf8").endswith("\n\n"):
            raise Exception("Need \n\n ended post_data, got={0}".format(http_req.post_data[:-16]))

        # Go
        logger.debug("Influx, http go, req=%s", http_req)
        logger.debug("Influx, http go, post_data=%s", repr(http_req.post_data))
        http_rep = http_client.go_http(http_req)

        # Ok
        logger.debug("Influx, http reply, rep=%s", http_rep)
        logger.debug("Influx, http reply, buf=%s", repr(http_rep.buffer))
        return http_rep
