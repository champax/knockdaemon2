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

# Python 3.7 hinting patch, MUST BE AT HEAD
from __future__ import annotations

import logging
import os.path
import re
from typing import Optional



from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolmysql.Mysql.MysqlApi import MysqlApi

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Manticore(KnockProbe):
    """
    Probe
    """

    MANTICORE_CONF_DIR = "/etc/manticoresearch"

    # Debian : extract creds from file
    MANTICORE_CONFIG_FILES = [
        # Old ones
        ("V1", "/etc/manticoresearch/manticore.conf "),
    ]

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self.category = "/sql/manticore"

    @classmethod
    def _parse_config_debian_buffer(cls, buf: str) -> tuple[Optional[str], Optional[int]]:
        # Split
        logger.debug("Buffer loaded, parsing...")
        ar = buf.split("\n")
        for r in ar:
            r = r.strip()

            # Empty
            if len(r) == 0:
                continue
            r = r.strip()
            # Comment
            if r[0] == "\"" or r[0] == "#":
                continue

            # Look for "listen = 127.0.0.1:9306:mysql"
            if r.startswith("listen") and ":mysql" in r:
                ar = r.split("=")[1].split(":")
                host = ar[0].strip()
                port = int(ar[1].strip())
                logger.info("Got host=%s, port=%s", host, port)
                return host, port
        return None, None

    # noinspection PyMethodMayBeStatic
    def _parse_config_debian(self) -> tuple[Optional[str], Optional[int]]:
        """
        Parse config file
        :return: tuple (host,port) or None,None if failed
        :rtype tuple
        """

        for cur_version, cur_file in Manticore.MANTICORE_CONFIG_FILES:
            try:
                if cur_version == "V1":
                    # File is root access only, try to load
                    buf = None

                    if FileUtility.is_file_exist(cur_file):
                        buf = FileUtility.file_to_textbuffer(cur_file, "ascii")

                    # Check
                    if not buf:
                        # IOError 13 possible (file is root only) Retry invoke, invoke sudo (unittest mainly)
                        logger.debug("Load failed, retry invoke, fallback invoke now")
                        cmd = "cat {0}".format(cur_file)
                        ec, so, se = ButcherTools.invoke(cmd)
                        if ec != 0:
                            logger.debug("invoke failed, retry sudo, ec=%s, so=%s, se=%s", ec, so, se)
                            # Retry sudo
                            cmd = "sudo cat {0}".format(cur_file)
                            ec, so, se = ButcherTools.invoke(cmd)
                            if ec != 0:
                                logger.info("invoke failed (sudo fallback), give up, ec=%s, so=%s, se=%s", ec, so, se)
                                continue
                        # Ok
                        buf = so

                    # Split
                    return self._parse_config_debian_buffer(buf)
                else:
                    raise Exception("Invalid version=%s" % cur_version)
            except Exception as e:
                logger.warning("Parse failed, ex=%s", SolBase.extostr(e))

        # All parsing failed
        logger.warning("Unable to locate host,port")
        return None, None

    def _execute_linux(self):
        """
        Execute
        """
        self._execute_native()

    def _execute_native(self):
        """
        Exec, native
        """

        # Check
        if not os.path.exists(self.MANTICORE_CONF_DIR):
            return
        elif not os.path.isdir(self.MANTICORE_CONF_DIR):
            return

        try:
            # Fetch (MUST NOT FAIL)
            host, port = self._parse_config_debian()

            if host is None or port is None:
                logger.warning("Cannot process (host|port None, got=%s:%s), signaling instance down", host, port)
                self.notify_value_n("k.manticore.started", {"PORT": str(port)}, 0)
            else:
                self._execute_via_creds(host, int(port))
        except Exception as e:
            # Notify instance down (type : 0)
            logger.warning("Execute failed, signaling instance down, started=0, ex=%s", SolBase.extostr(e))
            self.notify_value_n("k.manticore.started", {}, 0)

    def _execute_via_creds(self, host: str, port: int):
        """
        Execute
        """

        # Check
        if not host or not port:
            # FATAL
            # Notify instance down (type : 0)
            logger.warning("Cannot execute (host|port None, got=%s:%s), signaling instance down", host, port)
            self.notify_value_n("k.manticore.started", {"PORT": str(port)}, 0)
            return

        # Config OK
        d_conf = {
            "hosts": [host],
            "port": port,
            "database": None,
            "user": "",
            "password": "",
            "autocommit": True,
            "pool_name": "p1",  # not used
            "pool_size": 5  # not used
        }

        # -----------------------------
        # MANTICORE FETCH
        # -----------------------------

        # Fetch variables
        ms = SolBase.mscurrent()

        logger.debug("Manticore connect/exec now")
        ar_show_status = MysqlApi.exec_n(d_conf, "SHOW STATUS")

        # Process
        self.process_manticore_buffers(
            ar_show_status,
            port,
            SolBase.msdiff(ms),
        )

    @classmethod
    def get_known_keys(cls, cluster_name: str) -> list:
        """
        Get known keys, cluster_name based
        """

        return [
            "uptime",
            "connections",
            "maxed_out",
            "command_.*",
            "insert_replace_stats_.*",
            "search_stats_ms.*",
            "update_stats_ms.*",
            "agent_.*",
            "queries",
            "dist_queries",
            "workers.*",
            "load",
            "load_primary",
            "load_secondary",
            "query_wall",
            "dist_.*",
            "avg_query_wall",
            "avg_dist_.*",
            "qcache_.*",

            "cluster_%s_status" % cluster_name,
            "cluster_%s_size" % cluster_name,
            "cluster_%s_node_state" % cluster_name,
            "cluster_%s_indexes_count" % cluster_name,
            "cluster_%s_last_applied" % cluster_name,
            "cluster_%s_last_committed" % cluster_name,
            "cluster_%s_replicated" % cluster_name,
            "cluster_%s_replicated_bytes" % cluster_name,
            "cluster_%s_repl_keys" % cluster_name,
            "cluster_%s_repl_keys_bytes" % cluster_name,
            "cluster_%s_repl_data_bytes" % cluster_name,
            "cluster_%s_repl_other_bytes" % cluster_name,

            "cluster_%s_received" % cluster_name,
            "cluster_%s_received_bytes" % cluster_name,
            "cluster_%s_local_commits" % cluster_name,
            "cluster_%s_local_cert_failures" % cluster_name,
            "cluster_%s_local_replays" % cluster_name,
            "cluster_%s_local_send_queue" % cluster_name,
            "cluster_%s_local_send_queue_max" % cluster_name,
            "cluster_%s_local_send_queue_min" % cluster_name,
            "cluster_%s_local_send_queue_avg" % cluster_name,

            "cluster_%s_local_recv_queue" % cluster_name,
            "cluster_%s_local_recv_queue_max" % cluster_name,
            "cluster_%s_local_recv_queue_min" % cluster_name,
            "cluster_%s_local_recv_queue_avg" % cluster_name,
            "cluster_%s_local_cached_downto" % cluster_name,
            "cluster_%s_flow_control_paused_ns" % cluster_name,
            "cluster_%s_flow_control_paused" % cluster_name,
            "cluster_%s_flow_control_sent" % cluster_name,
            "cluster_%s_flow_control_recv" % cluster_name,
            "cluster_%s_cert_deps_distance" % cluster_name,
            "cluster_%s_apply_oooe" % cluster_name,
            "cluster_%s_apply_oool" % cluster_name,
            "cluster_%s_apply_window" % cluster_name,
            "cluster_%s_commit_oooe" % cluster_name,
            "cluster_%s_commit_oool" % cluster_name,
            "cluster_%s_commit_window" % cluster_name,

            "cluster_%s_local_state" % cluster_name,
            "cluster_%s_cert_index_size" % cluster_name,
            "cluster_%s_cert_bucket_count" % cluster_name,
            "cluster_%s_gcache_pool_size" % cluster_name,
            "cluster_%s_causal_reads" % cluster_name,
            "cluster_%s_cert_interval" % cluster_name,
            "cluster_%s_open_transactions" % cluster_name,
            "cluster_%s_open_connections" % cluster_name,

            "cluster_%s_ist_receive_seqno_start" % cluster_name,
            "cluster_%s_ist_receive_seqno_current" % cluster_name,
            "cluster_%s_ist_receive_seqno_end" % cluster_name,
            "cluster_%s_cluster_weight" % cluster_name,
            "cluster_%s_desync_count" % cluster_name,
            "cluster_%s_open_connections" % cluster_name,

            "cluster_%s_sst_total" % cluster_name,
            "cluster_%s_sst_stage" % cluster_name,
            "cluster_%s_sst_stage_total" % cluster_name,
            "cluster_%s_sst_table" % cluster_name,
            "cluster_%s_sst_tables" % cluster_name,
        ]

    def process_manticore_buffers(
            self,
            ar_show_status: list,  # list of dict (Counter, Value)
            port: int,
            ms_manticore: float):
        """
        Process manticore buffers
        """

        # Allocate output dict
        d_out = dict()

        # Port must be str
        port = str(port)

        # Notify exec time
        self.notify_value_n("k.manticore.exec.ss.ms", {"PORT": port}, ms_manticore)

        # -----------------------------
        # SHOW STATUS
        # -----------------------------

        # Index the list
        d_show_status = dict()
        for d in ar_show_status:
            d_show_status[d["Counter"]] = d["Value"]

        # -----------------------------
        # Get the cluster name (mandatory)
        # -----------------------------
        cluster_name = d_show_status.get("cluster_name", None)
        if cluster_name is None or len(cluster_name) == 0:
            # Cannot process, not cluster
            logger.warning("Cannot process, no cluster_name, got=%s", cluster_name)
        else:
            for known_key in self.get_known_keys(cluster_name):
                # May have regex....
                ar_known_keys = list()
                if ".*" in known_key:
                    # Regex
                    for k in d_show_status.keys():
                        if re.match(known_key, k):
                            ar_known_keys.append(k)
                else:
                    # Direct
                    ar_known_keys.append(known_key)

                # Check
                if len(ar_known_keys) == 0:
                    continue

                # GO
                for current_key in ar_known_keys:
                    # Get
                    if current_key not in d_show_status:
                        logger.debug("Key not found (bypass), known_key=%s", known_key)
                        continue
                    v = d_show_status[current_key]

                    # ----------------
                    # Special, str
                    if current_key in [
                        "cluster_%s_status" % cluster_name,
                        "cluster_%s_node_state" % cluster_name,
                        "cluster_%s_indexes" % cluster_name,

                    ]:
                        # We remove the cluster_name from the known key (easier for graphing stuff)
                        pushed_current_key = current_key.replace("_%s_" % cluster_name, "_")
                        # Push
                        d_out["k.manticore." + pushed_current_key] = v
                    # ----------------
                    # Special
                    # insert_replace_stats_ms
                    # search_stats_ms_
                    # update_stats_ms_
                    # load
                    # load_primary
                    # load_secondary
                    elif "_stats_ms" in current_key or current_key in ["load", "load_primary", "load_secondary"]:
                        # N/A N/A N/A
                        # 1.0 1.0 1.0
                        # 1 1 1
                        # => last 1, 5, and 15 minutes
                        v = v.replace("N/A", "0").strip()
                        ar_v = v.split(" ")
                        # We remove the cluster_name from the known key (easier for graphing stuff)
                        pushed_current_key = current_key.replace("_%s_" % cluster_name, "_")
                        # Push
                        d_out["k.manticore." + pushed_current_key + "_last_1_min"] = float(ar_v[0])
                        d_out["k.manticore." + pushed_current_key + "_last_5_min"] = float(ar_v[1])
                        d_out["k.manticore." + pushed_current_key + "_last_15_min"] = float(ar_v[2])
                    else:
                        # ----------------
                        # Default, cast to float
                        try:
                            if v == "-":
                                v = 0.0
                            else:
                                v = float(v)
                        except ValueError as e:
                            logger.debug("Value invalid (bypass), known_key=%s, v=%s, ex=%s", known_key, v, SolBase.extostr(e))
                            continue
                        # We remove the cluster_name from the known key (easier for graphing stuff)
                        pushed_current_key = current_key.replace("_%s_" % cluster_name, "_")
                        # Push
                        d_out["k.manticore." + pushed_current_key] = v

        # -----------------------------
        # Debug and PUSH
        # -----------------------------
        for k, v in d_out.items():
            logger.debug("Final, k=%s, v=%s, vtype=%s", k, v, type(v))

        for k, v in d_out.items():
            # Push it
            self.notify_value_n(k, {"PORT": port}, v)

        # -----------------------------
        # Over, instance up
        # -----------------------------
        logger.debug("Execute ok, signaling instance up, started=1")
        self.notify_value_n("k.manticore.started", {"PORT": port}, 1)
