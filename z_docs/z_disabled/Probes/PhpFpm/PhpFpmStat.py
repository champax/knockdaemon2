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
import glob
import logging
import re

import ujson
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class PhpFpmStat(KnockProbe):
    """
    Probe
    """

    AR_FPM_CONFIG_FILE = [
        # Debian
        "/etc/init.d/php5-fpm",
        # Centos
        "/etc/php-fpm.conf",
    ]

    # TODO : Request per second somewhere ??

    KEYS = [
        # float => per second
        # int   => current (aka cur)
        # k.x   => internal

        # started :
        # 1  : RUNNING
        # 0  : FAILED

        # INTERNAL
        ("k.phpfpm.started", "int", "k.phpfpm.started"),

        # HTTP MILLIS
        ("k.phpfpm.status.ms", "float", "k.phpfpm.status.ms"),

        # START
        ("start since", "int", "k.phpfpm.start_since"),

        # QUEUE (current and upper limit)
        ("listen queue", "int", "k.phpfpm.listen_queue"),
        ("listen queue len", "int", "k.phpfpm.listen_queue_limit"),

        # SCOREBOARD
        ("active processes", "int", "k.phpfpm.active_processes"),
        ("idle processes", "int", "k.phpfpm.idle_processes"),

        # PER SEC : Connection
        ("accepted conn", "float", "k.phpfpm.accepted_conn"),

        # DOC :
        # listen_queue_len :        maximum number of connections that will be queued. Once this limit is reached, subsequent connections will either be refused, or ignored.
        # listen_queue :            the number of connections that have been initiated by not yet accepted
        # max listen queue:         the maximum value the listen queue has reached while php-fpm has been running. => SKIP
        # max active processes      the maximum number of active processes since FPM has started
        # max children reached      the number of times the process limit has been reached, when pm tries to start more children
        # total processes           the number of idle + active processes
        # slow requests             the number of requests that exceeded your request_slowlog_timeout value

        # SKIP
        ("max listen queue", "skip", "k.phpfpm.max_listen_queue"),

        # SKIP
        ("max active processes", "skip", "k.phpfpm.max_active_processes"),
        ("max children reached", "skip", "k.phpfpm.max_children_reached"),

        # SKIP
        ("total processes", "skip", "k.phpfpm.total_processes"),

        # SKIP
        ("start time", "skip", "k.phpfpm.start_time"),

        # SKIP
        ("slow requests", "skip", "k.phpfpm.slow_requests"),

        # SKIP
        ("process manager", "skip", "k.phpfpm.process_manager"),
        ("pool", "skip", "k.phpfpm.pool"),
    ]

    def __init__(self, d_pool_from_url=None):
        """
        Constructor
        :param d_pool_from_url: None,dict
        :type d_pool_from_url: None,dict
        """

        self._d_pool_from_url = d_pool_from_url
        self._d_all = dict()
        KnockProbe.__init__(self)

        self.category = "/app/phpfpm"

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

        # Load config
        # url0 = pool_name|uri
        # ...
        # urlN = pool_name|uri
        if self._d_pool_from_url:
            logger.info("Skip loading _d_pool_from_url from config (already set), _d_pool_from_url=%s", self._d_pool_from_url)
            return

        # Load
        try:
            # Allocate
            self._d_pool_from_url = dict()
            idx = 0
            while True:
                key = "url" + str(idx)

                # Check
                if key not in d:
                    logger.info("All url loaded")
                    break

                # Get it
                buf = d[key]
                ar = buf.split("|")
                k = ar[0]
                v = ar[1:]

                # Hash
                self._d_pool_from_url[k] = v
                logger.info("Hashed, k=%s, v=%s", k, v)

                # Increment
                idx += 1

            # Ok
            logger.info("Config loaded, _d_pool_from_url=%s", self._d_pool_from_url)
        except Exception as e:
            logger.warning("Exception while loading config, ex=%s", SolBase.extostr(e))

    def _execute_linux(self):
        """
        Exec
        """

        # Reset
        self._d_all = dict()

        # Check
        located_f = None
        for cur_f in PhpFpmStat.AR_FPM_CONFIG_FILE:
            if FileUtility.is_file_exist(cur_f):
                located_f = cur_f
                break

        # Check
        if not located_f:
            logger.info("Give up (no file found in %s)", PhpFpmStat.AR_FPM_CONFIG_FILE)
            return

        # Ok
        logger.info("Phpfpm detected (%s found)", located_f)

        # -------------------------------
        # Browse /etc/php5/fpm/pool.d/* and process them (verify status_path)
        # -------------------------------

        d_pool_from_files = dict()
        ar_files = glob.glob("/etc/php5/fpm/pool.d/*") + glob.glob("/etc/php-fpm.d/*")
        for cur_file in ar_files:
            # Go
            status_path, pool_id = self._process_file(cur_file)

            # Check
            if not status_path:
                continue

            # Check
            if pool_id in d_pool_from_files:
                logger.warning("Already hashed pool, pool_id=%s, d_pool_from_files=%s", pool_id, d_pool_from_files)

            # Hash
            d_pool_from_files[pool_id] = status_path, cur_file

        # Check
        if len(d_pool_from_files) == 0:
            logger.info("Give up (no status_path in pools)")

        # -------------------------------
        # Ok, here :
        # d_pool_from_files : detected pools (using files) : pool_id => status_path, cur_file
        # _d_pool_from_url  : config pools  : pool_id => list of uris
        # We MUST have the same element count
        # -------------------------------

        if len(d_pool_from_files) != len(self._d_pool_from_url):
            logger.warning("Possible pool mismatch, d_pool_from_files=%s, _d_pool_from_url=%s", d_pool_from_files, self._d_pool_from_url)
        else:
            logger.info("Pool seems ok, d_pool_from_files=%s, _d_pool_from_url=%s", d_pool_from_files, self._d_pool_from_url)

        # NOTE : In call cases, we process the config pool (we NEED the uris, this basterd fpm has no stats socket or similar)

        # -------------------------------
        # Execute stuff now
        # -------------------------------

        # ALL : always started
        self.notify_value_n("k.phpfpm.started", {"ID": "ALL"}, 1)

        # GO
        logger.info("Processing pools (from d_pool_from_files)")
        for pool_id, (status_path, pool_file) in d_pool_from_files.items():
            logger.info("Processing, pool_id=%s, status_path=%s, pool_file=%s", pool_id, status_path, pool_file)

            # Try to locate uri
            if pool_id not in self._d_pool_from_url:
                logger.warning("Cannot locate uri, notify started=0 and skip, pool_id=%s, _d_pool_from_url=%s", pool_id, self._d_pool_from_url)
                self.notify_value_n("k.phpfpm.started", {"ID": pool_id}, 0)
                continue

            # Try each uris
            pool_ok = False
            for cur_uri in self._d_pool_from_url[pool_id]:
                logger.info("Trying cur_uri=%s", cur_uri)
                if self._process_pool(pool_id, cur_uri):
                    # Ok
                    logger.info("Uri ok, notify started=1 and return, pool_id=%s", pool_id)
                    self.notify_value_n("k.phpfpm.started", {"ID": pool_id}, 1)

                    # Set as ok
                    pool_ok = True
                    break

            # Here, we are NOT OK for this pool
            if not pool_ok:
                logger.warning("All Uri down, notify started=0 and return, pool_id=%s", pool_id)
                self.notify_value_n("k.phpfpm.started", {"ID": pool_id}, 0)

            # Next pool
            pass

        # All pool ok, push ALL
        self._push_all()

    # noinspection PyMethodMayBeStatic
    def _process_file(self, cur_file):
        """
        Process a file
        :param cur_file: str
        :type cur_file str
        :return tuple (status path, pool id)
        :rtype tuple
        """

        # TODO OOPS didn"t see the find_status method :(
        try:
            logger.info("Processing now, cur_file=%s", cur_file)

            # Check
            if not FileUtility.is_file_exist(cur_file):
                logger.warning("Give up (file not found), cur_file=%s", cur_file)
                return None, None

            # Load buffer
            buf = FileUtility.file_to_textbuffer(cur_file, "utf8")
            if not buf:
                logger.warning("Give up (no buffer), cur_file=%s", cur_file)
                return None, None

            # Parse
            ar_buf = buf.split("\n")
            cur_status_path = None
            cur_id = None
            for a in ar_buf:
                a = a.strip()
                if len(a) == 0:
                    continue
                elif a.startswith(";") or a.startswith("#"):
                    continue

                if a.startswith("[") and a.endswith("]"):
                    logger.info("Detected pool_id=%s", a)
                    cur_id = a.replace("[", "").replace("]", "")
                elif a.startswith("pm.status_path"):
                    # Got a status path, good
                    logger.info("Detected status_path=%s", a)

                    # Extract
                    temp_ar = a.split("=", 1)
                    if len(temp_ar) != 2:
                        logger.warning("Split issues, temp_ar=%s", temp_ar)
                        continue

                    temp_ar[1] = temp_ar[1].strip()
                    if len(temp_ar[1]) == 0:
                        logger.warning("Config issue, not value, temp_ar=%s", temp_ar)
                        continue

                    # Ok
                    cur_status_path = temp_ar[1].strip()
                    logger.info("Got cur_status_path=%s", cur_status_path)

            # Check
            if not cur_status_path:
                logger.warning("Give up (no status_path), cur_file=%s", cur_file)
                return None, None

            # Ok
            return cur_status_path, cur_id
        except Exception as e:
            logger.warning("Give up (exception), cur_file=%s, ex=%s", cur_file, SolBase.extostr(e))
            return None, None

    def _process_pool(self, pool_id, pool_uri):
        """
        Process a pool
        :param pool_id: str
        :type pool_id: str
        :param pool_uri: str
        :type pool_uri: str
        :return bool
        :rtype bool
        """

        try:
            logger.info("Processing pool, pool_id=%s, pool_uri=%s", pool_id, pool_uri)
            ms_http_start = SolBase.mscurrent()
            d_json = self.fetch_url_as_json(pool_uri)
            ms_http = SolBase.msdiff(ms_http_start)

            # Check
            if not d_json:
                # Notify KO
                logger.info("No valid reply, return False")
                return False

            # Ok
            logger.info("Valid reply")

            # Add http millis
            d_json["k.phpfpm.status.ms"] = ms_http

            # Browse our KEYS
            for k, knock_type, knock_key in PhpFpmStat.KEYS:
                # Try
                if k not in d_json:
                    if k.find("k.phpfpm.") != 0:
                        logger.warning("Unable to locate k=%s in d_out", k)
                    continue

                # Ok, fetch and cast
                v = d_json[k]
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

                # Handle ALL
                self._handle_all(knock_key, v)

                # Notify
                self.notify_value_n(knock_key + "", {"ID": pool_id}, v)

            # Success
            return True
        except Exception as e:
            logger.info("Exception, ex=%s", SolBase.extostr(e))
            return False

    def _push_all(self):
        """
        Push all
        """

        for k, v in self._d_all.items():
            self.notify_value_n(k, {"ID": "ALL"}, v)

    def _handle_all(self, knock_key, v):
        """
        Handle all
        :param knock_key: str
        :type knock_key: str
        :param v: int,float
        :type v: int,float
        """

        # Miss
        if knock_key not in self._d_all:
            self._d_all[knock_key] = v
            return

        # Hit : SUM
        if knock_key in [
            "k.phpfpm.listen_queue",
            "k.phpfpm.active_processes",
            "k.phpfpm.idle_processes",
            "k.phpfpm.accepted_conn",
        ]:
            self._d_all[knock_key] += v
            return

        # Hit : MIN
        if knock_key in [
            "k.phpfpm.start_since",
        ]:
            self._d_all[knock_key] = min(self._d_all[knock_key], v)
            return

        # Hit : MAX
        if knock_key in [
            "k.phpfpm.listen_queue_limit",
        ]:
            self._d_all[knock_key] = max(self._d_all[knock_key], v)
            return

        # Failed
        logger.warning("Not managed knock_key=%s for ALL instance", knock_key)

    # noinspection PyMethodMayBeStatic
    def fetch_url_as_json(self, url_status):
        """
        Get Status
        sample :{
            "pool":"www",
            "process manager":"dynamic",
            "start time":1415829290,
            "start since":2615,
            "accepted conn":271839,
            "listen queue":0,
            "max listen queue":0,
            "listen queue len":0,
            "idle processes":2,
            "active processes":1,
            "total processes":3,
            "max active processes":5,
            "max children reached":6,
            "slow requests":0
            }
        :param url_status: str
        :type url_status: str
        :return: dict,None
        :rtype: dict,None
        """

        try:
            # Fix status url (we need ?json)
            if url_status.find("?json") < 0:
                url_status += "?json"

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
            if hresp.status_code == 200:
                # Get buffer
                pd = hresp.buffer

                # Check
                if not pd:
                    logger.warning("No buffer, give up")
                    return None

                # Json
                try:
                    d_json = ujson.loads(pd)
                    logger.info("Got d_json=%s", d_json)
                    return d_json
                except Exception as e:
                    logger.warning("json loads exception, give up, ex=%s", SolBase.extostr(e))
                    return None

            # Failed
            logger.warning("No http 200, give up")
            return None

        except Exception as e:
            logger.warning("Exception, ex=%s", SolBase.extostr(e))
            return None

    @staticmethod
    def find_status():
        """
        Find all status url
        :return: List of status url
        :rtype: list(dict())
        """
        reg_obj_status = re.compile(r"^pm.status_path\s*=\s*(.*)$")
        # noinspection RegExpRedundantEscape
        reg_obj_pool = re.compile(r"^\[(.*)\].*$")
        res = []
        for filename in glob.glob("/etc/php5/fpm/**/*.conf"):
            pool = None
            url = None
            for line in open(filename, "r"):
                search_obj_status = reg_obj_status.search(line)
                if search_obj_status:
                    url = search_obj_status.group(1)

                search_obj_pool = reg_obj_pool.search(line)
                if search_obj_pool:
                    pool = search_obj_pool.group(1)
            if url is not None:
                res.append((pool, "http://127.0.0.1/" + url))
        return res
