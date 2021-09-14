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
import re

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest
from urllib3.exceptions import MaxRetryError

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class NginxStat(KnockProbe):
    """
    Probe
    """

    # TODO : Max connection from config + trigger

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
            logger.info("Skip loading ar_url from config (already set), ar_url=%s", self.ar_url)
            return

        if "url" in d:
            logger.info("Loading url from config")
            url = d["url"]
            url = url.strip()

            if url.lower() == "auto":
                logger.info("Auto url from config, using default")
                self.ar_url = ["http://127.0.0.1/nginx_status"]
            else:
                self.ar_url = url.split("|")
        else:
            logger.info("No url from config, using default")
            self.ar_url = ["http://127.0.0.1/nginx_status"]

        logger.info("Set ar_url=%s", self.ar_url)

    def _execute_linux(self):
        """
        Exec
        """

        if not FileUtility.is_file_exist('/etc/nginx/nginx.conf'):
            logger.info("Give up (/etc/nginx/nginx.conf not found)")
            return

        logger.info("Nginx detected (/etc/nginx/nginx.conf found)")

        pool_id = "default"

        # -------------------------------
        # Loop and try uris
        # -------------------------------

        for u in self.ar_url:
            logger.info("Trying u=%s", u)

            # Fetch
            ms_http_start = SolBase.mscurrent()
            try:
                d_nginx = self.fetch_url(u)
            except MaxRetryError:
                d_nginx = None
            ms_http = SolBase.msdiff(ms_http_start)

            # Check
            if not d_nginx:
                logger.info("Url failed, skip, u=%s", u)
                continue

            # Add http millis
            d_nginx["k.nginx.status.ms"] = ms_http

            # -------------------------------
            # Got a dict, fine, send everything browsing our keys
            # -------------------------------
            logger.info("Url reply ok, firing notify now")
            for k, knock_type, knock_key in NginxStat.KEYS:
                # Try
                if k not in d_nginx:
                    if k.find("k.nginx.") != 0:
                        logger.warning("Unable to locate k=%s in d_nginx", k)
                    else:
                        logger.info("Unable to locate k=%s in d_nginx (this is expected)", k)
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
            logger.info("Uri ok, notify started=1 and return, pool_id=%s", pool_id)
            self.notify_value_n("k.nginx.started", {"ID": pool_id}, 1)
            return

        # Here we are NOT ok
        logger.warning("All Uri down, notify started=0 and return, pool_id=%s", pool_id)
        self.notify_value_n("k.nginx.started", {"ID": pool_id}, 0)

    # noinspection PyMethodMayBeStatic
    def fetch_url(self, url_status):
        """
        Fetch url and return a dict
        :param url_status: str
        :type url_status: str
        :return: dict,None
        :rtype: dict,None
        """

        try:
            # Go
            logger.info("Processing url_status=%s", url_status)

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

            # Uri
            hreq.uri = url_status

            # Fire http now
            logger.info("Firing http now, hreq=%s", hreq)
            hresp = hclient.go_http(hreq)
            logger.info("Got reply, hresp=%s", hresp)

            # Get response
            if hresp.status_code != 200:
                logger.warning("No http 200, give up")
                return None

            # Get buffer
            pd = hresp.buffer

            # Check
            if not pd:
                logger.warning("No buffer, give up")
                return None
            elif pd.find("Active connections") < 0:
                logger.warning("Invalid buffer (no Active connections), give up")
                return None

            # Got it : parse
            d_nginx = dict()
            logger.debug("Parsing pd=%s", repr(pd))

            match1 = re.search(r'Active connections:\s+(\d+)', pd)
            match2 = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', pd)
            match3 = re.search(r'Reading:\s*(\d+)\s*Writing:\s*(\d+)\s*Waiting:\s*(\d+)', pd)

            if not match1 or not match2 or not match3:
                logger.warning('Unable to parse %s, uri=%s, pd=%s', url_status, pd)
                return None

            d_nginx['connections'] = int(match1.group(1))

            d_nginx['accepted'] = int(match2.group(1))
            d_nginx['handled'] = int(match2.group(2))
            d_nginx['requests'] = int(match2.group(3))

            d_nginx['reading'] = int(match3.group(1))

            d_nginx['writing'] = int(match3.group(2))
            d_nginx['waiting'] = int(match3.group(3))

            # Over
            logger.info("Url hit, d_nginx=%s", d_nginx)
            return d_nginx

        except Exception as e:
            logger.warning("Exception, ex=%s", SolBase.extostr(e))
            return None
