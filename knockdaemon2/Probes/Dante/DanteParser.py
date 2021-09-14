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

from knockdaemon2.Probes.Parser.BaseParser import BaseParser

logger = logging.getLogger(__name__)


class DanteParser(BaseParser):
    """
    Dante log parser
    Doc : http://www.inet.no/dante/doc/1.3.x/logformat.pdf
    """

    def __init__(self, file_mask=None, position_file=None, kvc=None):
        """
        Constructor
        """

        # Stats : event
        self.event_unknown = 0
        self.event_entry = 0
        self.event_traffic = 0
        self.event_terminate = 0

        # Stats : Request
        self.request_tcp_accept = 0
        self.request_tcp_connect = 0
        self.request_tcp_bind = 0
        self.request_tcp_bind_reply = 0
        self.request_udp_associate = 0
        self.request_udp_reply = 0
        self.request_unknown = 0

        # Stats : access
        self.access_pass = 0
        self.access_block = 0
        self.idle_report = 0
        self.potential_error_log = 0

        # Closure reason
        self.close_io_expired = 0
        self.close_client_reset_by_peer = 0
        self.close_client_close = 0
        self.close_other = 0

        # Report
        self.hash_report_header = dict()
        self.hash_report_row = dict()

        # Compute report
        self.hash_computed_header = None
        self.hash_computed_row = None

        # Call base
        BaseParser.__init__(self, file_mask, position_file, kvc)

    # ================================
    # LOW LEVEL OVERRIDES
    # ================================

    def on_file_pre_parsing(self):
        """
        Called BEFORE the file is parsed.
        """

        # Reset the report hashes
        self.hash_report_header = dict()
        self.hash_report_row = dict()
        self.idle_report = 0

    def on_file_post_parsing(self):
        """
        Called after a file has been parsed
        """

        # Must populate counters now
        self.populate_counters()

    def on_file_parse_line(self, buf):
        """
        Called when a line buffer has to be parsed
        :param buf: Buffer
        :type buf: str
        :return Bool (True : Success, False : Failed)
        :rtype bool
        """
        return self.try_parse(buf)

    # ================================
    # IMPLEMENTATION
    # ================================

    def populate_counters(self):
        """
        Populate counters
        """

        # ===================
        # DISCO KEY
        # ===================

        self.notify_discovery_n("k.dante.discovery", {"ID": "dante"})

        # ===================
        # DATA
        # ===================

        # Stats : line
        self.notify_key_value("knock.dante.line_parsed", self.line_parsed)
        self.notify_key_value("knock.dante.line_parsed_ok", self.line_parsed_ok)
        self.notify_key_value("knock.dante.line_parsed_failed", self.line_parsed_failed)
        self.notify_key_value("knock.dante.line_parsed_skipped", self.line_parsed_skipped)

        # Stats : event
        self.notify_key_value("knock.dante.event_unknown", self.event_unknown)
        self.notify_key_value("knock.dante.event_entry", self.event_entry)
        self.notify_key_value("knock.dante.event_traffic", self.event_traffic)
        self.notify_key_value("knock.dante.event_terminate", self.event_terminate)

        # Stats : Request
        self.notify_key_value("knock.dante.request_tcp_accept", self.request_tcp_accept)
        self.notify_key_value("knock.dante.request_tcp_connect", self.request_tcp_connect)
        self.notify_key_value("knock.dante.request_tcp_bind", self.request_tcp_bind)
        self.notify_key_value("knock.dante.request_tcp_bind_reply", self.request_tcp_bind_reply)
        self.notify_key_value("knock.dante.request_udp_associate", self.request_udp_associate)
        self.notify_key_value("knock.dante.request_udp_reply", self.request_udp_reply)
        self.notify_key_value("knock.dante.request_unknown", self.request_unknown)

        # Stats : access
        self.notify_key_value("knock.dante.access_pass", self.access_pass)
        self.notify_key_value("knock.dante.access_block", self.access_block)
        self.notify_key_value("knock.dante.idle_report", self.idle_report)
        self.notify_key_value("knock.dante.potential_error_log", self.potential_error_log)

        # Closure reason
        self.notify_key_value("knock.dante.close_io_expired", self.close_io_expired)
        self.notify_key_value("knock.dante.close_client_reset_by_peer",
                              self.close_client_reset_by_peer)
        self.notify_key_value("knock.dante.close_client_close", self.close_client_close)
        self.notify_key_value("knock.dante.close_other", self.close_other)

        # Last parse time
        self.notify_key_value("knock.dante.last_parse_time_ms", self.last_parse_time_ms)

        # Current position, current file
        self.notify_key_value("knock.dante.file_cur_name", self.file_cur_name)
        self.notify_key_value("knock.dante.file_cur_pos", self.file_cur_pos)

        # ===================
        # Report stuff...
        # ===================

        self.hash_computed_header = self.compute_report_header()
        self.hash_computed_row = self.compute_report_row()

        for key, value in self.hash_computed_header.iteritems():
            self.notify_key_value(key, value)

        for key, value in self.hash_computed_row.iteritems():
            self.notify_key_value(key, value)

    def notify_key_value(self, key, value, append_dante=True):
        """
        Notify
        :param key: Key
        :type key: str, unicode
        :param append_dante; True if append [dante]
        :type append_dante: bool
        :param value: Value
        """

        if self.kvc:
            # Callback (unittest)
            logger.debug("notify_key_value : to callback, key=%s, value=%s", key, value)
            self.kvc(key, value)
        else:
            # server
            logger.debug("notify_key_value : to server, key=%s, value=%s", key, value)
            if not append_dante:
                self.notify_value_n(key, None, value)
            else:
                self.notify_value_n(key, {"ID": "dante"}, value)

    def try_parse(self, buf):
        """
        Try to parse
        :param buf: Buffer
        :type buf: str
        :return Bool
        :rtype bool
        """

        # Buffer :
        # Mar 13 13:13:13 lb02 danted[538]: pass(2): tcp/connect -:
        # Note : LOG FORMAT IS BULLSHIT

        # PPE
        # Mar 14 10:16:04 lb02 danted[538]: pass(1): tcp/connect ]: 4321
        # -> 10.0.10.3.53784 -> 3659,  3659 -> 10.0.10.100.1080 -> 4321: connection i/o expired
        # Mar 14 10:16:04 lb02 danted[538]: pass(2): tcp/connect ]: 4321
        # -> 10.0.10.3.53784 -> 3659,  3659 ->
        # feedback.push.apple.com.2196 -> 4321: connection i/o expired

        # LOCAL
        # Mar 13 18:03:29 (1363194209) danted[22781]: dante v1.1.19 up 0 days, 0:00, a: 0, c: 0
        # Mar 13 18:03:29 (1363194209) danted[22781]: negotiators (1): a: 0, h: 0, c: 0
        # Mar 13 18:03:29 (1363194209) danted[22781]: requests (4): a: 0, h: 0, c: 0
        # Mar 13 18:03:29 (1363194209) danted[22781]: iorelayers (1): a: 0, h: 0, c: 0

        # Split using " "
        ar = buf.split(" ")

        # Activities logs
        # 0 : Mar           ===> [Month]
        # 1 : 13            ===> [Day]
        # 2 : 13:13:13      ===> [HH:MM:SS]
        # 3 : lb02          ===> [Server]
        # 4 : danted[538]:  ===> [Daemon[pid]:]
        # 5 : pass(2):      ===> [AccessControl(rule N):]
        # 6 : tcp/connect   ===> [RequestType]
        # 7 : -:            ===> [Event]
        # BULLSHIT stuff
        # LAST :            ===> if event==Closure : reason of closure

        # SIGUSR1 report
        # 0  : Mar           ===> [Month]
        # 1  : 13            ===> [Day]
        # 2  : 13:13:13      ===> [HH:MM:SS]
        # 3  : lb02          ===> [Server]
        # 4  : danted[538]:  ===> [Daemon[pid]:]
        # 5  ; dante
        # 6  : v1.1.19
        # 7  : up
        # 8  : 0
        # 9  : days,
        # 10 : 0:00,
        # 11 : a:
        # 12 : 0,
        # 13 : c:
        # 14 : 0

        # SIGUSR1 report
        # 0  : Mar           ===> [Month]
        # 1  : 13            ===> [Day]
        # 2  : 13:13:13      ===> [HH:MM:SS]
        # 3  : lb02          ===> [Server]
        # 4  : danted[538]:  ===> [Daemon[pid]:]
        # 5  ; negotiators
        # 6  : (1):
        # 7  : a:
        # 8  : 0,
        # 9  : h:
        # 10 : 0,
        # 11 : c:
        # 12 : 0

        # IDLE report
        # Mar 14 17:55:01 lb02 danted[538]: 10.0.10.3.55850 <->
        # feedback.push.apple.com.2196: idle 636s

        # Must have 8 at least
        if len(ar) < 8:
            self.line_parsed_skipped += 1
            return False

        # Patch (one digit day)
        if ar[1] == "":
            ar.remove("")

        # Must have 8 at least after patch
        if len(ar) < 8:
            self.line_parsed_skipped += 1
            return False

        # Get
        access_control = ar[5]
        request_type = ar[6]
        event_type = ar[7]

        # Access control
        if access_control.startswith("pass"):
            self.access_pass += 1
        elif access_control.startswith("block"):
            self.access_block += 1
        elif access_control == "dante":
            # ---------------------
            # SIGUSR Header
            # Mar 13 18:03:29 (1363194209) danted[22781]: dante v1.1.19 up 0 days, 0:00, a: 0, c: 0
            # ---------------------
            report_svr = ar[3]
            report_process = ar[4]

            # Got danted[538]:
            report_pid = int(report_process.replace("danted[", "").replace("]:", ""))

            # A value
            a_value = int(ar[12].replace(",", ""))
            # C value
            c_value = int(ar[14])

            # Process
            self.populate_report_header(report_svr, report_pid, a_value, c_value)
            return True
        elif access_control == "negotiators" \
                or access_control == "requests" \
                or access_control == "iorelayers":
            # ---------------------
            # SIGUSR1 report
            # Mar 13 18:03:29 (1363194209) danted[22781]: negotiators (1): a: 0, h: 0, c: 0
            # ---------------------
            report_svr = ar[3]
            report_process = ar[4]

            # Got danted[538]:
            report_pid = int(report_process.replace("danted[", "").replace("]:", ""))

            # Report item
            report_item = ar[5]

            # A value
            a_value = int(ar[8].replace(",", ""))
            # H value
            h_value = int(ar[10].replace(",", ""))
            # C value
            c_value = int(ar[12])

            # Process
            self.populate_report_row(
                report_svr, report_pid, report_item, a_value, h_value, c_value
            )
            return True
        else:
            # Idle or unknown stuff...
            # Mar 14 17:55:01 lb02 danted[538]: 10.0.10.3.55850 <->
            # feedback.push.apple.com.2196: idle 636s
            if ar[len(ar) - 2] == "idle":
                # ---------------------
                # SIGUSR1 report
                # Idle
                # ---------------------
                self.idle_report += 1
                return True
            else:
                logger.debug("Unknow access_control=[%s], buffer=%s", access_control, buf)
                self.potential_error_log += 1
                # If we are in access unknow, this is an error, do not continue
                return True

        # Event
        is_terminate = False
        if event_type == "[:":
            self.event_entry += 1
        elif event_type == "-:":
            self.event_traffic += 1
        elif event_type == "]:":
            self.event_terminate += 1
            is_terminate = True
        else:
            logger.debug("Unknow event_type=[%s], buffer=%s", event_type, buf)
            self.event_unknown += 1

        # Request type
        if request_type == "tcp/accept":
            self.request_tcp_accept += 1
        elif request_type == "tcp/connect":
            self.request_tcp_connect += 1
        elif request_type == "tcp/bind":
            self.request_tcp_bind += 1
        elif request_type == "tcp/bindreply":
            self.request_tcp_bind_reply += 1
        elif request_type == "udp/udpassociate":
            self.request_udp_associate += 1
        elif request_type == "udp/udpreply":
            self.request_udp_reply += 1
        else:
            logger.debug("Unknow request_type=[%s], buffer=%s", request_type, buf)
            self.request_unknown += 1

        # Closure reason
        if is_terminate:
            # Try to detect closure reason
            if buf.find("connection i/o expired") > 0:
                self.close_io_expired += 1
            elif buf.find("client error: Connection reset by peer (errno = 104)") > 0:
                self.close_client_reset_by_peer += 1
            elif buf.find("client closed"):
                self.close_client_close += 1
            else:
                logger.debug("Unknown closure reason, buffer=%s", buf)
                self.close_other += 1
        return True

    def populate_report_header(self, report_svr, report_pid, a_value, c_value):
        """
        Report header
        :param report_svr: Server
        :type report_svr: svr
        :param report_pid: Pid
        :type report_pid: int
        :param a_value: Value
        :type a_value: int
        :param c_value: Value
        :type c_value: int
        """

        svr_key = "{0}{1}".format(report_svr, report_pid)

        # Dict[Server] => ( Dict[valueKey] => Value )
        if svr_key not in self.hash_report_header:
            # Init a new one
            logger.debug("ReportHeader : add server, svr=%s, pid=%s, a=%s, c=%s",
                         report_svr, report_pid, a_value, c_value)
            h = dict()
            h["a_value"] = a_value
            h["c_value"] = c_value
            # Hash it
            self.hash_report_header[svr_key] = h
        else:
            logger.debug("ReportHeader : upd server, svr=%s, pid=%s, a=%s, c=%s",
                         report_svr, report_pid, a_value, c_value)
            # Got existing... get it
            h = self.hash_report_header[svr_key]
            # Replace values
            h["a_value"] = a_value
            h["c_value"] = c_value

    def compute_report_header(self):
        """
        Compute report header
        Dict returned :
        - "knock.dante.header.key.count"
        - "knock.dante.header.a_value.sum"
        - "knock.dante.header.c_value.sum"
        - "knock.dante.header.a_value.min"
        - "knock.dante.header.c_value.min"
        - "knock.dante.header.a_value.max"
        - "knock.dante.header.c_value.max"
        :return: Dict
        :rtype: dict
        """

        h_out = dict()

        for key in self.hash_report_header.keys():
            # Get hash value
            h_value = self.hash_report_header[key]
            a_value = h_value["a_value"]
            c_value = h_value["c_value"]

            # Populate
            if "knock.dante.header.key.count" not in h_out:
                h_out["knock.dante.header.key.count"] = 1
                h_out["knock.dante.header.a_value.sum"] = a_value
                h_out["knock.dante.header.c_value.sum"] = c_value
                h_out["knock.dante.header.a_value.min"] = a_value
                h_out["knock.dante.header.c_value.min"] = c_value
                h_out["knock.dante.header.a_value.max"] = a_value
                h_out["knock.dante.header.c_value.max"] = c_value
            else:
                h_out["knock.dante.header.key.count"] += 1
                h_out["knock.dante.header.a_value.sum"] = \
                    h_out["knock.dante.header.a_value.sum"] + a_value
                h_out["knock.dante.header.c_value.sum"] = \
                    h_out["knock.dante.header.c_value.sum"] + c_value
                h_out["knock.dante.header.a_value.min"] = \
                    min(h_out["knock.dante.header.a_value.min"], a_value)
                h_out["knock.dante.header.c_value.min"] = \
                    min(h_out["knock.dante.header.c_value.min"], c_value)
                h_out["knock.dante.header.a_value.max"] = \
                    max(h_out["knock.dante.header.a_value.max"], a_value)
                h_out["knock.dante.header.c_value.max"] = \
                    max(h_out["knock.dante.header.c_value.max"], c_value)

        if "knock.dante.header.key.count" in h_out == 0:
            # Default
            h_out["knock.dante.header.key.count"] = 0
            h_out["knock.dante.header.a_value.sum"] = 0
            h_out["knock.dante.header.c_value.sum"] = 0
            h_out["knock.dante.header.a_value.min"] = 0
            h_out["knock.dante.header.c_value.min"] = 0
            h_out["knock.dante.header.a_value.max"] = 0
            h_out["knock.dante.header.c_value.max"] = 0

        return h_out

    def populate_report_row(self, report_svr, report_pid, report_item, a_value, h_value, c_value):
        """
        Report row
        :param report_svr: Server
        :type report_svr: str
        :param report_pid: Pid
        :type report_pid: int
        :param report_item: Item
        :type report_item: str
        :param a_value: Value
        :type a_value: int
        :param h_value: Value
        :type h_value: int
        :param c_value: Value
        :type c_value: int
        """

        svr_key = "{0}{1}".format(report_svr, report_pid)

        # Dict[Server] => (Dict[report_item] => ( Dict[valueKey] => Value ))
        if svr_key not in self.hash_report_row:
            logger.debug("ReportRow : add server, svr=%s, pid=%s, i=%s, a=%s, h=%s, c=%s",
                         report_svr, report_pid,
                         report_item, a_value, h_value, c_value)
            # Populate the item value
            h_values = dict()
            h_values["a_value"] = a_value
            h_values["h_value"] = h_value
            h_values["c_value"] = c_value

            # Create an hash for the report (report_item => Values)
            h_report = dict()
            h_report[report_item] = h_values

            # Register the server (report_svr => report_item)
            self.hash_report_row[svr_key] = h_report
        else:
            # Got existing server... get it
            h_report = self.hash_report_row[svr_key]

            # Check report item
            if report_item not in h_report:
                # Report not registered, add new values
                logger.debug("ReportRow : add item, svr=%s, pid=%s, i=%s, a=%s, h=%s, c=%s",
                             report_svr, report_pid,
                             report_item, a_value, h_value, c_value)
                h_values = dict()
                h_values["a_value"] = a_value
                h_values["h_value"] = h_value
                h_values["c_value"] = c_value
                # Hash them
                h_report[report_item] = h_values
            else:
                logger.debug("ReportRow : upd item, svr=%s, pid=%s, i=%s, a=%s, h=%s, c=%s",
                             report_svr, report_pid,
                             report_item, a_value, h_value, c_value)
                # Replace values : get
                h_values = h_report[report_item]
                # Replace
                h_values["a_value"] = a_value
                h_values["h_value"] = h_value
                h_values["c_value"] = c_value

    def compute_report_row(self):
        """
        Compute report row
        Dict returned :
        - "knock.dante.row.row.key.count"
        - "knock.dante.row.negotiators.a_value.sum"
        - "knock.dante.row.negotiators.h_value.sum"
        - "knock.dante.row.negotiators.c_value.sum"
        - "knock.dante.row.negotiators.a_value.min"
        - "knock.dante.row.negotiators.h_value.min"
        - "knock.dante.row.negotiators.c_value.min"
        - "knock.dante.row.negotiators.a_value.max"
        - "knock.dante.row.negotiators.h_value.max"
        - "knock.dante.row.negotiators.c_value.max"
        - "knock.dante.row.requests.a_value.sum"
        - "knock.dante.row.requests.h_value.sum"
        - "knock.dante.row.requests.c_value.sum"
        - "knock.dante.row.requests.a_value.min"
        - "knock.dante.row.requests.h_value.min"
        - "knock.dante.row.requests.c_value.min"
        - "knock.dante.row.requests.a_value.max"
        - "knock.dante.row.requests.h_value.max"
        - "knock.dante.row.requests.c_value.max"
        - "knock.dante.row.iorelayers.a_value.sum"
        - "knock.dante.row.iorelayers.h_value.sum"
        - "knock.dante.row.iorelayers.c_value.sum"
        - "knock.dante.row.iorelayers.a_value.min"
        - "knock.dante.row.iorelayers.h_value.min"
        - "knock.dante.row.iorelayers.c_value.min"
        - "knock.dante.row.iorelayers.a_value.max"
        - "knock.dante.row.iorelayers.h_value.max"
        - "knock.dante.row.iorelayers.c_value.max"
        :return: Dict
        :rtype: dict
        """

        h_out = dict()

        for key in self.hash_report_row.keys():
            # Get hash server (=> items)
            h_server = self.hash_report_row[key]

            # Browse items
            for item in h_server.keys():
                # Get values
                hash_value = h_server[item]

                if "a_value" in hash_value:
                    a_value = hash_value["a_value"]
                else:
                    a_value = 0

                if "h_value" in hash_value:
                    h_value = hash_value["h_value"]
                else:
                    h_value = 0

                if "c_value" in hash_value:
                    c_value = hash_value["c_value"]
                else:
                    c_value = 0

                # Populate
                self.fill_dict(h_out, "knock.dante.row.key.count", 1, "sum")

                self.fill_dict(h_out, "knock.dante.row." + item + ".a_value.sum", a_value, "sum")
                self.fill_dict(h_out, "knock.dante.row." + item + ".h_value.sum", h_value, "sum")
                self.fill_dict(h_out, "knock.dante.row." + item + ".c_value.sum", c_value, "sum")

                self.fill_dict(h_out, "knock.dante.row." + item + ".a_value.min", a_value, "min")
                self.fill_dict(h_out, "knock.dante.row." + item + ".h_value.min", h_value, "min")
                self.fill_dict(h_out, "knock.dante.row." + item + ".c_value.min", c_value, "min")

                self.fill_dict(h_out, "knock.dante.row." + item + ".a_value.max", a_value, "max")
                self.fill_dict(h_out, "knock.dante.row." + item + ".h_value.max", h_value, "max")
                self.fill_dict(h_out, "knock.dante.row." + item + ".c_value.max", c_value, "max")

        self.fix_dict(h_out, "knock.dante.row.key.count")
        self.fix_dict(h_out, "knock.dante.row.negotiators.a_value.sum")
        self.fix_dict(h_out, "knock.dante.row.negotiators.h_value.sum")
        self.fix_dict(h_out, "knock.dante.row.negotiators.c_value.sum")
        self.fix_dict(h_out, "knock.dante.row.negotiators.a_value.min")
        self.fix_dict(h_out, "knock.dante.row.negotiators.h_value.min")
        self.fix_dict(h_out, "knock.dante.row.negotiators.c_value.min")
        self.fix_dict(h_out, "knock.dante.row.negotiators.a_value.max")
        self.fix_dict(h_out, "knock.dante.row.negotiators.h_value.max")
        self.fix_dict(h_out, "knock.dante.row.negotiators.c_value.max")
        self.fix_dict(h_out, "knock.dante.row.requests.a_value.sum")
        self.fix_dict(h_out, "knock.dante.row.requests.h_value.sum")
        self.fix_dict(h_out, "knock.dante.row.requests.c_value.sum")
        self.fix_dict(h_out, "knock.dante.row.requests.a_value.min")
        self.fix_dict(h_out, "knock.dante.row.requests.h_value.min")
        self.fix_dict(h_out, "knock.dante.row.requests.c_value.min")
        self.fix_dict(h_out, "knock.dante.row.requests.a_value.max")
        self.fix_dict(h_out, "knock.dante.row.requests.h_value.max")
        self.fix_dict(h_out, "knock.dante.row.requests.c_value.max")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.a_value.sum")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.h_value.sum")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.c_value.sum")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.a_value.min")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.h_value.min")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.c_value.min")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.a_value.max")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.h_value.max")
        self.fix_dict(h_out, "knock.dante.row.iorelayers.c_value.max")

        return h_out
