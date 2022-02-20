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

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


# noinspection PyMethodMayBeStatic
class Netstat(KnockProbe):
    """
    Doc
    """

    ICMP_ECHO_REQUEST = 8  # Seems to be the same on Solaris.

    PROC_TCP = "/proc/net/tcp"
    STATE = {
        "01": "ESTABLISHED",
        "02": "SYN_SENT",
        "03": "SYN_RECV",
        "04": "FIN_WAIT1",
        "05": "FIN_WAIT2",
        "06": "TIME_WAIT",
        "07": "CLOSE",
        "08": "CLOSE_WAIT",
        "09": "LAST_ACK",
        "0A": "LISTEN",
        "0B": "CLOSING"
    }

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.counter = dict()

        self.category = "/os/network"

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

        # Tco
        ar_tcp = self.load_proc_net_tcp()
        self.process_net_tcp_from_list(ar_tcp)

        # Conntrack
        with open("/proc/sys/net/netfilter/nf_conntrack_count") as f:
            nf_conntrack_count = float(f.readline())
        with open("/proc/sys/net/netfilter/nf_conntrack_max") as f:
            nf_conntrack_max = float(f.readline())
        self.process_conntrack(nf_conntrack_count, nf_conntrack_max)

    def process_net_tcp_from_list(self, ar_tcp):
        """
        Process tcp from buffer
        :param ar_tcp: list of str
        :type ar_tcp: list
        """
        self.counter = dict()
        for line in ar_tcp:
            line = line.strip()
            if len(line) == 0:
                continue
            line_array = self._remove_empty(line.split(" "))  # Split lines and remove empty space.
            if self.STATE[line_array[3]] in self.counter:
                self.counter[self.STATE[line_array[3]]] += 1
            else:
                self.counter[self.STATE[line_array[3]]] = 1

        self.notify_value_n("k.net.netstat.SYN_SENT", None, self._get_counter_value("SYN_SENT"))
        self.notify_value_n("k.net.netstat.LISTEN", None, self._get_counter_value("LISTEN"))
        self.notify_value_n("k.net.netstat.TIME_WAIT", None, self._get_counter_value("TIME_WAIT"))
        self.notify_value_n("k.net.netstat.SYN_RECV", None, self._get_counter_value("SYN_RECV"))
        self.notify_value_n("k.net.netstat.LAST_ACK", None, self._get_counter_value("LAST_ACK"))
        self.notify_value_n("k.net.netstat.CLOSE_WAIT", None, self._get_counter_value("CLOSE_WAIT"))
        self.notify_value_n("k.net.netstat.CLOSED", None, self._get_counter_value("CLOSED"))
        self.notify_value_n("k.net.netstat.FIN_WAIT2", None, self._get_counter_value("FIN_WAIT2"))
        self.notify_value_n("k.net.netstat.FIN_WAIT1", None, self._get_counter_value("FIN_WAIT1"))
        self.notify_value_n("k.net.netstat.ESTABLISHED", None, self._get_counter_value("ESTABLISHED"))
        self.notify_value_n("k.net.netstat.CLOSING", None, self._get_counter_value("CLOSING"))

    def process_conntrack(self, nf_conntrack_count, nf_conntrack_max):
        """
        Process conntrack
        :param nf_conntrack_count: float
        :type nf_conntrack_count: float
        :param nf_conntrack_max: float
        :type nf_conntrack_max: float
        """

        self.notify_value_n("k.net.conntrack.count", None, nf_conntrack_count)
        self.notify_value_n("k.net.conntrack.max", None, nf_conntrack_max)
        # Ratio
        self.notify_value_n("k.net.conntrack.used", None, 100.0 * nf_conntrack_count / nf_conntrack_max)

    def _get_counter_value(self, state):
        """
        Get
        :param state:
        :return:
        """
        if state in self.counter:
            return self.counter[state]
        else:
            return 0

    def load_proc_net_tcp(self):
        """
        Read the table of tcp connections & remove header
        :return list of str
        :rtype list
        """
        with open(self.PROC_TCP, "r") as f:
            content = f.readlines()
            content.pop(0)
        return content

    @classmethod
    def _remove_empty(cls, array):
        """
        Doc
        :param array: list
        :type array: list
        :return list
        :rtype list
        """
        return [x for x in array if x != ""]
