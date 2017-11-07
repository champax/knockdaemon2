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

import glob
import logging

import re
import redis
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class RedisStat(KnockProbe):
    """
    Probe
    """

    KEYS = [
        # INTERNAL
        ("k.redis.started", "int", "k.redis.started", "custom"),

        # INFO COMMAND MILLIS
        ("k.redis.info.ms", "float", "k.redis.info.ms", "max"),

        # Uptime (current)
        ("uptime_in_seconds", "int", "k.redis.uptime_in_seconds", "min"),

        # Clients (current)
        ("connected_clients", "int", "k.redis.connected_clients", "sum"),

        # Memory (current)
        ("used_memory_rss", "int", "k.redis.used_memory_rss", "max"),
        ("mem_fragmentation_ratio", "float", "k.redis.mem_fragmentation_ratio", "max"),

        # Persistence (current)
        ("rdb_last_bgsave_time_sec", "int", "k.redis.rdb_last_bgsave_time_sec", "max"),
        ("aof_last_rewrite_time_sec", "int", "k.redis.aof_last_rewrite_time_sec", "max"),

        ("rdb_last_bgsave_status", "str", "k.redis.rdb_last_bgsave_status", "custom"),
        ("aof_last_bgrewrite_status", "str", "k.redis.aof_last_bgrewrite_status", "custom"),
        ("aof_last_write_status", "str", "k.redis.aof_last_write_status", "custom"),

        # Stats (per sec)
        ("total_connections_received", "float", "k.redis.total_connections_received", "sum"),
        ("total_commands_processed", "float", "k.redis.total_commands_processed", "sum"),
        ("expired_keys", "float", "k.redis.expired_keys", "sum"),
        ("evicted_keys", "float", "k.redis.evicted_keys", "sum"),
        ("keyspace_hits", "float", "k.redis.keyspace_hits", "sum"),
        ("keyspace_misses", "float", "k.redis.keyspace_misses", "sum"),

        # Pubsub (current)
        ("pubsub_channels", "int", "k.redis.pubsub_channels", "sum"),
        ("pubsub_patterns", "int", "k.redis.pubsub_patterns", "sum"),

        # Optional (if not present, link to master is up) (current)
        ("master_link_down_since_seconds", "int", "k.redis.master_link_down_since_seconds", "max"),

        # Keyspace : special processing (current)
        ("k.redis.db.key_count_with_ttl", "int", "k.redis.db.key_count_with_ttl", "sum"),
        ("k.redis.db.key_count", "int", "k.redis.db.key_count", "sum"),
    ]

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self._d_aggregate = None
        self.category = "/nosql/redis"

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
        # RESET
        # ---------------------------

        self._d_aggregate = dict()

        # ---------------------------
        # DETECT CONFIGS
        # ---------------------------

        # Caution : sentinel add a port
        # CF :
        # root@klchgui01:~# grep port /etc/redis/* | grep -v "#"
        # /etc/redis/redis.conf:port 6379
        # /etc/redis/sentinel.conf:port 26379

        redis_ports = list()
        conf_files = glob.glob("/etc/redis/*.conf") + glob.glob("/etc/redis.conf")
        for conf in conf_files:
            # Read
            buf = FileUtility.file_to_textbuffer(conf, "utf-8")

            # Sentinel bypass # TODO : regex detection of "sentinel monitor"
            if "sentinel monitor" in buf:
                continue

            # Go
            for line in buf.split("\n"):
                line = line.strip()
                if line.startswith("port "):
                    line2 = re.sub(" +", " ", line)
                    port = line2[5:].strip()
                    redis_ports.append(port)

                    logger.info("Redis, got instance port=%s, line=%s, line2=%s", port, line, line2)

                    # Detected instance, notify disco asap
                    self.notify_discovery_n("k.redis.discovery", {"RDPORT": port})
                    break

        # If no instance, give up
        if len(redis_ports) == 0:
            logger.info("No redis instance detected, give up")
            return

        # ALL instance
        self.notify_discovery_n("k.redis.discovery", {"RDPORT": "ALL"})

        # ---------------------------
        # PROCESS INSTANCES
        # ---------------------------
        for port in redis_ports:

            # -------
            # FETCH INFO
            # -------
            # TODO : Redis info : handle info with timeout ?

            try:
                # Connect
                ms_info_start = SolBase.mscurrent()
                logger.info("Redis now, port=%s", port)
                r = redis.Redis("localhost", int(port))

                # Query info
                logger.info("Redis info now, r=%s", r)
                d_info = r.info()
                ms_info = SolBase.msdiff(ms_info_start)

                # Add ms
                d_info["k.redis.info.ms"] = ms_info

                # Notify up
                logger.info("Redis info ok, notifying started=1, d_info=%s", d_info)
                self.notify_value_n("k.redis.started", {"RDPORT": port}, 1)
            except Exception as e:
                logger.warn("Exception, port=%s, notifying started=0, ex=%s", port, SolBase.extostr(e))
                self.notify_value_n("k.redis.started", {"RDPORT": port}, 0)
                continue

            # AGGREG : Started
            self.notify_value_n("k.redis.started", {"RDPORT": "ALL"}, 1)

            # -------
            # PROCESS INFO
            # -------

            # 0) fix d_info
            if "master_link_down_since_seconds" not in d_info:
                d_info["master_link_down_since_seconds"] = 0

            # a) dbX special processing : (keys, expires, avg_ttl)
            key_count = 0
            key_count_with_ttl = 0
            for k, v in d_info.iteritems():
                if k.find("db") != 0:
                    continue

                # Got
                # k => dbX
                # v => keys=3,expires=3,avg_ttl=7193838
                key_count += v["keys"]
                key_count_with_ttl += v["expires"]

            # b) Browse our KEYS
            for k, knock_type, knock_key, aggreg_op in RedisStat.KEYS:
                logger.debug("Processing, k=%s, knock_key=%s", k, knock_key)

                # Try
                if k not in d_info:
                    if k == "k.redis.db.key_count_with_ttl":
                        # Special "db" processing
                        v = key_count_with_ttl
                    elif k == "k.redis.db.key_count":
                        # Special "db" processing
                        v = key_count
                    elif k.find("k.redis.") == 0:
                        # Expected
                        continue
                    else:
                        logger.warn("Unable to locate k=%s in d_out", k)
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
                self._push_result(knock_key, port, v, aggreg_op)

        # Push aggregate results
        for key, value in self._d_aggregate.iteritems():
            self.notify_value_n(key, {"RDPORT": "ALL"}, value)

        # Over
        logger.info("redis done")

    def _push_result(self, key, redis_port, value, aggreg_op):
        """
        Agregate all key and send local key
        :param key; key
        ;param redis_port: redis_port
        :param value: value
        :param aggreg_op: str
        """

        self.notify_value_n(key, {"RDPORT": redis_port}, value)

        if aggreg_op == "min":
            if key not in self._d_aggregate:
                self._d_aggregate[key] = value
            else:
                self._d_aggregate[key] = min(value, self._d_aggregate[key])
            return
        elif aggreg_op == "max":
            if key not in self._d_aggregate:
                self._d_aggregate[key] = value
            else:
                self._d_aggregate[key] = max(value, self._d_aggregate[key])
            return
        elif aggreg_op == "sum":
            if key not in self._d_aggregate:
                self._d_aggregate[key] = value
            else:
                self._d_aggregate[key] += value
            return
        elif aggreg_op == "custom":
            # Custom stuff
            if key in [
                "k.redis.rdb_last_bgsave_status",
                "k.redis.aof_last_bgrewrite_status",
                "k.redis.aof_last_write_status",
            ]:
                if key not in self._d_aggregate:
                    self._d_aggregate[key] = value
                elif value != "ok":
                    # Not ok win
                    self._d_aggregate[key] = value
                return

        # Here, unknown op or not custom managed
        raise Exception("Un-managed push, key={0}, aggreg_op={1}".format(key, aggreg_op))
