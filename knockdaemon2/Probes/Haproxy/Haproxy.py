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
import socket

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysoltcp.tcpbase.TcpSocketManager import TcpSocketManager

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Haproxy(KnockProbe):
    """
    Probe
    DOC : https://cbonte.github.io/haproxy-dconv/1.6/management.html#9.1
    """

    def __init__(self):
        """
        Constructor
        """

        KnockProbe.__init__(self)
        self.category = "/web/haproxy"

    @classmethod
    def parse_buffer(cls, buf):
        """
        Parse haproxy buffer and return a list of dict.
        :param buf: str
        :type buf: str
        :return list of dict
        :rtype list
        """

        assert buf, "Need buf"
        assert len(buf) > 0, "Need buf not empty"

        ar_out = list()
        ar_buf = buf.split("\n")
        ar_fields = None
        for cur_line in ar_buf:
            logger.info("Parsing, cur_line=%s", cur_line)
            # Clean
            cur_line = cur_line.strip()
            if len(cur_line) == 0:
                continue

            # Header
            if cur_line.startswith("#"):
                assert ar_fields is None, "cur_line startswith #, need ar_fields None"
                cur_line = cur_line[1:]

            # Clean again
            cur_line = cur_line.strip()

            # Split
            ar_cur_line = cur_line.split(",")

            # Header
            if not ar_fields:
                # We assume first row is field list
                ar_fields = ar_cur_line
                logger.debug("Got ar_fields=%s", ar_fields)
                continue

            # Data
            cur_d = dict()
            idx = 0
            for cur_val in ar_cur_line:
                # Get name
                cur_field = ar_fields[idx]
                idx += 1

                # Try float
                # noinspection PyBroadException
                try:
                    cur_val = float(cur_val)
                except:
                    # If empty string, set 0.0
                    if len(cur_val) == 0:
                        cur_val = 0.0

                # Store
                cur_d[cur_field] = cur_val

            # Append
            logger.info("Got cur_d=%s", cur_d)
            ar_out.append(cur_d)

        # Over
        return ar_out

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

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Exec
        """

        try:
            if not FileUtility.is_file_exist('/etc/haproxy/haproxy.cfg'):
                logger.info("Give up (/etc/haproxy/haproxy.cfg not found)")
                return

            logger.info("Haproxy detected (/etc/haproxy/haproxy.cfg found)")

            # -------------------------------
            # Load config and locate stats socket /var/lib/haproxy/stats
            # -------------------------------

            c_buf = FileUtility.file_to_textbuffer("/etc/haproxy/haproxy.cfg", "utf-8")
            ar_buf = c_buf.split("\n")
            soc_name = None
            for cur_line in ar_buf:
                cur_line = cur_line.strip()
                if cur_line.startswith("stats socket "):
                    soc_name = cur_line.replace("stats socket ", "").strip()
                    soc_name = soc_name.split(" ")[0]
                    break

            # Check
            if not soc_name:
                logger.warn("Unable to locate stats socket (giveup)")
                return

            # Ok
            logger.info("Got soc_name=%s", soc_name)

            # -------------------------------
            # Open socket, send and readall
            # -------------------------------

            ha_buf = ""
            try:
                soc = None
                try:
                    logger.info("Alloc socket, soc_name=%s", soc_name)
                    soc = socket.socket(socket.AF_UNIX, type=socket.SOCK_STREAM)
                    logger.info("Connect socket, soc_name=%s", soc_name)
                    soc.connect(soc_name)
                    SolBase.sleep(0)
                    logger.info("Send socket, soc_name=%s", soc_name)
                    soc.sendall("show stat\n")
                    SolBase.sleep(0)

                    logger.info("Recv (start) socket, soc_name=%s", soc_name)
                    buf = soc.recv(1024)
                    while buf:
                        ha_buf += buf
                        logger.info("Recv (loop) socket, soc_name=%s", soc_name)
                        buf = soc.recv(1024)

                    logger.info("Recv (over) socket, soc_name=%s", soc_name)
                finally:
                    logger.info("Closing socket, soc_name=%s", soc_name)
                    SolBase.safe_close_socket(soc)
                    SolBase.sleep(0)
            except Exception as e:
                logger.warn("Exception, ex=%s", SolBase.extostr(e))
                raise

            # -------------------------------
            # Parse
            # -------------------------------

            # Parse
            ar_ha = self.parse_buffer(ha_buf)

            # Name mapping
            d_map = {
                "scur": "session_cur",
                "slim": "session_limit",
                "dreq": "denied_req",
                "dresp": "denied_resp",
                "ereq": "err_req",
                "econ": "err_conn",
                "eresp": "err_resp",
                "hrsp_1xx": "hrsp_1xx",
                "hrsp_2xx": "hrsp_2xx",
                "hrsp_3xx": "hrsp_3xx",
                "hrsp_4xx": "hrsp_4xx",
                "hrsp_5xx": "hrsp_5xx",
                "hrsp_other": "hrsp_other",
                "qtime": "avg_time_queue_ms",
                "ctime": "avg_time_connect_ms",
                "rtime": "avg_time_resp_ms",
                "ttime": "avg_time_session_ms",
                "status_ok": "status_ok",
                "status_ko": "status_ko",
            }

            # Global stuff
            d_global = {
                "scur": 0.0,
                "slim": 0.0,
                "dreq": 0.0,
                "dresp": 0.0,
                "ereq": 0.0,
                "econ": 0.0,
                "eresp": 0.0,
                "status_ok": 0.0,
                "status_ko": 0.0,
                "hrsp_1xx": 0.0,
                "hrsp_2xx": 0.0,
                "hrsp_3xx": 0.0,
                "hrsp_4xx": 0.0,
                "hrsp_5xx": 0.0,
                "hrsp_other": 0.0,
                "qtime": 0.0,
                "ctime": 0.0,
                "rtime": 0.0,
                "ttime": 0.0,
            }

            # Lets rock
            for cur_d in ar_ha:
                # String
                proxy_name = cur_d["pxname"]
                service_name = cur_d["svname"]
                status = cur_d["status"]

                # -----------------------
                # BYPASS STATS
                # -----------------------

                if proxy_name == "stats":
                    continue

                # -----------------------
                # GLOBAL
                # -----------------------

                # Global stuff
                if status in ["OPEN", "UP"]:
                    d_global["status_ok"] += 1.0
                    cur_d["status_ok"] = 1.0
                    cur_d["status_ko"] = 0.0
                else:
                    d_global["status_ko"] += 1.0
                    cur_d["status_ok"] = 0.0
                    cur_d["status_ko"] = 1.0

                # Global stuff
                for s in [
                    "scur", "slim", "dreq", "dresp", "ereq", "econ", "eresp",
                    "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx", "hrsp_5xx", "hrsp_other",
                ]:
                    d_global[s] += cur_d[s]

                # Global stuff
                for s in [
                    "qtime", "ctime", "rtime", "ttime",
                ]:
                    d_global[s] = max(d_global[s], cur_d[s])

                # -----------------------
                # BYPASS REAL SERVERS
                # -----------------------
                if service_name not in ["FRONTEND", "BACKEND"]:
                    continue

                # -----------------------
                # LOCAL : PUSH
                # -----------------------
                for s in [
                    "scur", "slim", "dreq", "dresp", "ereq", "econ", "eresp",
                    "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx", "hrsp_5xx", "hrsp_other",
                    "qtime", "ctime", "rtime", "ttime",
                    "status_ok", "status_ko",
                ]:
                    # Name mapping
                    s_map = d_map[s]

                    # Key
                    s_key = "k.haproxy." + s_map

                    # Tag
                    d_tag = {
                        "PROXY": service_name + "." + proxy_name,
                    }

                    # Push
                    self.notify_value_n(
                        counter_key=s_key,
                        d_disco_id_tag=d_tag,
                        counter_value=cur_d[s],
                    )
            # -----------------------
            # GLOBAL : PUSH
            # -----------------------
            for s in [
                "scur", "slim", "dreq", "dresp", "ereq", "econ", "eresp",
                "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx", "hrsp_5xx", "hrsp_other",
                "qtime", "ctime", "rtime", "ttime",
                "status_ok", "status_ko",
            ]:
                # Name mapping
                s_map = d_map[s]

                # Key
                s_key = "k.haproxy." + s_map

                # Push
                self.notify_value_n(
                    counter_key=s_key,
                    d_disco_id_tag={"PROXY": "ALL"},
                    counter_value=d_global[s],
                )

            # Success, notify started (global only)
            logger.info("Run ok (signaling up)")
            self.notify_value_n(
                counter_key="k.haproxy.started",
                d_disco_id_tag={"PROXY": "ALL"},
                counter_value=1,
            )
        except Exception as e:
            logger.warn("Exception (signaling down), ex=%s", SolBase.extostr(e))
            # Failed
            self.notify_value_n(
                counter_key="k.haproxy.started",
                d_disco_id_tag={"PROXY": "ALL"},
                counter_value=0,
            )
