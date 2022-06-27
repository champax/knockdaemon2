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
import socket

import ujson
from pysolbase.SolBase import SolBase

logger = logging.getLogger(__name__)


class UdpClient(object):
    """
    Udp client
    """

    def __init__(self, max_udp_size=61440):
        """
        Constructor
        For max udp size, refer to internet (ie https://stackoverflow.com/questions/14993000/the-most-reliable-and-efficient-udp-packet-size)
        As we act mostly on localhost, and MTU localhost is 65536, we assume a default of 61440 (we take some margin)
        :param max_udp_size: int
        :type max_udp_size: int
        """

        self._max_udp_size = max_udp_size
        self._soc = None

    def connect(self, socket_name):
        """
        Connect
        :param socket_name: str
        :type socket_name: str
        """

        try:
            self._soc = socket.socket(socket.AF_UNIX, type=socket.SOCK_DGRAM)
            self._soc.connect(socket_name)
        except Exception as e:
            logger.warning("connect failed, ex=%s", SolBase.extostr(e))
            raise

    def disconnect(self):
        """
        Disconnect
        """

        if self._soc:
            SolBase.safe_close_socket(self._soc)
            self._soc = None

    def send_json(self, json_list):
        """
        Wrapper, use this method, see _send_json
        :param json_list: list
        :type json_list: list
        """
        return self._send_json(json_list, self.send_binary)

    def _send_json(self, json_list, send_callback):
        """
        Send json, by chunk.
        UDP is not reliable, we send one packet of maximum bytes _max_udp_size
        in order to have the server handling correctly incoming atomic UDP packets

        We expect json_list as :
        => list of list of (item, type, float)
        => IE: [ ["item", "C", 8.0], ["item2", "G", 12.0 ], ["item3", "G", 15.0 ], ["zzz1", "DTC", 5.0 ], ["zzz2", "DTC", 2001.0 ] ].

        Method assume the socket is connected and running and act as fire-and-forget.
        Any socket issue will interrupt the processing. No reconnection on the socket is performed.

        The caller is responsible of calling connect before this method and disconnect method afterward to close the socket.

        :param json_list: list
        :type json_list: list
        :param send_callback: function, present for unittest only
        :type send_callback: callable
        """

        # We pre-encode all items len (approximate) to boost up a bit the for loop
        pre_encoded_list = list()
        for cur_list in json_list:
            pre_encoded_list.append(len(ujson.dumps([cur_list], ensure_ascii=False).encode("utf8")))

        # Ok
        cur_total_len = 0
        start_idx = 0
        cur_idx = 0

        # Browse
        for cur_idx in range(0, len(json_list)):
            # Get
            cur_len = pre_encoded_list[cur_idx]

            # Check length
            if cur_total_len + cur_len > self._max_udp_size:
                # Too big, cur_idx do not fit, extract from [start_idx, cur_idx[

                # Re-encode
                b_buf = ujson.dumps(json_list[start_idx:cur_idx], ensure_ascii=False).encode("utf8")

                # Check
                if len(b_buf) > self._max_udp_size:
                    raise Exception("b_buf override (case A), len=%s, max_udp_size=%s" % (len(b_buf), self._max_udp_size))

                # Send it
                send_callback(b_buf)

                # Reset
                start_idx = cur_idx
                cur_total_len = cur_len
            else:
                # We fit, continue to buffer
                cur_total_len += cur_len

        # Last stuff
        if cur_total_len > 0:
            # Re-encode (do not forget last item, so +1)
            b_buf = ujson.dumps(json_list[start_idx:cur_idx + 1], ensure_ascii=False).encode("utf8")

            # Check
            if len(b_buf) > self._max_udp_size:
                raise Exception("b_buf override (case B), len=%s, max_udp_size=%s" % (len(b_buf), self._max_udp_size))

            # Send it
            send_callback(b_buf)

        # Over
        pass

    def send_binary(self, bin_buf):
        """
        Send binary
        :param bin_buf: bytes
        :type bin_buf: bytes
        """

        if not self._soc:
            raise Exception("No socket")

        try:
            self._soc.sendall(bin_buf)
        except Exception as e:
            logger.warning("send failed, ex=%s", SolBase.extostr(e))
            raise
