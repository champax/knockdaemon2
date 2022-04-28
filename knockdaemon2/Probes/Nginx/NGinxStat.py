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
import re

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class NginxStat(KnockProbe):
    """
    Probe
    """

    KEYS = [
        # float => per second
        # int   => current (aka cur)
        # k.x   => internal

        # started :
        # 1  : RUNNING
        # 0  : FAILED

        # INTERNAL
        ("k.nginx.started", "int", "k.nginx.started"),

        # NGINX Status http millis
        ("k.nginx.status.ms", "float", "k.nginx.status.ms"),

        # ACCEPT / REQUEST PER SEC
        ("accepted", "float", "k.nginx.accepted"),
        ("requests", "float", "k.nginx.requests"),

        # CURRENT CONNECTION
        ("connections", "int", "k.nginx.connections"),

        # CURRENT CONNECTION STATUS
        ("reading", "int", "k.nginx.reading"),
        ("writing", "int", "k.nginx.writing"),
        ("waiting", "int", "k.nginx.waiting"),

        # SKIP (useless)
        ("handled", "skip", "k.nginx.handled"),
    ]

    def __init__(self, url=None):
        """
        Constructor
        """

        if url:
            self.ar_url = [url]
        else:
            self.ar_url = None

        KnockProbe.__init__(self)
        self.category = "/web/nginx"

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
        if self.ar_url:
            logger.debug("Got (set) ar_url=%s", self.ar_url)
            return
        elif "url" in d:
            url = d["url"].strip().lower()
            if url == "auto":
                self.ar_url = ["http://127.0.0.1/nginx_status"]
                logger.debug("Got (auto) ar_url=%s", self.ar_url)
            else:
                self.ar_url = url.split("|")
                logger.debug("Got (load) ar_url=%s", self.ar_url)
        else:
            self.ar_url = ["http://127.0.0.1/nginx_status"]
            logger.debug("No url from config, using default")

    def _execute_linux(self):
        """
        Exec
        """

        self._execute_native()

    def _execute_native(self):
        """
        Exec, native
        """

        # Detect nginx
        if not FileUtility.is_file_exist('/etc/nginx/nginx.conf'):
            logger.debug("Give up (/etc/nginx/nginx.conf not found)")
            return
        logger.debug("Nginx detected (/etc/nginx/nginx.conf found)")

        pool_id = "default"

        # -------------------------------
        # Loop and try uris
        # -------------------------------

        for u in self.ar_url:
            logger.debug("Trying u=%s", u)

            # Fetch
            ms_http_start = SolBase.mscurrent()
            buf_nginx = self.fetch_nginx_url(u)
            if not buf_nginx:
                continue

            # Try process
            if self.process_nginx_buffer(buf_nginx, pool_id, SolBase.msdiff(ms_http_start)):
                return

        # Here we are NOT ok
        logger.warning("All Uri down, notify started=0 and return, pool_id=%s", pool_id)
        self.notify_value_n("k.nginx.started", {"ID": pool_id}, 0)

    def process_nginx_buffer(self, nginx_buf, pool_id, ms_http):
        """
        Process nginx buffer, return True if ok
        :param nginx_buf: bytes
        :type nginx_buf: bytes
        :param pool_id: str
        :type pool_id: str
        :param ms_http: float
        :type ms_http: float
        :return bool
        :rtype bool
        """

        try:
            d_nginx = self.parse_nginx_buffer(nginx_buf.decode("utf8"))

            # Add http millis
            d_nginx["k.nginx.status.ms"] = ms_http

            # Go
            for k, knock_type, knock_key in NginxStat.KEYS:
                # Try
                if k not in d_nginx:
                    if k.find("k.nginx.") != 0:
                        logger.warning("Unable to locate k=%s in d_nginx", k)
                    else:
                        logger.debug("Unable to locate k=%s in d_nginx (this is expected)", k)
                    continue

                # Ok, fetch and cast
                v = d_nginx[k]
                if knock_type == "int":
                    v = int(v)
                elif knock_type == "float":
                    v = float(v)
                elif knock_type == "str":
                    v = str(v)
                elif knock_type == "skip":
                    logger.debug("Skipping type=%s", knock_type)
                    continue
                else:
                    logger.warning("Not managed type=%s", knock_type)

                # Notify
                self.notify_value_n(knock_key, {"ID": pool_id}, v)

            # Good, notify & exit
            logger.debug("Processing, notify started=1 and return, pool_id=%s", pool_id)
            self.notify_value_n("k.nginx.started", {"ID": pool_id}, 1)
            return True
        except Exception as e:
            logger.debug("Ex=%s", SolBase.extostr(e))
            return False

    @classmethod
    def fetch_nginx_url(cls, url):
        """
        Fetch url and return buffer
        :param url: str
        :type url: str
        :return: bytes,None
        :rtype: bytes,None
        """

        try:
            # Go
            logger.debug("Processing url=%s", url)

            # Client
            hclient = HttpClient()

            # Setup request
            hreq = HttpRequest()

            # Config (low timeout here + general timeout at 2000, backend by gevent with_timeout)
            # TODO Timeout by config
            hreq.general_timeout_ms = 2000
            hreq.connection_timeout_ms = 1500
            hreq.network_timeout_ms = 1500
            hreq.keep_alive = False
            hreq.https_insecure = False

            # Disable caching (if we pass through varnish or similar, yeah this basterd bullshit is possible)
            hreq.headers["Cache-Control"] = "no-cache"

            # Uri
            hreq.uri = url

            # Fire http now
            logger.debug("Firing http now, hreq=%s", hreq)
            hresp = hclient.go_http(hreq)
            logger.debug("Got reply, hresp=%s", hresp)

            # Get response
            if hresp.status_code != 200:
                logger.info("No http 200, give up, uri=%s, status_code=%s", hreq.uri, hresp.status_code)
                return None

            # Check
            if not hresp.buffer:
                logger.info("No buffer, give up, uri=%s, status_code=%s", hreq.uri, hresp.status_code)
                return None
            return hresp.buffer
        except Exception as e:
            logger.warning("Exception, ex=%s", SolBase.extostr(e))
            return None

    @classmethod
    def parse_nginx_buffer(cls, buf_nginx):
        """
        Parse nginx buffer
        :param buf_nginx: str
        :type buf_nginx: str
        :return dict,None
        :rtype dict,None
        """

        if buf_nginx.find("Active connections") < 0:
            logger.debug("Give up (no Active connections)")
            return None

        # Got it : parse
        d_nginx = dict()
        logger.debug("Parsing buf_nginx=%s", repr(buf_nginx))

        match1 = re.search(r'Active connections:\s+(\d+)', buf_nginx)
        match2 = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', buf_nginx)
        match3 = re.search(r'Reading:\s*(\d+)\s*Writing:\s*(\d+)\s*Waiting:\s*(\d+)', buf_nginx)

        if not match1 or not match2 or not match3:
            logger.debug("Unable to parse (re miss), match1=%s, match2=%s, match3=%s", match1, match2, match3)
            return None

        d_nginx['connections'] = int(match1.group(1))
        d_nginx['accepted'] = int(match2.group(1))
        d_nginx['handled'] = int(match2.group(2))
        d_nginx['requests'] = int(match2.group(3))
        d_nginx['reading'] = int(match3.group(1))
        d_nginx['writing'] = int(match3.group(2))
        d_nginx['waiting'] = int(match3.group(3))

        # Over
        return d_nginx
