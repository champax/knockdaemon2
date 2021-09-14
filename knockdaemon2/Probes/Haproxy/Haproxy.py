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
import csv
import logging
import re
import socket
from StringIO import StringIO

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase

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
        Not used

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
            logger.debug("Parsing, cur_line=%s", cur_line)
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
            logger.debug("Got cur_d=%s", cur_d)
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

            try:
                ha_buf = self.read_soc(soc_name, "show stat")
            except Exception as e:
                logger.warn("Exception, ex=%s", SolBase.extostr(e))
                raise e

            # -------------------------------
            # Parse
            # -------------------------------

            # Parse
            csv_dict = self.csv_parse(ha_buf)

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

            # initialize output dict
            agregated_dict = {}
            # Lets rock
            for cur_d in csv_dict:
                # String
                proxy_name = cur_d["# pxname"]
                service_name = cur_d["svname"]
                status = cur_d["status"]

                # -----------------------
                # BYPASS STATS
                # -----------------------

                if proxy_name == "stats":
                    continue

                # -----------------------
                # Initialize aggregated record
                # -----------------------
                if proxy_name not in agregated_dict:
                    agregated_dict[proxy_name] = dict()

                    # initialize agregated_dict
                    agregated_dict[proxy_name]['msg'] = ""
                    for k in ["status_ok", "status_ko", "server_ok", "server_ko"]:
                        agregated_dict[proxy_name][k] = 0.0

                # -----------------------
                # GLOBAL
                # -----------------------

                # Global stuff
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
                # Global stuff
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
                if service_name not in ["FRONTEND", "BACKEND"]:  # real server
                    if cur_d['status'] in ["OPEN", "UP"]:
                        agregated_dict[proxy_name]['server_ok'] += 1
                        agregated_dict[proxy_name]['status_ok'] += 1
                        d_global["status_ok"] += 1.0


                    else:
                        agregated_dict[proxy_name]['server_ko'] += 1.0
                        agregated_dict[proxy_name]['status_ko'] += 1.0
                        agregated_dict[proxy_name]['msg'] += ";%s %s-%s" % (service_name, cur_d['check_status'], cur_d['check_code'])
                        d_global["status_ko"] += 1.0

                else:  # proxy
                    agregated_dict[proxy_name]['type'] = service_name.lower()
                    # -----------------------
                    # get needed data
                    # -----------------------
                    for s in [
                        "scur", "slim", "dreq", "dresp", "ereq", "econ", "eresp",
                        "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx", "hrsp_5xx", "hrsp_other",
                        "qtime", "ctime", "rtime", "ttime",

                    ]:
                        # Name mapping
                        s_map = d_map[s]
                        v = cur_d[s] or 0
                        agregated_dict[proxy_name][s_map] = float(v)

            for proxy_name, proxy_detail_d in agregated_dict.items():
                # -----------------------
                # LOCAL : PUSH each proxy
                # -----------------------
                if len(proxy_detail_d['msg']) == 0:
                    proxy_detail_d['msg'] = 'OK'

                self.notify_value_n(
                    counter_key="k.haproxy.%s" % proxy_detail_d['type'],
                    d_disco_id_tag={"PROXY": proxy_name},
                    counter_value=proxy_detail_d["status_ok"],
                    additional_fields=proxy_detail_d
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

        self.read_table(soc_name)

    def read_soc(self, soc_name, cmd):
        """
        Open socket, send and readall

        :param soc_name: Socket path
        :type soc_name: str
        :param cmd:
        :type cmd: str
        :return:
        :rtype str
        """
        ha_buf = ""
        soc = None
        try:
            logger.debug("Alloc socket, soc_name=%s", soc_name)
            soc = socket.socket(socket.AF_UNIX, type=socket.SOCK_STREAM)
            logger.debug("Connect socket, soc_name=%s", soc_name)
            soc.connect(soc_name)
            SolBase.sleep(0)
            logger.debug("Send socket, soc_name=%s", soc_name)
            soc.sendall("%s \n" % cmd)
            SolBase.sleep(0)

            logger.debug("Recv (start) socket, soc_name=%s", soc_name)
            buf = soc.recv(1024)
            while buf:
                ha_buf += buf
                logger.debug("Recv (loop) socket, soc_name=%s", soc_name)
                buf = soc.recv(1024)

            logger.debug("Recv (over) socket, soc_name=%s", soc_name)
        finally:
            logger.info("Closing socket, soc_name=%s", soc_name)
            SolBase.safe_close_socket(soc)
            SolBase.sleep(0)
        return ha_buf

    @classmethod
    def csv_parse(cls, ha_buf):
        """

        :param ha_buf: buffer to parse
        :type ha_buf: str
        :return:
        :rtype: csv.DictReader
        """
        f = StringIO()
        f.write(ha_buf)
        f.seek(0)

        return csv.DictReader(f)

    def read_table(self, soc_name):
        """
         echo "show table" | socat stdio tcp4-connect:127.0.0.1:2000
        # table: http-front-httpssl, type: binary, size:2097152, used:0
        # table: http_backend_backend_vulogauth_11295, type: ip, size:2097152, used:1

        :param soc_name: str
        :type soc_name: str
        :return:
        """
        regex = r"# table: ([-a-zA-Z0-9_]+), type: (\w+), size:(\d+), used:(\d+)"

        try:
            ha_buf = self.read_soc(soc_name, "show table")
        except Exception as e:
            logger.warn("Exception, ex=%s", SolBase.extostr(e))
            raise e

        matches = re.finditer(regex, ha_buf, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):

            logger.debug("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum=matchNum, start=match.start(), end=match.end(), match=match.group()))

            try:
                table_name, table_type, table_size, used = match.groups()
                self.notify_value_n(
                    counter_key="k.haproxy.table" ,
                    d_disco_id_tag={"TABLE": table_name,
                                    "TYPE": table_type},
                    counter_value=int(used),
                    additional_fields={"size": int(table_size)}
                )
            except Exception as e:
                logger.warning(SolBase.extostr(e))
                continue

