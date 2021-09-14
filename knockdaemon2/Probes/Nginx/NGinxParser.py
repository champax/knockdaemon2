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

from pysolbase.SolBase import SolBase
from pysolmeters.DelayToCount import DelayToCount

from knockdaemon2.Probes.Parser.BaseParser import BaseParser

logger = logging.getLogger(__name__)


class NGinxStat(object):
    """
    Nginx stats
    """

    def __init__(self):
        """
        Init
        """

        self.log_count = 0
        self.log_count_with_up_stream = 0
        self.ng_reply_time_ms = DelayToCount("ngMs")
        self.up_reply_time_ms = DelayToCount("upMs")

        self.ng_reply_time_ms_longpoll = DelayToCount("ngMsLongPoll")
        self.up_reply_time_ms_longpoll = DelayToCount("upMsLongPoll")

        self.ng_hash_statuscode_to_count = dict()
        self.up_hash_statuscode_to_count = dict()

        # Pre-hash all status
        for a in NGinxParser.get_http_class_list():
            self.ng_hash_statuscode_to_count[a] = 0
            self.up_hash_statuscode_to_count[a] = 0

        # Cache
        self.request_cache_totalcount = 0
        self.request_cache_byte_totalsent = 0

        self.request_cache_nocache = 0
        self.request_cache_miss = 0
        self.request_cache_hit = 0

        self.request_cache_byte_nocache = 0
        self.request_cache_byte_miss = 0
        self.request_cache_byte_hit = 0


class NGinxLog(object):
    """
    Log item
    """

    def __init__(self):
        """
        Init
        """
        self.server = None
        self.date = None
        self.pipe = None
        self.remote_ip = None
        self.remote_port = None
        self.local_ip = None
        self.local_port = None
        self.http_status = None
        self.reply_ms = None
        self.http_version = None
        self.http_method = None
        self.http_context_req_keepalive = None
        self.http_context_req_transfert_encoding = None
        self.http_context_resp_keepalive = None
        self.http_context_resp_transfert_encoding = None
        self.http_request_content_length = None
        self.http_sent_bytes = None
        self.http_sent_body_bytes = None
        self.http_uri = None
        self.up_socket = None
        self.up_http_status_code = None
        self.up_http_ms = None
        self.up_http_context_keepalive = None
        self.up_http_context_transfert_encoding = None
        self.up_http_context_content_length = None
        self.up_http_cache = None
        self.user_agent = None

        self.component_name = None
        self.http_status_class = None
        self.up_http_statuscode_class = None


