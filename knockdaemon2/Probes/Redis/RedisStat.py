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
        ("master_last_io_seconds_ago", "int", "k.redis.master_last_io_seconds_ago", "max"),

        # Keyspace : special processing (current)
        ("k.redis.db.key_count_with_ttl", "int", "k.redis.db.key_count_with_ttl", "sum"),
        ("k.redis.db.key_count", "int", "k.redis.db.key_count", "sum"),
    ]

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self._d_aggregate = dict()
        self.category = "/nosql/redis"

    def _execute_linux(self):
        """
        Execute
        """

        self._execute_native()

    @classmethod
    def try_get_redis_port(cls, buf):
        """
        Try get redis port from config
        :param buf: config buffer
        :type buf: str
        :return: int,None
        :rtype int,None
        """

        # Go
        for line in buf.split("\n"):
            line = line.strip()
            if line.startswith("port "):
                line2 = re.sub(" +", " ", line)
                port = line2[5:].strip()
                port = int(port)
                return port
        return None

    @classmethod
    def fetch_redis_info(cls, port):
        """
        Fetch redis into
        :param port: int
        :type port: int
        :return dict,None
        :rtype dict,None
        """

        r = redis.Redis("localhost", int(port))
        d_info = r.info()
        return d_info

    def process_redis_dict(self, d_info, port, ms_info):
        """
        Process redis dict
        :param d_info: dict
        :type d_info: dict
        :param port: int
        :type port: int
        :param ms_info: float
        :type ms_info: float
        :return: dict
        :rtype dict
        """

        # Add ms
        d_info["k.redis.info.ms"] = ms_info

        # 0) fix d_info
        if "master_link_down_since_seconds" not in d_info:
            d_info["master_link_down_since_seconds"] = 0
        if "master_last_io_seconds_ago" not in d_info:
            d_info["master_last_io_seconds_ago"] = 0

        # a) dbX special processing : (keys, expires, avg_ttl)
        key_count = 0
        key_count_with_ttl = 0
        for k, v in d_info.items():
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
                    logger.warning("Unable to locate k=%s in d_out", k)
                    continue
            else:
                # Ok, fetch
                v = d_info[k]

            # Discard invalid values  (mem_fragmentation_ratio can be nan on restart)
            if v is None:
                continue
            elif isinstance(v, str) and (len(v) == 0 or v.lower() == "nan"):
                continue

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
                logger.warning("Not managed type=%s", knock_type)
                continue

            # Notify
            self._push_result(knock_key, port, v, aggreg_op)

        # Notify up
        logger.debug("Redis info ok, notifying started=1, d_info=%s", d_info)
        self.notify_value_n("k.redis.started", {"RDPORT": str(port)}, 1)
        self.notify_value_n("k.redis.started", {"RDPORT": "ALL"}, 1)

    def process_redis_aggregate(self):
        """
        Process aggregate
        """
        # Push aggregate results
        for key, value in self._d_aggregate.items():
            self.notify_value_n(key, {"RDPORT": "ALL"}, value)

    def _notify_down(self, port):
        """
        Notify down
        :param port: int
        :type port: int
        """

        self.notify_value_n("k.redis.started", {"RDPORT": port}, 0)

    def _execute_native(self):
        """
        Exec, native
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

        # Scan configs
        redis_ports = list()
        conf_files = glob.glob("/etc/redis/*.conf") + glob.glob("/etc/redis.conf")
        for conf in conf_files:
            # Read
            buf = FileUtility.file_to_textbuffer(conf, "utf8")
            if buf is None:
                continue
            elif "sentinel monitor" in buf:
                # Sentinel bypass # TODO : regex detection of "sentinel monitor"
                continue

            # Go
            port = self.try_get_redis_port(buf)
            redis_ports.append(port)

        # If no instance, give up
        if len(redis_ports) == 0:
            logger.debug("No redis instance detected, give up")
            return

        # ---------------------------
        # PROCESS INSTANCES
        # ---------------------------
        for port in redis_ports:

            # -------
            # FETCH INFO
            # -------
            # TODO : Redis info : handle info with timeout ?

            try:
                # Fetch info
                ms = SolBase.mscurrent()
                d_info = self.fetch_redis_info(port)

                # Process it
                if self.process_redis_dict(d_info, port, SolBase.msdiff(ms)):
                    return

            except Exception as e:
                logger.warning("Exception, port=%s, notifying started=0, ex=%s", port, SolBase.extostr(e))
                self._notify_down(port)
                continue

        # Push aggregate
        self.process_redis_aggregate()

    def _push_result(self, key, redis_port, value, aggreg_op):
        """
        Agregate all key and send local key
        :param key; key
        :type key: str
        ;param redis_port: redis_port
        :type redis_port: int
        :param value: value
        :type: value: object
        :param aggreg_op: str
        :type aggreg_op: str
        """

        if value is None:
            return
        elif isinstance(value, str) and (len(value) == 0 or value.lower() == "nan"):
            return

        self.notify_value_n(key, {"RDPORT": str(redis_port)}, value)

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
