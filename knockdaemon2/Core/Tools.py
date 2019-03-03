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
from base64 import b64encode
from urllib import urlencode

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
        :param notify_values: List of (superv_key, tag, value, d_opt_tags). Cleared upon success.
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
        # list : tuple (probe_name, disco_value, value, timestamp)
        # notify_values => <type 'list'>: [('test.dummy.count', 'all', 100, 1503045097.626604), ('test.dummy.count', 'one', 90, 1503045097.626629), ('test.dummy.count[two]', None, 10, 1503045097.626639), ('test.dummy.error', 'all', 5, 1503045097.62668), ('test.dummy.error', 'one', 3, 1503045097.626704), ('test.dummy.error', 'two', 2, 1503045097.626728)]

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
        assert len(node_hash) == 1, "len(node_hash) must be 1, got node_hash={0}".format(node_hash)
        c_host = node_hash["host"]
        logger.debug("Processing c_host=%s", c_host)

        # Process data and build output dict
        ar_out = list()
        for item in notify_values:
            # additional_fields : default value {}
            if len(item) == 5:
                probe_name, dd, value, timestamp, d_opt_tags = item
                additional_fields = {}
            else:
                probe_name, dd, value, timestamp, d_opt_tags, additional_fields = item

            # We got a unix timestamp (1503045097.626604)
            # Convert it to required date format
            dt_temp = SolBase.dt_ensure_utc_naive(SolBase.epoch_to_dt(timestamp))
            s_dt_temp = dt_temp.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Init
            d_tags = {"host": c_host, "ns": account_hash["acc_namespace"]}

            # Discovery
            if dd:
                d_tags.update(dd)

            # Add optional tags
            if d_opt_tags:
                d_tags.update(d_opt_tags)

            f_dict = {"value": value}
            f_dict.update(additional_fields)

            # Build
            d_temp = {
                "measurement": probe_name,
                "tags": d_tags,
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

        return {
            "Authorization": "Basic " + b64encode(b':'.join((username, password)))
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
            'Content-type': u'application/json'
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
            http_req.uri = "http://{0}:{1}/query?{2}".format(host, port, s_qs)
        http_req.method = "POST"

        # Go
        logger.info("Influx, http go, req=%s", http_req)
        logger.info("Influx, http go, post_data=%s", repr(http_req.post_data))
        http_rep = http_client.go_http(http_req)

        # Ok
        logger.info("Influx, http reply, rep=%s", http_rep)
        logger.info("Influx, http reply, buf=%s", repr(http_rep.buffer))
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
            'Content-type': u'application/json'
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
            http_req.uri = "http://{0}:{1}/query?{2}".format(host, port, s_qs)
        http_req.method = "POST"

        # Go
        logger.info("Influx, http go, req=%s", http_req)
        logger.info("Influx, http go, post_data=%s", repr(http_req.post_data))
        http_rep = http_client.go_http(http_req)

        # Ok
        logger.info("Influx, http reply, rep=%s", http_rep)
        logger.info("Influx, http reply, buf=%s", repr(http_rep.buffer))
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
            'Content-type': u'application/octet-stream'
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
            http_req.uri = "http://{0}:{1}/write?{2}".format(host, port, s_qs)
        http_req.method = "POST"
        http_req.post_data = ('\n'.join(ar_data) + '\n').encode('utf-8')
        assert http_req.post_data.endswith("\n\n"), "Need \n\n ended post_data, got={0}".format(http_req.post_data[:-16])

        # Go
        logger.info("Influx, http go, req=%s", http_req)
        logger.debug("Influx, http go, post_data=%s", repr(http_req.post_data))
        http_rep = http_client.go_http(http_req)

        # Ok
        logger.info("Influx, http reply, rep=%s", http_rep)
        logger.info("Influx, http reply, buf=%s", repr(http_rep.buffer))
        return http_rep
