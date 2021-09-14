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
    from knockdaemon2.Windows.Wmi.Wmi import Wmi

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
                try:
                    local_type = int(open(interface + '/type', 'r').read().strip())
                except Exception as ex:
                    logger.warn("Ex=%s", SolBase.extostr(ex))

                if local_type not in self.SUPPORTED_TYPES:
                    continue

                interface_name = os.path.basename(interface)

                d_in = interface_name

                # Disco
                self.notify_discovery_n("k.net.if.discovery", {"IFNAME": d_in})

                # Status interface
                operstate = ""

                try:
                    operstate = open(interface + "/operstate", "r").read().strip()

                except Exception as e:
                    logger.warn(SolBase.extostr(e))

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
                    logger.warn("interface %s: %s", interface, SolBase.extostr(e))
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
            logger.warn("Exception=%s", SolBase.extostr(e))

    # noinspection PyMethodMayBeStatic
    def _get_adapter_perf(self, d_wmi, a_name):
        """
        Get adapter perf using name
        :param d_wmi: dict
        :type d_wmi: dict
        :param a_name: str,unicode
        :type a_name: str,unicode
        :return dict,None
        :rtype dict,None
        """

        for d in d_wmi["Win32_PerfRawData_Tcpip_NetworkInterface"]:
            if d["Name"] == a_name:
                return d
        return None

    def _execute_windows(self):
        """
        Windows         
        """

        d = None
        try:
            d, age_ms = Wmi.wmi_get_dict()
            logger.info("Using wmi with age_ms=%s", age_ms)

            # k.net.if.status[eth0,status] = 'ok'
            # k.net.if.status[eth0,duplex] = 'full'
            # k.net.if.type[eth0] = 'Ethernet'
            # k.net.if.status[eth0,address] = '02:00:00:d7:ac:18'

            # k.net.if.status[eth0,speed] = '1000'

            # k.eth.bytes.recv[eth0] = 81746282371
            # k.eth.bytes.sent[eth0] = 121116445003
            # k.net.if.status[eth0,mtu] = 1500
            # k.net.if.status[eth0,tx_queue_len] = 1000
            # k.eth.errors.recv[eth0] = 0
            # k.eth.errors.sent[eth0] = 0
            # k.eth.missederrors.recv[eth0] = 0
            # k.eth.packet.recv[eth0] = 1099537831
            # k.eth.packet.sent[eth0] = 162656888
            # k.eth.packetdrop.recv[eth0] = 0
            # k.eth.packetdrop.sent[eth0] = 0
            # k.net.if.collisions[eth0] = 0

            # Browse network adapters
            for d_na in d["Win32_NetworkAdapter"]:
                na_cid = d_na.get("NetConnectionID", None)
                na_name = d_na.get("Name", None)
                na_status = d_na.get("NetConnectionStatus", None)
                na_enabled = d_na.get("NetEnabled", False)
                na_physical = d_na.get("PhysicalAdapter", False)
                na_speed = d_na.get("Speed", None)
                na_installed = d_na.get("Installed", False)
                na_availability = d_na.get("Availability", None)
                na_did = d_na["DeviceID"]
                na_desc = d_na.get("Description", "")
                na_mac = d_na.get("MACAddress", None)
                na_type = d_na.get("AdapterType", None)

                na_availability_str = Network.WIN_AVAILABILITY_TO_STRING.get(na_availability if na_availability else -1, "dunno")
                na_status_str = Network.WIN_STATUS_TO_STRING.get(na_status if na_status else -1, "dunno")

                logger.info("Processing did=%s, cid=%s, name=%s, desc=%s, mac=%s, type=%s", na_did, na_cid, na_name, na_desc, na_mac, na_type)
                logger.info("Processing did=%s, name=%s, status=%s(%s) , en=%s, phys=%s, inst=%s, av=%s(%s), speed=%s",
                            na_did, na_cid,
                            na_status, na_status_str,
                            na_enabled, na_physical, na_installed,
                            na_availability, na_availability_str,
                            na_speed
                            )

                # If not enabled, bypass
                if not na_enabled:
                    logger.info("Bypass (not enabled), did=%s", na_did)
                    continue

                # This one is enabled and must work... get stats
                # Using name (zzz)
                logger.info("Fetching perf using name=%s", na_name)
                d_raw_perf = self._get_adapter_perf(d, na_name)
                if not d_raw_perf:
                    logger.warn("Unable to fetch perf (bypass), name=%s", na_name)
                    continue

                # Ok, so... we are using NetConnectionID as discovery name
                dd = na_cid
                logger.info("Fetched perf, engaging using disco=%s", dd)
                d_stat = dict()

                # ----------------
                # Status
                # ----------------
                if na_status == 2:
                    # Connected
                    d_stat["k.net.if.status.status"] = "ok"
                else:
                    # Other
                    d_stat["k.net.if.status.status"] = na_status_str

                # ----------------
                # Duplex : not wmi supported (zzz), fallback full
                # ----------------
                d_stat["k.net.if.status.duplex"] = "full"

                # ----------------
                # Direct
                # ----------------
                d_stat["k.net.if.type"] = na_type
                # d_stat["k.net.if.status.address"] = na_mac
                d_stat["k.net.if.status.speed"] = int(int(na_speed) / 1000 / 1000)

                # ----------------
                # STATS
                # ----------------

                # k.net.if.status[eth0,mtu] = 1500

                # k.eth.bytes.recv[eth0] = 81746282371
                # k.eth.bytes.sent[eth0] = 121116445003

                # k.net.if.status[eth0,tx_queue_len] = 1000
                # k.eth.errors.recv[eth0] = 0
                # k.eth.errors.sent[eth0] = 0
                # k.eth.missederrors.recv[eth0] = 0
                # k.eth.packet.recv[eth0] = 1099537831
                # k.eth.packet.sent[eth0] = 162656888
                # k.eth.packetdrop.recv[eth0] = 0
                # k.eth.packetdrop.sent[eth0] = 0
                # k.net.if.collisions[eth0] = 0

                for k_stat, d_w, w_key, w_default in [
                    ["k.net.if.status.mtu", None, "bypass", 0],  # MTU may be available from Win32_NetworkAdapterConfiguration :: MTU (but its presence is not guarantee)

                    ["k.eth.bytes.recv", d_raw_perf, "BytesReceivedPersec", 0],  # OK
                    ["k.eth.bytes.sent", d_raw_perf, "BytesSentPersec", 0],  # OK

                    ["k.eth.packet.recv", d_raw_perf, "PacketsReceivedPersec", 0],  # OK
                    ["k.eth.packet.sent", d_raw_perf, "PacketsSentPersec", 0],  # OK

                    ["k.eth.errors.recv", d_raw_perf, "bypass", 0],  # No support
                    ["k.eth.errors.sent", d_raw_perf, "bypass", 0],  # No support

                    ["k.eth.packetdrop.recv", d_raw_perf, ["PacketsReceivedErrors",  # number of inbound packets that contained errors preventing them from being deliverable to a higher-layer protocol
                                                           "PacketsReceivedUnknown "], 0],  # number of packets received through the interface that were discarded because of an unknown or unsupported protocol
                    ["k.eth.packetdrop.sent", d_raw_perf, "PacketsOutboundErrors", 0],  # number of outbound packets that could not be transmitted because of errors

                    ["k.eth.missederrors.recv", d_raw_perf, "bypass", 0],  # No support

                    ["k.net.if.status.tx_queue_len", d_raw_perf, "bypass", 0],  # No support
                    ["k.net.if.collisions", d_raw_perf, "bypass", 0],  # No support
                ]:

                    # ----------------
                    # FETCH STAT
                    # ----------------
                    if isinstance(w_key, (str, unicode)):
                        if w_key == "bypass":
                            d_stat[k_stat] = w_default
                            continue
                        else:
                            d_stat[k_stat] = int(d_raw_perf.get(w_key, w_default))
                    elif isinstance(w_key, (tuple, list)):
                        d_stat[k_stat] = 0
                        for k2 in w_key:
                            d_stat[k_stat] += int(d_raw_perf.get(k2, w_default))

                # ----------------
                # LOG
                # ----------------
                for k, v in d_stat.iteritems():
                    logger.info("Got %s=%s", k, v)

                # ----------------
                # Disco
                # ----------------
                self.notify_discovery_n("k.net.if.discovery", {"IFNAME": dd})

                # ----------------
                # NOTIFY
                # ----------------
                for k, v in d_stat.iteritems():
                    self.notify_value_n(k, {"IFNAME": dd}, v)

        except Exception as e:
            logger.warn("Exception while processing, ex=%s, d=%s", SolBase.extostr(e), d)
