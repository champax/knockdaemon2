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

import glob
import logging
import os
import struct
from socket import AF_INET
from socket import socket, SOCK_DGRAM

from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    pass

if not PTools.get_distribution_type() == "windows":
    import fcntl

logger = logging.getLogger(__name__)


def get_interface_status(interface_name):
    """

    :param interface_name:
    :return:
    """

    siocgifflags = 0x8913
    null256 = '\0' * 256

    # Get the interface name from the command line
    # ifname = 'lfdso'

    # Create a socket so we have a handle to query
    s = socket(AF_INET, SOCK_DGRAM)

    # Call ioctl(  ) to get the flags for the given interface
    result = fcntl.ioctl(s.fileno(), siocgifflags, interface_name + null256)

    # Extract the interface's flags from the return value
    flags, = struct.unpack('H', result[16:18])

    # Check "UP" bit and print a message
    up = flags & 1
    return ('down', 'up')[up]


class Network(KnockProbe):
    """
    Doc
    """

    # Interface Type, cf:
    # noinspection PyTypeChecker
    SUPPORTED_TYPES = dict({
        1: 'Ethernet',
        32: 'InfiniBand',
        512: 'PPP',
        768: 'IPIP tunnel',
        772: 'LoopBack',
        776: 'sit device - IPv6-in-IPv4',
        778: 'GRE over IP',
        801: 'Wlan IEEE 802.11',
        823: 'GRE over IPv6'
    })
    listInterfaceAlwaysUP = (776, 772, 768)

    WIN_AVAILABILITY_TO_STRING = {
        1: "Other",
        2: "Unknown",
        3: "Running/Full Power",
        4: "Warning",
        5: "In Test",
        6: "Not Applicable",
        7: "Power Off",
        8: "Off Line",
        9: "Off Duty",
        10: "Degraded",
        11: "Not Installed",
        12: "Install Error",
        13: "Power Save - Unknown",
        14: "Power Save - Low Power Mode",
        15: "Power Save - Standby",
        16: "Power Cycle",
        17: "Power Save - Warning",
        18: "Paused",
        19: "Not Ready",
        20: "Not Configured",
        21: "Quiesced",
    }

    WIN_STATUS_TO_STRING = {
        0: "Disconnected",
        1: "Connecting",
        2: "Connected",
        3: "Disconnecting",
        4: "Hardware Not Present",
        5: "Hardware Disabled",
        6: "Hardware Malfunction",
        7: "Media Disconnected",
        8: "Authenticating",
        9: "Authentication Succeeded",
        10: "Authentication Failed",
        11: "Invalid Address",
        12: "Credentials Required",
    }

    def __init__(self):
        """
        Init
        """

        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.category = "/os/network"

    def _execute_linux(self):
        """
        Exec
        """

        try:
            interfaces = glob.glob('/sys/class/net/*')

            for interface in interfaces:

                if not os.path.islink(interface):
                    # Non physical interface
                    continue

                # noinspection PyBroadException
                local_type = None
                try:
                    local_type = int(open(interface + '/type', 'r').read().strip())
                except Exception as ex:
                    logger.warning("Ex=%s", SolBase.extostr(ex))

                if local_type not in self.SUPPORTED_TYPES:
                    continue

                interface_name = os.path.basename(interface)

                d_in = interface_name

                # Status interface
                operstate = ""

                try:
                    operstate = open(interface + "/operstate", "r").read().strip()

                except Exception as e:
                    logger.warning(SolBase.extostr(e))

                try:
                    # if  IPv6-in-IPv4
                    if local_type == 776:
                        if open(interface + "/address", "r").read().strip() == "00:00:00:00":
                            continue
                        else:
                            carrier = "1"
                    else:
                        carrier = open(interface + "/carrier", "r").read().strip()
                except IOError:
                    carrier = "0"
                except Exception as e:
                    logger.warning("interface %s: %s", interface, SolBase.extostr(e))
                    carrier = "0"

                # Interface tunnel / loopback
                if local_type in self.listInterfaceAlwaysUP:
                    status = True
                    self.notify_value_n("k.net.if.status.status", {"IFNAME": d_in}, "ok")
                # GRE Unknown status is normal
                elif local_type == 778 and operstate == "unknown":
                    status = True
                    self.notify_value_n("k.net.if.status.status", {"IFNAME": d_in}, "ok")
                # 769 IP IP6 Unknown status is normal
                elif local_type == 776 and operstate == "unknown":
                    status = True
                    self.notify_value_n("k.net.if.status.status", {"IFNAME": d_in}, "ok")
                elif operstate != "up":
                    operstate = get_interface_status(interface_name)
                    if operstate == "down":
                        self.notify_value_n("k.net.if.status.status", {"IFNAME": d_in}, "oper down")
                        status = False
                    else:
                        status = True
                        self.notify_value_n("k.net.if.status.status", {"IFNAME": d_in}, "ok")
                elif carrier != "1":
                    self.notify_value_n("k.net.if.status.status", {"IFNAME": d_in}, "Network unlink, please check cable")
                    status = False
                else:
                    status = True
                    self.notify_value_n("k.net.if.status.status", {"IFNAME": d_in}, "ok")

                # Status interface
                # disable counter interface if interface is down
                if not status:
                    continue
                recv = int(open(interface + "/statistics/rx_bytes", "r").read().strip())
                sent = int(open(interface + "/statistics/tx_bytes", "r").read().strip())
                self.notify_value_n("k.eth.bytes.recv", {"IFNAME": d_in}, recv)
                self.notify_value_n("k.eth.bytes.sent", {"IFNAME": d_in}, sent)

                try:
                    duplex = open(interface + "/duplex", "r").read().strip()
                except IOError:
                    duplex = "full"
                try:
                    speed = int(open(interface + "/speed", "r").read().strip())
                except IOError:
                    speed = "1000"

                self.notify_value_n("k.net.if.status.duplex", {"IFNAME": d_in}, duplex)
                if local_type == 776:
                    self.notify_value_n("k.net.if.status.speed", {"IFNAME": d_in}, 1000)
                else:
                    self.notify_value_n("k.net.if.status.speed", {"IFNAME": d_in}, int(speed))
                self.notify_value_n("k.net.if.type", {"IFNAME": d_in}, self.SUPPORTED_TYPES[local_type])
                self.notify_value_n("k.net.if.status.mtu", {"IFNAME": d_in}, int(open(interface + "/mtu", "r").read().strip()))
                # self.notify_value_n("k.net.if.status.address", {"IFNAME": d_in}, open(interface + "/address", "r").read().strip())
                self.notify_value_n("k.net.if.status.tx_queue_len", {"IFNAME": d_in}, int(open(interface + "/tx_queue_len", "r").read().strip()))
                self.notify_value_n("k.eth.errors.recv", {"IFNAME": d_in}, int(open(interface + "/statistics/rx_errors", "r").read().strip()))
                self.notify_value_n("k.eth.errors.sent", {"IFNAME": d_in}, int(open(interface + "/statistics/tx_errors", "r").read().strip()))
                self.notify_value_n("k.eth.missederrors.recv", {"IFNAME": d_in}, int(open(interface + "/statistics/rx_missed_errors", "r").read().strip()))
                self.notify_value_n("k.eth.packet.recv", {"IFNAME": d_in}, int(open(interface + "/statistics/rx_packets", "r").read().strip()))
                self.notify_value_n("k.eth.packet.sent", {"IFNAME": d_in}, int(open(interface + "/statistics/tx_packets", "r").read().strip()))
                self.notify_value_n("k.eth.packetdrop.recv", {"IFNAME": d_in}, int(open(interface + "/statistics/rx_dropped", "r").read().strip()))
                self.notify_value_n("k.eth.packetdrop.sent", {"IFNAME": d_in}, int(open(interface + "/statistics/tx_dropped", "r").read().strip()))
                self.notify_value_n("k.net.if.collisions", {"IFNAME": d_in}, int(open(interface + "/statistics/collisions", "r").read().strip()))

        except Exception as e:
            logger.warning("Exception=%s", SolBase.extostr(e))

    # noinspection PyMethodMayBeStatic
    def _get_adapter_perf(self, d_wmi, a_name):
        """
        Get adapter perf using name
        :param d_wmi: dict
        :type d_wmi: dict
        :param a_name: str
        :type a_name: str
        :return dict,None
        :rtype dict,None
        """

        for d in d_wmi["Win32_PerfRawData_Tcpip_NetworkInterface"]:
            if d["Name"] == a_name:
                return d
        return None
