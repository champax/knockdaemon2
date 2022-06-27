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
import csv
import logging
import socket
from io import StringIO

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Haproxy(KnockProbe):
    """
    Probe
    DOC : https://cbonte.github.io/haproxy-dconv/1.6/management.html#9.1
    """

    # Name mapping
    D_MAP = {
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

    def __init__(self):
        """
        Constructor
        """

        KnockProbe.__init__(self)
        self.category = "/web/haproxy"

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

    def _execute_linux(self):
        """
        Exec
        """

        self._execute_native()

    @classmethod
    def try_get_socket_name(cls, config_buf):
        """
        Try to get socket name from haproxy configuration
        :param config_buf: str
        :type config_buf: str
        :return str,None
        :rtype str,None
        """

        ar_buf = config_buf.split("\n")
        for cur_line in ar_buf:
            cur_line = cur_line.strip()
            if cur_line.startswith("stats socket "):
                soc_name = cur_line.replace("stats socket ", "").strip()
                soc_name = soc_name.split(" ")[0]
                return soc_name
        return None

    def _notify_down(self):
        """
        Notify down
        """
        # Failed
        self.notify_value_n(
            counter_key="k.haproxy.started",
            d_tags={"PROXY": "ALL"},
            counter_value=0,
        )

    def process_haproxy_buffer(self, ha_buf):
        """
        Process haproxy buffer
        :param ha_buf: str
        :type ha_buf: str
        """

        # Parse socket buffer
        csv_dict = self.csv_parse(ha_buf)

        # Init global stuff
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

        # Output dict
        agregated_dict = dict()

        # Lets rock
        for cur_d in csv_dict:
            proxy_name = cur_d["# pxname"]
            if proxy_name == "stats":
                continue

            service_name = cur_d["svname"]

            # Initialize aggregated record
            if proxy_name not in agregated_dict:
                agregated_dict[proxy_name] = dict()
                agregated_dict[proxy_name]['msg'] = ""
                for k in ["status_ok", "status_ko", "server_ok", "server_ko"]:
                    agregated_dict[proxy_name][k] = 0.0

            # -----------------------
            # GLOBAL
            # -----------------------

            # Global stuff (sum)
            for s in [
                "scur", "slim", "dreq", "dresp", "ereq", "econ", "eresp",
                "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx", "hrsp_5xx", "hrsp_other",
            ]:
                if cur_d[s] == '':
                    cur_d[s] = 0
                try:
                    d_global[s] += float(cur_d[s])
                except ValueError:
                    logger.warning("Can not converst to float %s in %s", cur_d[s], cur_d)
                except TypeError:
                    logger.warning("Can not converst to float %s in %s", cur_d[s], cur_d)

            # Global stuff (max)
            for s in [
                "qtime", "ctime", "rtime", "ttime",
            ]:
                if cur_d[s] == '':
                    cur_d[s] = 0
                try:
                    d_global[s] = max(d_global[s], float(cur_d[s]))
                except ValueError:
                    logger.warning("Can not convert to float %s in %s", cur_d[s], cur_d)

            # -----------------------
            # Server , frontend, backend
            # -----------------------
            if service_name not in ["FRONTEND", "BACKEND"]:
                # real server
                if cur_d['status'] in ["OPEN", "UP"]:
                    agregated_dict[proxy_name]['server_ok'] += 1
                    agregated_dict[proxy_name]['status_ok'] += 1
                    d_global["status_ok"] += 1.0
                else:
                    agregated_dict[proxy_name]['server_ko'] += 1.0
                    agregated_dict[proxy_name]['status_ko'] += 1.0
                    agregated_dict[proxy_name]['msg'] += ";%s %s-%s" % (service_name, cur_d['check_status'], cur_d['check_code'])
                    d_global["status_ko"] += 1.0

            else:
                # proxy
                agregated_dict[proxy_name]['type'] = service_name.lower()
                for s in [
                    "scur", "slim", "dreq", "dresp", "ereq", "econ", "eresp",
                    "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx", "hrsp_5xx", "hrsp_other",
                    "qtime", "ctime", "rtime", "ttime",

                ]:
                    # Name mapping
                    s_map = Haproxy.D_MAP[s]
                    v = cur_d[s] or 0
                    agregated_dict[proxy_name][s_map] = float(v)

        # Push counters / LOCAL
        for proxy_name, proxy_detail_d in agregated_dict.items():
            if len(proxy_detail_d['msg']) == 0:
                proxy_detail_d['msg'] = 'OK'
            self.notify_value_n(
                counter_key="k.haproxy.%s" % proxy_detail_d['type'],
                d_tags={"PROXY": proxy_name},
                counter_value=proxy_detail_d["status_ok"],
                d_values=proxy_detail_d
            )
        # Push counters / GLOBAL
        for s in [
            "scur", "slim", "dreq", "dresp", "ereq", "econ", "eresp",
            "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx", "hrsp_5xx", "hrsp_other",
            "qtime", "ctime", "rtime", "ttime",
            "status_ok", "status_ko",
        ]:
            s_key = "k.haproxy." + Haproxy.D_MAP[s]
            self.notify_value_n(
                counter_key=s_key,
                d_tags={"PROXY": "ALL"},
                counter_value=d_global[s],
            )

        # Success, notify started (global only)
        logger.debug("Run ok (signaling up)")
        self.notify_value_n(
            counter_key="k.haproxy.started",
            d_tags={"PROXY": "ALL"},
            counter_value=1,
        )

    def _execute_native(self):
        """
        Exec, native
        """

        # Detect haproxy
        try:
            if not FileUtility.is_file_exist('/etc/haproxy/haproxy.cfg'):
                logger.debug("Give up (/etc/haproxy/haproxy.cfg not found)")
                return
            logger.debug("Haproxy detected (/etc/haproxy/haproxy.cfg found)")

            # Get stat socket
            soc_name = self.try_get_socket_name(FileUtility.file_to_textbuffer("/etc/haproxy/haproxy.cfg", "utf8"))
            if not soc_name:
                logger.debug("Give up (unable to locate stats socket)")
                self._notify_down()
                return

            # Read all
            ha_buf = self.try_read_socket(soc_name, "show stat")
            if ha_buf is None:
                logger.debug("Give up (read_soc None)")
                self._notify_down()
                return

            # Process buffer
            self.process_haproxy_buffer(ha_buf)

        except Exception as e:
            logger.warning("Exception (signaling down), ex=%s", SolBase.extostr(e))
            self._notify_down()

    @classmethod
    def try_read_socket(cls, soc_name, cmd):
        """
        Open socket, send and readall

        :param soc_name: Socket path
        :type soc_name: str
        :param cmd: str
        :type cmd: str
        :return: str,None
        :rtype str,None
        """

        soc = None
        try:
            ha_buf = ""
            logger.debug("Alloc socket, soc_name=%s", soc_name)
            soc = socket.socket(socket.AF_UNIX, type=socket.SOCK_STREAM)
            logger.debug("Connect socket, soc_name=%s", soc_name)
            soc.connect(soc_name)
            SolBase.sleep(0)
            logger.debug("Send socket, soc_name=%s", soc_name)
            soc.sendall(("%s \n" % cmd).encode("utf8"))
            SolBase.sleep(0)

            logger.debug("Recv (start) socket, soc_name=%s", soc_name)
            buf = soc.recv(1024)
            while buf:
                if isinstance(buf, bytes):
                    buf = buf.decode("utf8")
                ha_buf += buf
                logger.debug("Recv (loop) socket, soc_name=%s", soc_name)
                buf = soc.recv(1024)

            logger.debug("Recv (over) socket, soc_name=%s", soc_name)
            return ha_buf
        except Exception as e:
            logger.warning("Give up (exception), soc_name=%s, ex=%s", soc_name, SolBase.extostr(e))
            return None
        finally:
            logger.debug("Closing socket, soc_name=%s", soc_name)
            SolBase.safe_close_socket(soc)
            SolBase.sleep(0)

    @classmethod
    def csv_parse(cls, ha_buf):
        """

        :param ha_buf: buffer to parse
        :type ha_buf: str
        :return: csv.DictReader
        :rtype: csv.DictReader
        """
        f = StringIO()
        f.write(ha_buf)
        f.seek(0)

        return csv.DictReader(f)
