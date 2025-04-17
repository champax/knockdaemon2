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

import fcntl
import glob
import logging
import os
import struct
from socket import AF_INET
from socket import socket, SOCK_DGRAM

from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Network(KnockProbe):
    """
    Doc
    """

    SUPPORTED_TYPES = dict({
        1: "Ethernet",
        32: "InfiniBand",
        512: "PPP",
        768: "IPIP tunnel",
        772: "LoopBack",
        776: "sit device - IPv6-in-IPv4",
        778: "GRE over IP",
        801: "Wlan IEEE 802.11",
        823: "GRE over IPv6"
    })

    AR_INTF_ALWAYS_UP = (776, 772, 768)

    def __init__(self):
        """
        Init
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.category = "/os/network"

    @classmethod
    def get_interface_status_from_socket(cls, interface_name):
        """
        Get interface status from socket
        :param interface_name:str
        :type interface_name: str
        :return: str ("down" or "up", depending on UP bit)
        :rtype str
        """

        siocgifflags = 0x8913
        null256 = "\0" * 256

        # Get the interface name from the command line
        # ifname = "lfdso"

        # Create a socket so we have a handle to query
        s = None
        try:
            s = socket(AF_INET, SOCK_DGRAM)

            # Call ioctl(  ) to get the flags for the given interface
            result = fcntl.ioctl(s.fileno(), siocgifflags, interface_name + null256)

            # Extract the interface's flags from the return value
            flags, = struct.unpack("H", result[16:18])

            # Check "UP" bit and print a message
            up = flags & 1
            s.close()
            return ("down", "up")[up]
        finally:
            if s is not None:
                s.close()

    @classmethod
    def try_read(cls, file_name, default=None):
        """
        Try read a file
        :param file_name: str
        :type file_name: str
        :param default: None,str
        :type default: None,str
        :return: str,None
        :rtype str,None
        """

        try:
            with open(file_name, "r") as f:
                s = f.read().strip()
                if len(s) == 0:
                    return default
                else:
                    return s
        except Exception as e:
            logger.debug("Exception reading file_name=%s, ex=%s", file_name, SolBase.extostr(e))
            return default

    def _execute_linux(self):
        """
        Exec
        """

        try:
            interfaces = glob.glob("/sys/class/net/*")
            for interface_dir in interfaces:

                # Non physical interface
                if not os.path.islink(interface_dir):
                    continue

                # GET : name
                interface_name = os.path.basename(interface_dir)

                # READ : /type
                n_local_type = int(self.try_read(interface_dir + "/type", default=-1))

                # READ : operstate
                operstate = self.try_read(interface_dir + "/operstate", default="")

                # READ : address
                address = self.try_read(interface_dir + "/address", default=None)

                # READ : carrier
                carrier = self.try_read(interface_dir + "/carrier", default=None)

                # READ : rx_bytes / tx_bytes
                recv = int(self.try_read(interface_dir + "/statistics/rx_bytes", default=0))
                sent = int(self.try_read(interface_dir + "/statistics/tx_bytes", default=0))

                # READ : duplex
                duplex = self.try_read(interface_dir + "/duplex", default="full")

                # READ : speed
                speed = int(self.try_read(interface_dir + "/speed", default="1000"))

                # READ : mtu
                mtu = int(self.try_read(interface_dir + "/mtu", default="0"))

                # READ : tx_queue_len
                tx_queue_len = int(self.try_read(interface_dir + "/tx_queue_len", default="0"))

                # READ : statistics
                rx_errors = int(self.try_read(interface_dir + "/statistics/rx_errors", default="0"))
                tx_errors = int(self.try_read(interface_dir + "/statistics/tx_errors", default="0"))
                rx_packets = int(self.try_read(interface_dir + "/statistics/rx_packets", default="0"))
                tx_packets = int(self.try_read(interface_dir + "/statistics/tx_packets", default="0"))
                rx_dropped = int(self.try_read(interface_dir + "/statistics/rx_dropped", default="0"))
                tx_dropped = int(self.try_read(interface_dir + "/statistics/tx_dropped", default="0"))
                collisions = int(self.try_read(interface_dir + "/statistics/collisions", default="0"))
                rx_missed_errors = int(self.try_read(interface_dir + "/statistics/rx_missed_errors", default="0"))

                # READ VIA SOCKET if not UP
                if operstate != "up":
                    operstate = self.get_interface_status_from_socket(interface_name)

                # PROCESS IT
                self.process_interface_from_datas(
                    interface_name=interface_name,
                    carrier=carrier,
                    n_local_type=n_local_type,
                    address=address,
                    operstate=operstate,
                    speed=speed,
                    recv=recv,
                    sent=sent,
                    duplex=duplex,
                    mtu=mtu,
                    tx_queue_len=tx_queue_len,
                    rx_errors=rx_errors, tx_errors=tx_errors,
                    rx_missed_errors=rx_missed_errors,
                    rx_packets=rx_packets, tx_packets=tx_packets,
                    rx_dropped=rx_dropped, tx_dropped=tx_dropped,
                    collisions=collisions,
                )
        except Exception as e:
            logger.warning("Ex=%s", SolBase.extostr(e))

    def process_interface_from_datas(
            self,
            interface_name,
            carrier,
            n_local_type,
            address,
            operstate,
            speed,
            recv,
            sent,
            duplex,
            mtu,
            tx_queue_len,
            rx_errors, tx_errors,
            rx_missed_errors,
            rx_packets, tx_packets,
            rx_dropped, tx_dropped,
            collisions
    ):
        """
        Process interface from datas
        :param interface_name: str
        :type interface_name: str
        :param carrier: str
        :type collisions: str
        :param n_local_type: int
        :type n_local_type: int
        :param address: str
        :type address: str
        :param operstate: str
        :type operstate: str
        :param speed: int
        :type speed: int
        :param recv: int
        :type recv: int
        :param sent: int
        :type sent: int
        :param duplex: str
        :type duplex: str
        :param mtu: int
        :type mtu: int
        :param tx_queue_len: int
        :type tx_queue_len: int
        :param rx_errors: int
        :type rx_errors: int
        :param tx_errors: int
        :type tx_errors: int
        :param rx_missed_errors: int
        :type rx_missed_errors: int
        :param rx_packets: int
        :type rx_packets: int
        :param tx_packets: int
        :type tx_packets: int
        :param rx_dropped: int
        :type rx_dropped: int
        :param tx_dropped: int
        :type tx_dropped: int
        :param collisions: int
        :type collisions: int
        """

        # -------------------------
        # CHECK TYPE
        if n_local_type not in self.SUPPORTED_TYPES:
            return

        # -------------------------
        # DETECT : effective_carrier
        if carrier is None:
            effective_carrier = "0"
        elif n_local_type == 776:
            if address is None:
                effective_carrier = "0"
            elif address == "00:00:00:00":
                # IPv6-in-IPv4 : bypass
                return
            else:
                effective_carrier = "1"
        else:
            effective_carrier = carrier

        # -------------------------
        # CHECK IF WE PROCESS

        # Interface tunnel / loopback
        if n_local_type in self.AR_INTF_ALWAYS_UP:
            self.notify_value_n("k.net.if.status.status", {"IFNAME": interface_name}, "ok")
        # GRE Unknown status is normal
        elif n_local_type == 778 and operstate == "unknown":
            self.notify_value_n("k.net.if.status.status", {"IFNAME": interface_name}, "ok")
        # 769 IP IP6 Unknown status is normal
        elif n_local_type == 776 and operstate == "unknown":
            self.notify_value_n("k.net.if.status.status", {"IFNAME": interface_name}, "ok")
        # Down
        elif operstate == "down":
            self.notify_value_n("k.net.if.status.status", {"IFNAME": interface_name}, "oper down")
            return
        # Up
        elif operstate == "up":
            self.notify_value_n("k.net.if.status.status", {"IFNAME": interface_name}, "ok")
        # Unlink
        elif effective_carrier != "1":
            self.notify_value_n("k.net.if.status.status", {"IFNAME": interface_name}, "Network unlink, please check cable")
            return
        # Ok
        else:
            self.notify_value_n("k.net.if.status.status", {"IFNAME": interface_name}, "ok")

        # -------------------------
        # PROCESS IT
        if n_local_type == 776:
            self.notify_value_n("k.net.if.status.speed", {"IFNAME": interface_name}, 1000)
        else:
            self.notify_value_n("k.net.if.status.speed", {"IFNAME": interface_name}, speed)
        self.notify_value_n("k.eth.bytes.recv", {"IFNAME": interface_name}, recv)
        self.notify_value_n("k.eth.bytes.sent", {"IFNAME": interface_name}, sent)
        self.notify_value_n("k.net.if.status.duplex", {"IFNAME": interface_name}, duplex)
        self.notify_value_n("k.net.if.type", {"IFNAME": interface_name}, self.SUPPORTED_TYPES[n_local_type])
        self.notify_value_n("k.net.if.status.mtu", {"IFNAME": interface_name}, mtu)
        self.notify_value_n("k.net.if.status.tx_queue_len", {"IFNAME": interface_name}, tx_queue_len)
        self.notify_value_n("k.eth.errors.recv", {"IFNAME": interface_name}, rx_errors)
        self.notify_value_n("k.eth.errors.sent", {"IFNAME": interface_name}, tx_errors)
        self.notify_value_n("k.eth.missederrors.recv", {"IFNAME": interface_name}, rx_missed_errors)
        self.notify_value_n("k.eth.packet.recv", {"IFNAME": interface_name}, rx_packets)
        self.notify_value_n("k.eth.packet.sent", {"IFNAME": interface_name}, tx_packets)
        self.notify_value_n("k.eth.packetdrop.recv", {"IFNAME": interface_name}, rx_dropped)
        self.notify_value_n("k.eth.packetdrop.sent", {"IFNAME": interface_name}, tx_dropped)
        self.notify_value_n("k.net.if.collisions", {"IFNAME": interface_name}, collisions)
