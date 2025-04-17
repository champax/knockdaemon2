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
import base64
import logging

import ujson
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class MaxscaleStat(KnockProbe):
    """
    Probe Maxscale
    Produce prefix counter : k.maxscale
    Tags: ID, HOTS
    counters:
        routed_packets :
        total_connections: total number of connections since reset or restart
        active_operations : curent query operations
        connections: current maxscale connection to backend
        state:
            Tags: Running, Master, Slave, Draining, Drained, Auth_Error, Maintenance, Slave_of_External_Master
            value: 0|1
            docs: https://mariadb.com/kb/en/mariadb-maxscale-24-mariadb-maxscale-configuration-guide/#server
        read: select
        write : other command
    """

    def __init__(self, url=None):
        """
        Constructor
        """

        self.password = None
        self.username = None
        if url:
            self.ar_url = [url]
        else:
            self.ar_url = 'http://127.0.0.1:8989/v1/'

        KnockProbe.__init__(self)

        self.category = "/sql/mariadb"

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

        # Get username and password
        self.password = d.get('password', None)
        if self.password is not None and len(self.password) > 0:
            self.username = d.get("username", None)

        # Get url
        if self.ar_url:
            logger.debug("Got (set) ar_url=%s", self.ar_url)
        elif "url" in d:
            url = d["url"].strip().lower()
            if url == "auto":
                self.ar_url = ["http://127.0.0.1:8989/v1/"]
                logger.debug("Got (auto) ar_url=%s", self.ar_url)
            else:
                self.ar_url = url.split("|")
                logger.debug("Got (load) ar_url=%s", self.ar_url)
        else:
            self.ar_url = ["http://127.0.0.1:8989/v1/"]
            logger.debug("Got (default) ar_url=%s", self.ar_url)

        # Fix if NOT list
        if not isinstance(self.ar_url, list):
            if isinstance(self.ar_url, str):
                self.ar_url = [self.ar_url]

        # Log
        logger.debug("Using u=%s, p=%s, ar=%s, from d=%s", self.username, self.password, self.ar_url, d)

    def _execute_linux(self):
        """
        Exec
        """
        self._execute_native()

    def _execute_native(self):
        """
        Execute native
        """

        # -------------------------------
        # Detect apache
        # -------------------------------
        conf_files = ['/etc/maxscale.cnf', '/etc/httpd/conf/httpd.conf']
        found = False
        conf_file = None
        for conf_file in conf_files:
            if FileUtility.is_file_exist(conf_file):
                found = True
                break
        if not found:
            logger.debug('Maxscale not found')
            return
        logger.debug("maxscale detected, using=%s", conf_file)

        # -------------------------------
        # Try uris and try process
        # -------------------------------

        for u in self.ar_url:
            logger.debug("Trying u=%s", u)

            # Try fetch
            ms_http_start = SolBase.mscurrent()
            buf_maxscale = self.fetch_maxscale_servers_url(u)
            if buf_maxscale is None:
                continue

            # Try process
            if self.process_maxscale_buffer(buf_maxscale, SolBase.msdiff(ms_http_start)):
                return

        # Here we are NOT ok
        logger.info("All Uri down, notify started=0 and return")
        self.notify_value_n("k.maxscale.started", None, 0)

    def process_maxscale_buffer(self, maxscale_buff, ms_http):
        """
        Process apache buffer, return True if ok
        :param maxscale_buff: bytes
        :type maxscale_buff: bytes
        :param ms_http: float
        :type ms_http: float
        :return bool
        :rtype bool
        """

        # Populate
        try:
            d_maxscale = ujson.loads(maxscale_buff.decode())
        except Exception as e:
            logger.error("Failed to decode maxscale buffer: %s", SolBase.extostr(e))
            return False

        logger.debug("Processing, d_maxscale=%s", d_maxscale)
        backends = d_maxscale['data']
        for backend in backends:
            backend_id = backend['id']
            attributes = backend['attributes']
            statistics = attributes['statistics']
            values = dict()
            for item in ['routed_packets', 'total_connections', 'active_operations', 'connections']:
                try:
                    values[item] = float(statistics[item])
                except KeyError as e:
                    logger.error("Failed to get statistics for %s: %s", item, SolBase.extostr(e))
                    continue
            # send result
            self.notify_value_n(f'k.maxscale.server.general', {'BACKEND': backend_id}, 1.0, d_values=values)

            # cumulate all counters
            values = dict()
            for ops in ['read', 'write']:
                count = 0
                for time_distribution in statistics['response_time_distribution'][ops]['distribution']:
                    count += time_distribution['count']
                values[ops] = float(count)
            self.notify_value_n(f'k.maxscale.server.ops', {'BACKEND': backend_id}, 1.0, d_values=values)

            # Initialize status
            all_status = {
                "Running": 0,
                "Master": 0,
                "Slave": 0,
                "Draining": 0,
                "Drained": 0,
                "Auth_Error": 0,
                "Maintenance": 0,
                "Slave_of_External_Master": 0
            }
            s_status = attributes['state']  # ie: "state": "Slave, Synced, Running",
            for status in s_status.split(','):
                status = status.strip().replace(' ', '_')
                all_status[status] = 1
                # Notify
            self.notify_value_n('k.maxscale.server.state', {'BACKEND': backend_id}, 1.0, d_values=all_status)

        # Good, notify & exit
        logger.debug("Processing ok, notify started=1 and return")
        self.notify_value_n("k.maxscale.started", None, 1)
        return True

    def fetch_maxscale_servers_url(self, url):
        """
        Fetch url and return bytes, or None if failure
        :param url: str
        :type url: str
        :return: bytes,None
        :rtype: bytes,None
        """
        url = f"{url}servers"
        try:
            # Go
            logger.debug("Trying url=%s", url)

            # Client
            hclient = HttpClient()

            # Setup request
            hreq = HttpRequest()

            # Config (low timeout here + general timeout at 2000, backend by gevent with_timeout)
            # TODO Timeout by config
            hreq.general_timeout_ms = 2000
            hreq.connection_timeout_ms = 1000
            hreq.network_timeout_ms = 1000
            hreq.general_timeout_ms = 1000
            hreq.keep_alive = False
            hreq.https_insecure = False
            # Disable caching (if we pass through varnish or similar, yeah this basterd bullshit is possible)
            hreq.headers["Cache-Control"] = "no-cache"
            hreq.force_http_implementation = HttpClient.HTTP_IMPL_GEVENT
            # Add auth
            if self.username:
                b64 = base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()
                hreq.headers.update({"Authorization": f"Basic {b64}"})

            # Uri
            hreq.uri = url

            # Fire http now
            logger.debug("Firing http now, hreq=%s", hreq)
            hresp = hclient.go_http(hreq)
            logger.debug("Got reply, hresp=%s", hresp)

            # Get response
            if hresp.status_code != 200:
                logger.debug("Give up (no http 200), sc=%s", hresp.status_code)
                return None

            # Check
            if not hresp.buffer:
                logger.debug("Give up (buffer None)")
                return None
            else:
                logger.debug("Success, len.buffer=%s", len(hresp.buffer))
                return hresp.buffer

        except Exception as e:
            logger.warning("Give up (exception), ex=%s", SolBase.extostr(e))
            return None
