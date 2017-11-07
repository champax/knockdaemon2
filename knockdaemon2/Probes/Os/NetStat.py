"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac
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
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    from knockdaemon2.Windows.Helper.Netstat import get_netstat, STATES

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

    # =====================
    # WINDOWS
    # =====================

    # noinspection PyMethodMayBeStatic
    def _get_windows_count(self, ar, soc_state):
        """
        Get socket count for specified state
        :param ar: list of dict
        :type ar: list
        :param soc_state: str
        :type soc_state: str
        :return int
        :rtype int
        """

        # Validate state in STATES
        found = 0
        for k, v in STATES.iteritems():
            if v == soc_state:
                found += 1
                break
        assert found > 0, "found must be >0, got soc_state={0}".format(soc_state)

        c = 0
        for d in ar:
            if d["state"] == soc_state:
                c += 1
        return c

    def _execute_windows(self):
        """
        Windows
        """

        try:
            ms = SolBase.mscurrent()
            try:

                ar = get_netstat()
            finally:
                logger.info("get_netstat ms=%s", SolBase.msdiff(ms))

            self.notify_value_n("k.net.netstat.SYN_SENT", None, self._get_windows_count(ar, "SYN_SENT"))
            self.notify_value_n("k.net.netstat.LISTEN", None, self._get_windows_count(ar, "LISTENING"))
            self.notify_value_n("k.net.netstat.TIME_WAIT", None, self._get_windows_count(ar, "TIME_WAIT"))
            self.notify_value_n("k.net.netstat.SYN_RECV", None, self._get_windows_count(ar, "SYN_RCVD"))
            self.notify_value_n("k.net.netstat.LAST_ACK", None, self._get_windows_count(ar, "LAST_ACK"))
            self.notify_value_n("k.net.netstat.CLOSE_WAIT", None, self._get_windows_count(ar, "CLOSE_WAIT"))
            self.notify_value_n("k.net.netstat.CLOSED", None, self._get_windows_count(ar, "CLOSED"))
            self.notify_value_n("k.net.netstat.FIN_WAIT2", None, self._get_windows_count(ar, "FIN_WAIT_2"))
            self.notify_value_n("k.net.netstat.FIN_WAIT1", None, self._get_windows_count(ar, "FIN_WAIT"))
            self.notify_value_n("k.net.netstat.ESTABLISHED", None, self._get_windows_count(ar, "ESTABLISHED"))
            self.notify_value_n("k.net.netstat.CLOSING", None, self._get_windows_count(ar, "CLOSING"))
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
        finally:
            pass
