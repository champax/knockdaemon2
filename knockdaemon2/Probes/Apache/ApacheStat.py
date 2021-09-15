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

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class ApacheStat(KnockProbe):
    """
    Probe
    """

    KEYS = [
        # float => per second
        # int   => current (aka cur)
        # skip  => skip

        # started :
        # 1  : RUNNING
        # 0  : FAILED

        # INTERNAL
        ("k.apache.started", "int", "k.apache.started"),

        # FROM BUFFER
        ("Total Accesses", "float", "k.apache.stat.total_accesses"),
        ("Total kBytes", "float", "k.apache.stat.total_kbytes"),
        ("Uptime", "float", "k.apache.stat.uptime"),

        # HTTP Status response time millis
        ("k.apache.status.ms", "float", "k.apache.status.ms"),

        # BUSY / IDLE
        ("BusyWorkers", "float", "k.apache.stat.busy_workers"),
        ("IdleWorkers", "float", "k.apache.stat.idle_workers"),

        # FROM SCOREBOARD
        ("k.apache.sc.waiting_for_connection", "float", "k.apache.sc.waiting_for_connection"),
        ("k.apache.sc.starting_up", "float", "k.apache.sc.starting_up"),
        ("k.apache.sc.reading_request", "float", "k.apache.sc.reading_request"),
        ("k.apache.sc.send_reply", "float", "k.apache.sc.send_reply"),
        ("k.apache.sc.keepalive", "float", "k.apache.sc.keepalive"),
        ("k.apache.sc.dns_lookup", "float", "k.apache.sc.dns_lookup"),
        ("k.apache.sc.closing", "float", "k.apache.sc.closing"),
        ("k.apache.sc.logging", "float", "k.apache.sc.logging"),
        ("k.apache.sc.gracefully", "float", "k.apache.sc.gracefully"),
        ("k.apache.sc.idle", "float", "k.apache.sc.idle"),

        # OUT OF SCOREBOARD GRAPH (aka open slot without process)
        ("k.apache.sc.open", "float", "k.apache.sc.open"),

        # *** SKIP (useless)
        ("CPULoad", "skip", "k.apache.stat.cpu_load"),
        ("ReqPerSec", "skip", "k.apache.stat.req_per_sec"),
        ("BytesPerSec", "skip", "k.apache.stat.bytes_per_sec"),
        ("BytesPerReq", "skip", "k.apache.stat.bytes_per_req"),

        # *** SKIP (seems zero)
        ("ConnsTotal", "skip", "k.apache.stat.conns_total"),

        # *** SKIP (rely on scoreboard)
        ("ConnsAsyncWriting", "skip", "k.apache.stat.conns_async_writing"),
        ("ConnsAsyncKeepAlive", "skip", "k.apache.stat.conns_async_keepalive"),
        ("ConnsAsyncClosing", "skip", "k.apache.stat.conns_async_closing"),

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

        self.category = "/web/apache"

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
            logger.info("Got (set) ar_url=%s", self.ar_url)
            return
        elif "url" in d:
            url = d["url"].strip().lower()
            if url == "auto":
                self.ar_url = ["http://127.0.0.1/server-status?auto"]
                logger.info("Got (auto) ar_url=%s", self.ar_url)
            else:
                self.ar_url = url.split("|")
                logger.info("Got (load) ar_url=%s", self.ar_url)
        else:
            self.ar_url = ["http://127.0.0.1/server-status?auto"]
            logger.info("Got (default) ar_url=%s", self.ar_url)

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
        conf_files = ['/etc/apache2/apache2.conf', '/etc/httpd/conf/httpd.conf']
        found = False
        conf_file = None
        for conf_file in conf_files:
            if FileUtility.is_file_exist(conf_file):
                found = True
                break
        if not found:
            logger.info('apache not found')
            return
        logger.info("Apache detected, using=%s", conf_file)

        # -------------------------------
        # Try uris and try process
        # -------------------------------

        pool_id = "default"

        for u in self.ar_url:
            logger.info("Trying u=%s", u)

            # Try fetch
            ms_http_start = SolBase.mscurrent()
            buf_apache = self.fetch_apache_url(u)
            if buf_apache is None:
                continue

            # Try process
            if self.process_apache_buffer(buf_apache, pool_id, SolBase.msdiff(ms_http_start)):
                return

        # Here we are NOT ok
        logger.warning("All Uri down, notify started=0 and return, pool_id=%s", pool_id)
        self.notify_value_n("k.apache.started", {"ID": pool_id}, 0)

    def process_apache_buffer(self, apache_buf, pool_id, ms_http):
        """
        Process apache buffer, return True if ok
        :param apache_buf: bytes
        :type apache_buf: bytes
        :param pool_id: str
        :type pool_id: str
        :param ms_http: float
        :type ms_http: float
        :return bool
        :rtype bool
        """

        # Populate
        d_apache = self.parse_apache_buffer(apache_buf.decode("utf8"))

        # Add ms
        d_apache["k.apache.status.ms"] = ms_http

        logger.info("Processing, d_apache=%s, pool_id=%s", d_apache, pool_id)
        for k, knock_type, knock_key in ApacheStat.KEYS:
            # Try
            if k not in d_apache:
                if k.find("k.apache.") != 0:
                    logger.warning("Unable to locate k=%s in d_apache", k)
                else:
                    logger.debug("Unable to locate k=%s in d_apache (this is expected)", k)
                continue

            # Ok, fetch and cast
            v = d_apache[k]
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
        logger.info("Processing ok, notify started=1 and return, pool_id=%s", pool_id)
        self.notify_value_n("k.apache.started", {"ID": pool_id}, 1)
        return True

    @classmethod
    def parse_apache_buffer(cls, buf_apache):
        """
        Parse apache buffer and return a dict
        :param buf_apache: str
        :type buf_apache: str
        :return dict
        :rtype dict
        """

        d_apache = dict()
        logger.debug("Parsing buf_apache=%s", repr(buf_apache))
        for line in buf_apache.split("\n"):
            line = line.strip()
            if len(line) == 0:
                continue
            c_name = None
            c_value = None
            try:
                logger.debug("Parsing line=%s", line)
                c_name, c_value = line.split(':', 2)
                c_name = c_name.strip()
                c_value = c_value.strip()
                c_value = c_value.replace("%", "")

                if c_name == 'Scoreboard':
                    cls.populate_scoreboard(c_value, d_apache)
                else:
                    d_apache[c_name] = round(float(c_value), 2)
                    logger.debug("c_name=%s, c_value=%s, h_value=%s", c_name, c_value, d_apache[c_name])
            except Exception as e:
                logger.info("Skip line (exception), line=%s, c_name=%s, c_value=%s, ex=%s", line, c_name, c_value, e)
                continue
        return d_apache

    @classmethod
    def fetch_apache_url(cls, url):
        """
        Fetch url and return bytes, or None if failure
        :param url: str
        :type url: str
        :return: bytes,None
        :rtype: bytes,None
        """

        try:
            # Fix status url (we need ?auto)
            if url.find("?auto") < 0:
                url += "?auto"

            # Go
            logger.info("Trying url=%s", url)

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
            hreq.uri = url

            # Fire http now
            logger.debug("Firing http now, hreq=%s", hreq)
            hresp = hclient.go_http(hreq)
            logger.debug("Got reply, hresp=%s", hresp)

            # Get response
            if hresp.status_code != 200:
                logger.info("Give up (no http 200), sc=%s", hresp.status_code)
                return None

            # Check
            if not hresp.buffer:
                logger.info("Give up (buffer None)")
                return None
            elif hresp.buffer.find("Scoreboard") < 0:
                logger.info("Give up (no Scoreboard)")
                return None
            else:
                logger.info("Success, len.buffer=%s", len(hresp.buffer))
                return hresp.buffer

        except Exception as e:
            logger.warning("Give up (exception), ex=%s", SolBase.extostr(e))
            return None

    @classmethod
    def populate_scoreboard(cls, s, d_apache):
        """
        Get score by type and populate d_apache
        :param s: str
        :type s: str
        :param d_apache: dict
        :type d_apache: dict
        """

        # Scoreboard Key
        # "_" Waiting for Connectio
        # "S" Starting u
        # "R" Reading Request
        # "W" Sending Reply
        # "K" Keepalive (read)
        # "D" DNS Lookup
        # "C" Closing connection
        # "L" Logging
        # "G" Gracefully finishing
        # "I" Idle cleanup of worker
        # "." Open slot with no current process

        d_apache["k.apache.sc.waiting_for_connection"] = cls.get_scoreboard_metric(s, "_")
        d_apache["k.apache.sc.starting_up"] = cls.get_scoreboard_metric(s, "S")
        d_apache["k.apache.sc.reading_request"] = cls.get_scoreboard_metric(s, "R")
        d_apache["k.apache.sc.send_reply"] = cls.get_scoreboard_metric(s, "W")
        d_apache["k.apache.sc.keepalive"] = cls.get_scoreboard_metric(s, "K")
        d_apache["k.apache.sc.dns_lookup"] = cls.get_scoreboard_metric(s, "D")
        d_apache["k.apache.sc.closing"] = cls.get_scoreboard_metric(s, "C")
        d_apache["k.apache.sc.logging"] = cls.get_scoreboard_metric(s, "L")
        d_apache["k.apache.sc.gracefully"] = cls.get_scoreboard_metric(s, "G")
        d_apache["k.apache.sc.idle"] = cls.get_scoreboard_metric(s, "I")
        d_apache["k.apache.sc.open"] = cls.get_scoreboard_metric(s, ".")

    @classmethod
    def get_scoreboard_metric(cls, s, metric):
        """
        Get metric
        :param s: str
        :type s: str
        :param metric: str
        :type metric: str
        :return int
        :rtype int
        """
        return s.count(metric)
