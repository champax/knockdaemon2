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
import os
import re
import socket
import struct

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


# noinspection PyMethodMayBeStatic
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

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        LA DOC PD DU FION
        :return:
        """
        self._agregate = dict()

        hashtab, resulttab = self._parse()

        if not hashtab:
            logger.debug('keepalive stopped')
            return

        self.notify_discovery_n("knock.ipvsadm.discovery", {"VIP": "ALL"})

        for key, value in hashtab.iteritems():
            self.notify_discovery_n("knock.ipvsadm.discovery", {"VIP": key})
            self._push_result("knock.ipvsadm.activerip", key, value=value)

        for key, value in resulttab.iteritems():
            vip, key = key.split('_')
            self._push_result("knock.ipvsadm." + key, vip, value=value)

        self._send_all_result()

    def _parse(self, file_ip_vs='/proc/net/ip_vs'):
        """
        to test file_ip_vs = 'knock/ip_vs'
        """
        # MASK
        vip_exp = "^...\s+([0-9A-F]{8}):([0-9A-F]{4}).*$"
        rip_exp = \
            "^\s*->\s([0-9A-F]{8}):([0-9A-F]{4})\s{6}[A-Za-z]+\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)$"

        hashtab = dict()
        resulttab = dict()
        rip = ''
        portrip = ''
        weight_rip = ''
        active_con_rip = ''
        in_act_conn_rip = ''

        if not os.path.isfile(file_ip_vs):
            return False, False

        for line in file(file_ip_vs):
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
                hashtab[vip + ':' + str(portvip)] = "-".join(
                    rip + ':' + str(portrip) + hashtab[vip + ':' + str(portvip)])
                resulttab[vip + ':' + str(portvip) + '_weightRip'] += weight_rip
                resulttab[vip + ':' + str(portvip) + '_activeConRip'] += active_con_rip
                resulttab[vip + ':' + str(portvip) + '_InActConnRip'] += in_act_conn_rip

        return hashtab, resulttab

    def _send_all_result(self):
        """
        Send
        """
        for key, value in self._agregate.iteritems():
            self.notify_value_n(key, {"VIP": "ALL"}, value)

    def _push_result(self, key, id_vip, value):
        """
        Agregate all key and send local key

        :param key:
        :type key : str
        :param id_vip:
        :type id_vip : str
        :param value:
        :type value: variant
        """
        if key not in self._agregate:
            self._agregate[key] = value
        else:
            self._agregate[key] += value

        self.notify_value_n(key, id_vip, value)

    def _hex2ip(self, hex_ip):
        """
        Doc
        :param hex_ip:
        :return:
        """
        return ".".join(socket.inet_ntoa(
            struct.pack("<L", int("0x" + hex_ip, 16))).split(".")[::-1])

    def _hex2port(self, s):
        """
        Doc
        :param s:
        :return:
        """
        return int(s, 16)