# noinspection PyAbstractClass
class NGinxParser(BaseParser):
    """
    NGinx parser
    """

    __EXCLUDE_SERVER = "excludeserver"

    def __init__(self, file_mask=None, position_file=None, kv_callback=None):
        """
        Constructor
        """

        # Alloc stat (Key => NGinxStat)
        self.hash_stat = dict()
        self.hash_exclude = dict()

        # Call base
        BaseParser.__init__(self, file_mask, position_file, kv_callback)

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
        BaseParser.init_from_config(self, k, d_yaml_config, d)

        # Go
        temp = d["excludeserver"]
        ar = temp.lower().split(',')
        for a in ar:
            self.hash_exclude[a] = a
            logger.info("Excluding server=%s", a)

    # ================================
    # LOW LEVEL OVERRIDES
    # ================================

    def on_file_pre_parsing(self):
        """
        Called BEFORE the file is parsed.
        """

        # Reset some stats
        for s in self.hash_stat.values():
            # Cache
            s.request_cache_totalcount = 0
            s.request_cache_byte_totalsent = 0

            s.request_cache_nocache = 0
            s.request_cache_miss = 0
            s.request_cache_hit = 0

            s.request_cache_byte_nocache = 0
            s.request_cache_byte_miss = 0
            s.request_cache_byte_hit = 0

    def on_file_post_parsing(self):
        """
        Called after a file has been parsed
        """

        # Must populate counters now
        self.populate_counters()

    def on_file_parse_line(self, buf):
        """
        Called when a line buf has to be parsed
        :param buf: Buffer
        :type buf: str
        :return Bool (True : Success, False : Failed)
        :rtype bool
        """
        return self.try_parse(buf)

    # ================================
    # IMPLEMENTATION
    # ================================

    def notify_key_value(self, counter_key, d_disco_id_tag, counter_value):
        """
        Notify
        :param counter_key: Counter key (str)
        :type counter_key: str
        :param d_disco_id_tag: None (if no discovery) or dict of {disco_id: disco_tag}
        :type d_disco_id_tag: None, dict
        :param counter_value: Counter value
        :type counter_value: object
        """

        if self.notify_kvc:
            # Callback (unittest)
            logger.debug("notify_key_value : to callback, key=%s, d=%, value=%s", counter_key, d_disco_id_tag, counter_value)
            # noinspection PyCallingNonCallable
            self.notify_kvc(counter_key, d_disco_id_tag, counter_value)
        else:
            # server
            logger.debug("notify_key_value : to server, key=%s, d=%s, value=%s", counter_key, d_disco_id_tag, counter_value)
            self.notify_value_n(counter_key, d_disco_id_tag, counter_value)

    # noinspection PyMethodMayBeStatic
    def try_to_int(self, buf):
        """
        Try cast to int
        :param buf: Buffer
        :type buf: str
        :return: int
        :rtype: int
        """
        # noinspection PyBroadException
        try:
            return int(buf)
        except:
            return 0

    # noinspection PyMethodMayBeStatic
    def try_to_float(self, buf):
        """
        Try cast to float
        :param buf: Buffer
        :type buf: str
        :return: float
        :rtype: float
        """
        # noinspection PyBroadException
        try:
            return float(buf)
        except:
            return float(0)

    def get_http_class(self, http_code):
        """
        Get http class
        :param http_code: Http status code
        :type http_code: int, str
        :return: "" if zero, "1xx" "2xx" "3xx" "4xx" "5xx" if valid, else "Unknown",
        else raise an exception.
        :rtype: str
        """

        if SolBase.is_int(http_code):
            a = http_code
        else:
            a = self.try_to_int(http_code)

        if a == 0:
            return "NoStatus"
        elif a < 100 or a > 599:
            return "Unknown"
        elif a < 200:
            return "1xx"
        elif a < 300:
            return "2xx"
        elif a < 400:
            return "3xx"
        elif a < 500:
            return "4xx"
        elif a < 600:
            return "5xx"
        else:
            raise Exception("Bug in the code")

    @classmethod
    def get_http_class_list(cls):
        """
        Return the known http class list
        :return: list
        :rtype: list
        """

        a = list()
        a.append("NoStatus")
        a.append("Unknown")
        a.append("1xx")
        a.append("2xx")
        a.append("3xx")
        a.append("4xx")
        a.append("5xx")
        return a

    # noinspection PyMethodMayBeStatic
    def get_compo_name(self, unix_socket_buffer):
        """
        Get component name
        from buf
        - "unix:/var/run/uwsgi/app/LetMediabox/socket"
        :param unix_socket_buffer: Unix socket buf
        :type unix_socket_buffer: str
        :return: Component name
        :rtype: str
        """

        # noinspection PyUnreachableCode,PyBroadException
        try:
            if unix_socket_buffer == "-":
                return "NoComponent"
            elif len(unix_socket_buffer) == 0:
                return "NoComponent"
            else:
                return unix_socket_buffer.split("/")[5]
        except:
            return "NoComponent"

    def super_split(self, buf):
        """
        Advanced split
        If return None, buf is excluded.
        :param buf: Buffer
        :type buf: str
        :return: NGinxLog
        :rtype: NGinxLog,None
        """

        # gatehttp02                                ===> 00 : Server
        # 2013-03-14T18:00:18+01:00                 ===> 01 : Date
        # pipe=.                                    ===> 02 : Pipelined?
        # 46.218.202.198:15126                      ===> 03 : Remote ip:port
        # 37.110.193.21:443                         ===> 04 : Local ip:port
        # st=200                                    ===> 05 : Http status
        # sec=0.474                                 ===> 06 : Response time sec
        # HTTP/1.1                                  ===> 07 : HTTP version
        # POST                                      ===> 08 : HTTP method
        # "keep-alive/-/close/-"                    ===> 09 :
        # http_connection keep alive / http_transfer_encoding / sent_http_connection keep alive
        # / sent_http_transfer_encoding
        # reqclen=67                                ===> 10 : Request content length
        # sentb=727                                 ===> 11 : Sent bytes
        # sentbodyb=407                             ===> 12 : Sent body bytes
        # "https://http.ppe.knock.com:443"            ===> 13 : Uri called
        # "unix:/var/run/uwsgi/app/GateHttp/socket" ===> 14 : Socket used (component inside)
        # upst=200                                  ===> 15 : Upstream http status code
        # upsec=0.035                               ===> 16 : Upstream ms
        # up="-/-/407"                              ===> 17 :
        # Upstream http_connection keep alive / http_transfer_encoding / content-length
        # upstcache=-                               ===> 18 : Upstream cache
        # ua="xxx/1048 CFNetwork/548.1.4 Darwin"    ===> 19 : User agent

        # Alloc
        ng = NGinxLog()

        # split up to Uri (field 13)
        ar = buf.replace("  ", " ").split(" ", 13)

        # Server
        ng.server = ar[0]
        if ng.server.lower() in self.hash_exclude:
            # Excluded
            return None
        ng.date = ar[1]
        ng.pipe = ar[2].split("=")[1]

        temp = ar[3].split(":")
        ng.remote_ip = temp[0]
        ng.remote_port = self.try_to_int(temp[1])

        temp = ar[4].split(":")
        ng.local_ip = temp[0]
        ng.local_port = self.try_to_int(temp[1])

        ng.http_status = ar[5].split("=")[1]

        ng.reply_ms = self.try_to_float(ar[6].split("=")[1]) * 1000

        ng.http_version = ar[7]
        ng.http_method = ar[8]

        temp = ar[9][1:-1].split("/")
        ng.http_context_req_keepalive = temp[0]
        ng.http_context_req_transfert_encoding = temp[1]
        ng.http_context_resp_keepalive = temp[2]
        ng.http_context_resp_transfert_encoding = temp[3]

        ng.http_request_content_length = self.try_to_int(ar[10].split("=")[1])
        ng.http_sent_bytes = self.try_to_int(ar[11].split("=")[1])
        ng.http_sent_body_bytes = self.try_to_int(ar[12].split("=")[1])

        # Here, ar[13] => Remaining buf.
        # Must process http_uri FIRST (can contains spaces)
        # "http://whatever whatever " "unixsocket"

        # We must start with "
        assert ar[13].startswith("\""), "ar[13] must start with \", got={0}".format(ar[13])
        # We look for '" "'
        idx = ar[13].find("\" \"")

        # Get uri
        ng.http_uri = ar[13][:idx + 1][1:-1]

        # Get remaining part
        buffer2 = ar[13][idx + 2:]

        # Remains here :
        # "unix:/var/run/uwsgi/app/GateHttp/socket" ===> 0 : Socket used (component inside)
        # upst=200                                  ===> 1 : Upstream http status code
        # upsec=0.035                               ===> 2 : Upstream ms
        # up="-/-/407"                              ===> 3 :
        # Upstream http_connection keep alive / http_transfer_encoding / content-length
        # upstcache=-                               ===> 4 : Upstream cache
        # ua="xxx/1048 CFNetwork/548.1.4 Darwin"    ===> 5 : User agent

        ar2 = buffer2.split(" ", 5)

        ng.up_socket = ar2[0][1:-1]
        ng.up_http_status_code = ar2[1].split("=")[1]
        ng.up_http_ms = self.try_to_float(ar2[2].split("=")[1]) * 1000

        temp = ar2[3].split("=")[1][1:-1].split("/")
        ng.up_http_context_keepalive = temp[0]
        ng.up_http_context_transfert_encoding = temp[1]
        ng.up_http_context_content_length = self.try_to_int(temp[2])
        ng.up_http_cache = ar2[4].split("=")[1]
        ng.user_agent = ar2[5].split("=")[1][1:-1]

        # COMPO using unix socket
        # "unix:/var/run/uwsgi/app/CompoName/socket"
        ng.component_name = self.get_compo_name(ng.up_socket)

        # HTTP class
        ng.http_status_class = self.get_http_class(ng.http_status)

        # UP stream class
        ng.up_http_statuscode_class = self.get_http_class(ng.up_http_status_code)

        # Patch for upstream if cache is on
        if ng.up_http_cache == "HIT":
            # In case of HIT, upstream is "-" => must detect component using url
            # => NoComponent : http://uri => NO CACHE
            if ng.http_uri.find("/dummy/") >= 0:
                ng.component_name = "KnockDummy"

        return ng

    def try_parse(self, buf):
        """
        Try to parse
        :param buf: Buffer
        :type buf: str
        :return Bool
        :rtype bool
        """

        # Parse the row
        ng = self.super_split(buf)
        if ng is None:
            self.line_parsed_skipped += 1
            return False

        # Go the item, lets populate the stat
        # We populate :
        # ALL
        # Server_ALL
        # Server_Compo

        key_list = list()
        key_list.append("ALL")
        key_list.append(ng.server)
        if ng.component_name and len(ng.component_name) > 0:
            key_list.append(ng.component_name)

        # Populate
        # noinspection PyTypeChecker
        self.populate_stat(key_list, ng)
        return True

    def populate_stat(self, key_list, ng):
        """
        Populate stat
        :param key_list: List of hash key
        :type key_list: list
        :param ng: Item
        :type ng: NGinxLog
        """

        for key in key_list:
            self.populate_stat_internal(key, ng)

    def populate_stat_internal(self, key, ng):
        """
        Populate stat
        :param key: Hash key
        :type key: str
        :param ng: Item
        :type ng: NGinxLog
        """

        # Register if required
        if key not in self.hash_stat:
            self.hash_stat[key] = NGinxStat()

        # Get
        stat = self.hash_stat[key]

        # Log count
        stat.logCount += 1
        if ng.up_socket != "-":
            stat.log_count_with_upstream += 1

        # Reply time (us and upstream)
        # Normal and LongPoll
        if ng.http_uri.find("conversation") > 0 and ng.up_socket.find("CompoLongPolling") > 0:
            # Long polling
            stat.ngReplyTimeMsLongPoll.populate(ng.reply_ms)
            stat.upReplyTimeMsLongPoll.populate(ng.up_http_ms)
        else:
            stat.ngReplyTimeMs.populate(ng.reply_ms)
            stat.upReplyTimeMs.populate(ng.up_http_ms)

        # Status class (us and upstream)
        self.fill_dict(stat.ng_hash_statuscode_to_count, ng.http_status_class, 1, "sum")
        if ng.up_socket != "-":
            self.fill_dict(stat.up_hash_statuscode_to_count, ng.up_http_statuscode_class, 1, "sum")

        # =================
        # Cache
        # =================

        # upstcache=MISS
        # upstcache=HIT
        # upstcache=- => Cache disabled
        # Need :
        # - % cache hit (request count %)
        # - % bytes hit (total bytes send %)
        # => Log count : we have the request count

        # Request count
        stat.request_cache_totalcount += 1

        # Bytes sent
        stat.request_cache_byte_totalsent += ng.http_sent_bytes

        # Cache request
        if ng.up_http_cache == "-":
            stat.request_cache_nocache += 1
            stat.request_cache_byte_nocache += ng.http_sent_bytes
        elif ng.up_http_cache == "MISS":
            stat.request_cache_miss += 1
            stat.request_cache_byte_miss += ng.http_sent_bytes
        elif ng.up_http_cache == "HIT":
            stat.request_cache_hit += 1
            stat.request_cache_byte_hit += ng.http_sent_bytes

    def populate_counters(self):
        """
        Populate counters
        """

        # ===================
        # DISCO KEY
        # ===================

        # Dict
        self.notify_discovery_n("k.nglog.discovery", {"NGLOG": "ALL"})
        for key in self.hash_stat.keys():
            self.notify_discovery_n("k.nglog.discovery", {"NGLOG": key})

        # ===================
        # DATA (ALL only)
        # ===================

        # Stats : line
        self.notify_key_value("k.nglog.line_parsed", {"NGLOG": "ALL"}, self.line_parsed)
        self.notify_key_value("k.nglog.line_parsed_ok", {"NGLOG": "ALL"}, self.line_parsed_ok)
        self.notify_key_value("k.nglog.line_parsed_failed", {"NGLOG": "ALL"}, self.line_parsed_failed)
        self.notify_key_value("k.nglog.line_parsed_skipped", {"NGLOG": "ALL"}, self.line_parsed_skipped)

        # Last parse time
        self.notify_key_value("k.nglog.last_parse_time_ms", {"NGLOG": "ALL"}, self.last_parse_time_ms)

        # Current position, current file
        self.notify_key_value("k.nglog.file_cur_name", {"NGLOG": "ALL"}, self.file_cur_name)
        self.notify_key_value("k.nglog.file_cur_pos", {"NGLOG": "ALL"}, self.file_cur_pos)

        # ===================
        # DATA PER HASH
        # ===================

        for key, stat in self.hash_stat.iteritems():
            # Let's go...

            # Log count
            self.notify_key_value("k.nglog.log_count", {"NGLOG": key}, stat.logCount)
            self.notify_key_value("k.nglog.log_count_with_up_stream", {"NGLOG": key}, stat.log_count_with_upstream)

            # Cache hits
            total = stat.request_cache_hit + stat.request_cache_miss
            if total != 0:
                cache_hit_percent = (float(stat.request_cache_hit) / float(total)) * 100.0
            else:
                cache_hit_percent = 0.0

            total = stat.request_cache_byte_hit + stat.request_cache_byte_miss
            if total != 0:
                byte_hit_percent = (float(stat.request_cache_byte_hit) / float(total)) * 100.0
            else:
                byte_hit_percent = 0

            self.notify_key_value("k.nglog.cache_hit_percent", {"NGLOG": key}, cache_hit_percent)
            self.notify_key_value("k.nglog.byte_hit_percent", {"NGLOG": key}, byte_hit_percent)

            # Status hashes
            for status, count in stat.ng_hash_statuscode_to_count.iteritems():
                self.notify_key_value("k.nglog.ngHttpStatusCode.{0}".format(status), {"NGLOG": key}, count)

            for status, count in stat.up_hash_statuscode_to_count.iteritems():
                self.notify_key_value("k.nglog.up_http_status_code.{0}".format(status), {"NGLOG": key}, count)

            # Time to count...
            for ttcKey, ttcValue in stat.ngReplyTimeMs.getCounterDict().iteritems():
                self.notify_key_value("k.nglog.{0}".format(ttcKey), {"NGLOG": key}, ttcValue)

            for ttcKey, ttcValue in stat.upReplyTimeMs.getCounterDict().iteritems():
                self.notify_key_value("k.nglog.{0}".format(ttcKey), {"NGLOG": key}, ttcValue)

                # Time to count...
            for ttcKey, ttcValue in stat.ngReplyTimeMsLongPoll.getCounterDict().iteritems():
                self.notify_key_value("k.nglog.{0}".format(ttcKey), {"NGLOG": key}, ttcValue)

            for ttcKey, ttcValue in stat.upReplyTimeMsLongPoll.getCounterDict().iteritems():
                self.notify_key_value("k.nglog.{0}".format(ttcKey), {"NGLOG": key}, ttcValue)
