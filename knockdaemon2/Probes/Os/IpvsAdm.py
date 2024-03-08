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
import logging
import os
import re
import socket
import struct

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class IpvsAdm(KnockProbe):
    """
    Doc
    """

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self)

        self._agregate = None
        self._rootkey = None

        self.category = "/web/ipvsadm"

    def _execute_linux(self):
        """
        Execute
        """

        # Load
        buf = self.get_ipvsadm_buffer("/proc/net/ip_vs")

        # Process
        self.process_ipvsadm_buffer(buf)

    def process_ipvsadm_buffer(self, buf):
        """
        Process
        :param buf: str
        :type buf: str
        """

        # Reset
        self._agregate = dict()

        # Parse
        hashtab, resulttab = self.parse_ipvsadm_buffer(buf)

        # Check
        if not hashtab:
            logger.debug('keepalive stopped')
            return

        for key, value in hashtab.items():
            self._push_result("k.os.ipvsadm.activerip", key, value=value)

        for key, value in resulttab.items():
            vip, key = key.split('_')
            self._push_result("k.os.ipvsadm." + key, vip, value=value)

        self._send_all_result()

    @classmethod
    def get_ipvsadm_buffer(cls, file_name):
        """
        Get buffer
        :param file_name: str
        :type file_name: str
        :return: str,None
        :rtype str,None
        """
        if not os.path.isfile(file_name):
            return None
        with open(file_name, "r") as f:
            return f.read()

    def parse_ipvsadm_buffer(self, buf):
        """
        Process buffer
        :param buf: str,None
        :type buf: str,None
        :return tuple bool,bool
        :rtype tuple
        """
        # MASK
        vip_exp = r"^...\s+([0-9A-F]{8}):([0-9A-F]{4}).*$"
        rip_exp = r"^\s*->\s([0-9A-F]{8}):([0-9A-F]{4})\s{6}[A-Za-z]+\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)$"

        hashtab = dict()
        resulttab = dict()
        rip = ''
        portrip = ''
        weight_rip = ''
        active_con_rip = ''
        in_act_conn_rip = ''

        if buf is None or len(buf) == 0:
            return False, False

        vip = None
        portvip = None
        for line in buf.split("\n"):
            line = line.strip()
            # vip
            # TCP  256EC116:01BB rr
            # rip
            # -> 0A000A02:0050      Route   1      0          1

            matchvip = re.search(vip_exp, line.strip())
            if matchvip is not None:
                type_line = "vip"
                vip = self._hex2ip(matchvip.group(1))
                portvip = self._hex2port(matchvip.group(2))
                hashtab[vip + ':' + str(portvip)] = ""
                resulttab[vip + ':' + str(portvip) + '_weightRip'] = 0
                resulttab[vip + ':' + str(portvip) + '_activeConRip'] = 0
                resulttab[vip + ':' + str(portvip) + '_InActConnRip'] = 0
            else:
                matchrip = re.search(rip_exp, line.strip())
                if matchrip is not None:
                    type_line = "rip"
                    rip = self._hex2ip(matchrip.group(1))
                    portrip = self._hex2port(matchrip.group(2))
                    weight_rip = int(matchrip.group(3))
                    active_con_rip = int(matchrip.group(4))
                    in_act_conn_rip = int(matchrip.group(5))
                else:
                    type_line = "info"

            if type_line == "rip":
                if (len(hashtab[vip + ':' + str(portvip)])) > 0:
                    hashtab[vip + ':' + str(portvip)] = rip + ':' + str(portrip) + " - " + hashtab[vip + ':' + str(portvip)]
                else:
                    hashtab[vip + ':' + str(portvip)] = rip + ':' + str(portrip)
                resulttab[vip + ':' + str(portvip) + '_weightRip'] += weight_rip
                resulttab[vip + ':' + str(portvip) + '_activeConRip'] += active_con_rip
                resulttab[vip + ':' + str(portvip) + '_InActConnRip'] += in_act_conn_rip

        return hashtab, resulttab

    def _send_all_result(self):
        """
        Send
        """
        for key, value in self._agregate.items():
            self.notify_value_n(key, {"VIP": "ALL"}, value)

    def _push_result(self, key, id_vip, value):
        """
        Agregate all key and send local key

        :param key: str
        :type key: str
        :param id_vip: str
        :type id_vip : str
        :param value: variant
        :type value: variant
        """
        if key not in self._agregate:
            self._agregate[key] = value
        else:
            self._agregate[key] += value

        self.notify_value_n(key, {"VIP": id_vip}, value)

    @classmethod
    def _hex2ip(cls, hex_ip):
        """
        Doc
        :param hex_ip: str
        :type hex_ip: str
        :return: str
        :rtype str
        """
        return ".".join(socket.inet_ntoa(
            struct.pack("<L", int("0x" + hex_ip, 16))).split(".")[::-1])

    @classmethod
    def _hex2port(cls, s):
        """
        To port
        :param s: str
        :type s: str
        :return: int
        :rtype int
        """
        return int(s, 16)
