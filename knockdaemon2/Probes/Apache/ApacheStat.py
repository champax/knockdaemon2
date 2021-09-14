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
            logger.info("Skip loading ar_url from config (already set), ar_url=%s", self.ar_url)
            return

        if "url" in d:
            logger.info("Loading url from config")
            url = d["url"]
            url = url.strip()

            if url.lower() == "auto":
                logger.info("Auto url from config, using default")
                self.ar_url = ["http://127.0.0.1/server-status?auto"]
            else:
                self.ar_url = url.split("|")
        else:
            logger.info("No url from config, using default")
            self.ar_url = ["http://127.0.0.1/server-status?auto"]

        logger.info("Set ar_url=%s", self.ar_url)

    def _execute_linux(self):
        """
        Exec
        """
        conf_files = ['/etc/apache2/apache2.conf', '/etc/httpd/conf/httpd.conf']
        found = False
        for conf_file in conf_files:

            if FileUtility.is_file_exist(conf_file):
                found = True
                break
        if not found:
            logger.info('apache not found')
            return

        logger.info("Apache detected (/etc/apache2/apache2.conf found)")

        # -------------------------------
        # P0 : Fire discoveries
        # -------------------------------
        logger.info("Firing discoveries (default)")
        pool_id = "default"
        self.notify_discovery_n("k.apache.discovery", {"ID": pool_id})

        # -------------------------------
        # Loop and try uris
        # -------------------------------

        for u in self.ar_url:
            logger.info("Trying u=%s", u)

            # Fetch
            ms_http_start = SolBase.mscurrent()
            d_apache = self.fetch_url(u)
            ms_http = SolBase.msdiff(ms_http_start)

            # Check
            if not d_apache:
                logger.info("Url failed, skip, u=%s", u)
                continue

            # Add http millis
            d_apache["k.apache.status.ms"] = ms_http

            # -------------------------------
            # Got a dict, fine, send everything browsing our keys
            # -------------------------------
            ok = self.process_apache_dict(d_apache, pool_id)
            if ok:
                return

        # Here we are NOT ok
        logger.warning("All Uri down, notify started=0 and return, pool_id=%s", pool_id)
        self.notify_value_n("k.apache.started", {"ID": pool_id}, 0)

    def process_apache_dict(self, d_apache, pool_id):
        """
        Process apache dict, return True if ok
        :param d_apache: dict
        :type d_apache: dict
        :param pool_id: str
        :type pool_id: str
        :return bool
        :rtype bool
        """

        logger.info("Processing, d_apache=%s, pool_id=%s", d_apache, pool_id)
        for k, knock_type, knock_key in ApacheStat.KEYS:
            # Try
            if k not in d_apache:
                if k.find("k.apache.") != 0:
                    logger.warning("Unable to locate k=%s in d_apache", k)
                else:
                    logger.info("Unable to locate k=%s in d_apache (this is expected)", k)
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
        logger.info("Dict processing ok, notify started=1 and return, pool_id=%s", pool_id)
        self.notify_value_n("k.apache.started", {"ID": pool_id}, 1)
        return True

    def parser_apache_buffer(self, pd):
        """
        Parse apache buffer and return a dict
        :param pd: str
        :type pd: str
        :return dict
        :rtype dict
        """

        d_apache = dict()
        logger.debug("Parsing pd=%s", repr(pd))
        for line in pd.split("\n"):
            line = line.strip()

            if len(line) == 0:
                logger.debug("Skip line=%s", line)
                continue

            c_name = None
            c_value = None
            try:
                logger.debug("Parsing line=%s", line)
                (c_name, c_value) = line.split(':', 2)

                c_name = c_name.strip()

                c_value = c_value.strip()
                c_value = c_value.replace("%", "")

                if c_name == 'Scoreboard':
                    self.populate_scoreboard(c_value, d_apache)
                else:
                    d_apache[c_name] = round(float(c_value), 2)
                    logger.info("c_name=%s, c_value=%s, h_value=%s", c_name, c_value, d_apache[c_name])
            except Exception as e:
                logger.warning("Parsing failed, line=%s, c_name=%s, c_value=%s, ex=%s", line, c_name, c_value, e)
                continue

        return d_apache

    def fetch_url(self, url_status):
        """
        Fetch url and return a dict, or None if failure
        :param url_status: str
        :type url_status: str
        :return: dict,None
        :rtype: dict,None
        """

        try:
            # Fix status url (we need ?auto)
            if url_status.find("?auto") < 0:
                url_status += "?auto"

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
            elif pd.find("Scoreboard") < 0:
                logger.warning("Invalid buffer (no Scoreboard), give up")
                return None

            # Got it : parse
            d_apache = self.parser_apache_buffer(pd)

            # Over
            logger.info("Url hit, d_apache=%s", d_apache)
            return d_apache

        except Exception as e:
            logger.warning("Exception, ex=%s", SolBase.extostr(e))
            return None

    def populate_scoreboard(self, string, d_apache):
        """
        Get score by type and populate d_apache
        :param string: str
        :type string: str
        :param d_apache: dict
        :type d_apache: dict
        """

        logger.info("Populate scoreboard now")

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

        d_apache["k.apache.sc.waiting_for_connection"] = self.get_scoreboard_metric(string, "_")
        d_apache["k.apache.sc.starting_up"] = self.get_scoreboard_metric(string, "S")
        d_apache["k.apache.sc.reading_request"] = self.get_scoreboard_metric(string, "R")
        d_apache["k.apache.sc.send_reply"] = self.get_scoreboard_metric(string, "W")
        d_apache["k.apache.sc.keepalive"] = self.get_scoreboard_metric(string, "K")
        d_apache["k.apache.sc.dns_lookup"] = self.get_scoreboard_metric(string, "D")
        d_apache["k.apache.sc.closing"] = self.get_scoreboard_metric(string, "C")
        d_apache["k.apache.sc.logging"] = self.get_scoreboard_metric(string, "L")
        d_apache["k.apache.sc.gracefully"] = self.get_scoreboard_metric(string, "G")
        d_apache["k.apache.sc.idle"] = self.get_scoreboard_metric(string, "I")
        d_apache["k.apache.sc.open"] = self.get_scoreboard_metric(string, ".")

    # noinspection PyMethodMayBeStatic
    def get_scoreboard_metric(self, string, metric):
        """
        doc
        :param metric: metric
        :param string: string
        :return:
        """
        return string.count(metric)
