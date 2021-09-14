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
        '01': 'ESTABLISHED',
        '02': 'SYN_SENT',
        '03': 'SYN_RECV',
        '04': 'FIN_WAIT1',
        '05': 'FIN_WAIT2',
        '06': 'TIME_WAIT',
        '07': 'CLOSE',
        '08': 'CLOSE_WAIT',
        '09': 'LAST_ACK',
        '0A': 'LISTEN',
        '0B': 'CLOSING'
    }

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.counter = dict()
        self.pinghost = None
        self.ping_host = None

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

        # Go
        self.ping_host = d["ping_target_server"]

    def _execute_linux(self):
        """
        Exec
        """
        content = self._load()
        self.counter = dict()
        for line in content:
            line_array = self._remove_empty(line.split(' '))  # Split lines and remove empty space.
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

        # parse connection Tracker
        try:
            nf_conntrack_count = float(open('/proc/sys/net/netfilter/nf_conntrack_count').readline())
            nf_conntrack_max = float(open('/proc/sys/net/netfilter/nf_conntrack_max').readline())
            self.notify_value_n("k.net.conntrack.count", None, nf_conntrack_count)
            self.notify_value_n("k.net.conntrack.max", None, nf_conntrack_max)
            # Ration
            self.notify_value_n("k.net.conntrack.used", None, 100.0 * nf_conntrack_count / nf_conntrack_max)

        except Exception as e:
            logger.warning(SolBase.extostr(e))

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

    def _load(self):
        """
        Read the table of tcp connections & remove header
        """
        with open(self.PROC_TCP, 'r') as f:
            content = f.readlines()
            content.pop(0)
        return content

    # noinspection PyMethodMayBeStatic
    def _remove_empty(self, array):
        """
        Doc
        :param array:
        :return:
        """
        return [x for x in array if x != '']
