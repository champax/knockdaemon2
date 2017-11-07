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
from pymemcache.client.base import Client
from pythonsol.FileUtility import FileUtility
from pythonsol.SolBase import SolBase
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class MemCachedStat(KnockProbe):
    """
    Probe
    DOC : https://github.com/memcached/memcached/blob/master/doc/protocol.txt
    Handle single instance only, no aggregation
    """

    KEYS = [
        # INTERNAL
        ("k.memcached.started", "int", "k.memcached.started", "custom"),

        # STATS COMMAND Millis
        ("k.memcached.stat.ms", "float", "k.memcached.stat.ms", "max"),

        # Uptime (current, in sec) / Number of secs since the server started
        ("uptime", "int", "k.memcached.uptime", "min"),

        # Accepting (1 == ok)
        ("accepting_conns", "int", "k.memcached.accepting_conns", "sum"),

        # Current connections (as it) / Number of open connections
        ("curr_connections", "int", "k.memcached.curr_connections", "sum"),

        # Connection (per sec) / Total number of connections since start
        ("total_connections", "float", "k.memcached.total_connections", "sum"),

        # Refused conn (per sec) / Number of times server has stopped accepting (maxconns)
        ("listen_disabled_num", "float", "k.memcached.listen_disabled_num", "sum"),

        # Command (per sec) /  Cumulative number of retrieval, storage, flush, touch reqs
        ("cmd_get", "float", "k.memcached.cmd_get", "sum"),
        ("cmd_set", "float", "k.memcached.cmd_set", "sum"),
        ("cmd_flush", "float", "k.memcached.cmd_flush", "sum"),
        ("cmd_touch", "float", "k.memcached.cmd_touch", "sum"),

        # Hit ratio (per sec)
        ("get_hits", "float", "k.memcached.get_hits", "sum"),
        ("get_misses", "float", "k.memcached.get_misses", "sum"),

        ("delete_hits", "float", "k.memcached.delete_hits", "sum"),
        ("delete_misses", "float", "k.memcached.delete_misses", "sum"),

        ("incr_hits", "float", "k.memcached.incr_hits", "sum"),
        ("incr_misses", "float", "k.memcached.incr_misses", "sum"),

        ("cas_hits", "float", "k.memcached.cas_hits", "sum"),
        ("cas_misses", "float", "k.memcached.cas_misses", "sum"),
        ("cas_badval", "float", "k.memcached.cas_badval", "sum"),  # Key found but CAS value mismatch

        ("touch_hits", "float", "k.memcached.touch_hits", "sum"),
        ("touch_misses", "float", "k.memcached.touch_misses", "sum"),

        # Auth (if enabled) (per sec) (cumulative)
        ("auth_cmds", "float", "k.memcached.auth_cmds", "sum"),
        ("auth_errors", "float", "k.memcached.auth_errors", "sum"),

        # Bytes (per sec) (cumulative)
        ("bytes_read", "float", "k.memcached.bytes_read", "sum"),
        ("bytes_written", "float", "k.memcached.bytes_written", "sum"),

        # Cpu time (in sec) (delta per sec) (seconds:microseconds)
        ("rusage_user", "float", "k.memcached.rusage_user", "sum"),
        ("rusage_system", "float", "k.memcached.rusage_system", "sum"),

        # New item (per sec) (cumulative)
        ("total_items", "float", "k.memcached.total_items", "sum"),

        # Current item (as it) (current)
        ("curr_items", "int", "k.memcached.curr_items", "sum"),

        # Current threads (as it)
        ("threads", "int", "k.memcached.threads", "sum"),

        # Eviction (mem full, LRU not used)
        ("evictions", "float", "k.memcached.evictions", "sum"),

        # Reclaimed slot (reuse a previous deleted slot, LRU hit)
        ("reclaimed", "float", "k.memcached.reclaimed", "sum"),

        # Evicted (mem full) (never read) (per sec)
        ("evicted_unfetched", "float", "k.memcached.evicted_unfetched", "sum"),

        # Expired (never read) (per sec)
        ("expired_unfetched", "float", "k.memcached.expired_unfetched", "sum"),

        # LRU reclaimed by crawler
        # ("crawler_reclaimed", "float", "k.memcached.crawler_reclaimed", "sum"),

        # Mem (cur, available computed as limit_maxbytes - bytes)
        ("bytes", "int", "k.memcached.bytes", "sum"),
        ("bytes_av", "int", "k.memcached.bytes_av", "sum"),
    ]

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self.category = "/nosql/memcached"

    # noinspection PyMethodMayBeStatic
    def _detect_memcached(self):
        """
        Detect memcached
        :return tuple (tcp|unix, port|unix_socket_name, None|None)
        :rtype tuple
        """

        # Look for /etc/memcached.conf

        # Look for -p 11211
        # Look for -s unix_socket
        found = False
        conf_file = None
        conf_files = ['/etc/sysconfig/memcached', '/etc/memcached.conf']
        for conf_file in conf_files:

            if FileUtility.is_file_exist(conf_file):
                found = True
                break

        if not found or conf_file is None:
            logger.info("No %s, giveup", conf_files)
            return None, None

        # Browse file
        buf = FileUtility.file_to_textbuffer(conf_file, "utf-8")

        # Go
        for line in buf.split("\n"):
            line = line.strip()
            if line.startswith('-p '):
                ar = line.split(" ")
                port = int(ar[1])
                logger.info("Detected tcp=%s", line)
                return "tcp", port

            if line.startswith('PORT='):
                ar = line.split('"')
                port = int(ar[1])
                logger.info("Detected tcp=%s", line)
                return "tcp", port

            elif line.startswith('-s '):
                ar = line.split(" ")
                unix_socket_name = str(ar[1])
                logger.info("Detected unix=%s, got=%s", line, unix_socket_name)
                return "unix", unix_socket_name

        # Nothing found
        logger.warn("Found %s but unable to locate -p or -s rows, giveup", conf_file)
        return None, None

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Execute
        """

        # ---------------------------
        # DETECT CONFIGS
        # ---------------------------
        cur_type, connect_to = self._detect_memcached()
        if not cur_type:
            return

        # Single (default) instance notify
        logger.info("Memcache detected, cur_type=%s, connect_to=%s", cur_type, connect_to)
        self.notify_discovery_n("k.memcached.discovery", {"MC": str(connect_to)})

        # Push ALL
        self.notify_discovery_n("k.memcached.discovery", {"MC": "ALL"})

        # -------
        # CONNECT
        # -------

        # Stats command knows very few key, send it raw
        client = None
        try:
            # OK Got it, connect socket, send stats command and parse result
            ms_stat_start = SolBase.mscurrent()
            if cur_type == "tcp":
                client = Client(('127.0.0.1', connect_to))
            elif cur_type == "unix":
                # TODO : pymemcache do not support unix domain socket
                client = Client((str(connect_to)))
                raise Exception("Unable to handle unix socket at this stage (pymemcache support lacks), contact us")
            else:
                raise Exception("Invalid type={0}".format(cur_type))

            # Need str later on
            connect_to = str(connect_to)

            # noinspection PyProtectedMember
            d_info = client._fetch_cmd(b'stats', [], False)
            ms_stat = SolBase.msdiff(ms_stat_start)

            # Add millis
            d_info["k.memcached.stat.ms"] = ms_stat

            # Notify up
            logger.info("Memcached stats ok, notifying started=1, d_info=%s", d_info)
            self._push_result("k.memcached.started", connect_to, 1, False)

        except Exception as e:
            # Close
            if client:
                client.close()

            # Notify down
            logger.warn("Exception, connect_to=%s, notifying started=0, ex=%s", connect_to, SolBase.extostr(e))
            self._push_result("k.memcached.started", connect_to, 0, False)
            return

        # -------
        # PROCESS INFO
        # -------

        # b) Browse our KEYS
        for k, knock_type, knock_key, aggreg_op in MemCachedStat.KEYS:
            logger.debug("Processing, k=%s, knock_key=%s", k, knock_key)

            # Try
            if k not in d_info:
                if k == "bytes_av":
                    # Compute bytes available
                    b_used = int(d_info["bytes"])
                    b_max = int(d_info["limit_maxbytes"])
                    v = b_max - b_used
                elif k.find("k.memcached.") == 0:
                    # Expected
                    continue
                else:
                    logger.warn("Unable to locate k=%s in d_info", k)
                    continue
            else:
                # Ok, fetch
                v = d_info[k]

            # Cast
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
                logger.warn("Not managed type=%s", knock_type)
                continue

            # Notify
            self._push_result(knock_key, connect_to, v, False)

        # Over
        logger.info("memcached done")

    # noinspection PyUnusedLocal
    def _push_result(self, key, connect_to, value, aggreg_op):
        """
        Agregate all key and send local key
        :param key; key
        ;param connect_to: connect_to
        :param value: value
        :param aggreg_op: str
        """

        self.notify_value_n(key, {"MC": str(connect_to)}, value)

        # Need to push ALL (even if we handle a single instance currently)
        self.notify_value_n(key, {"MC": "ALL"}, value)
