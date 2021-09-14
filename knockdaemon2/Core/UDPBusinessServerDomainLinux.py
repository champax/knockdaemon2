"""
-*- coding: utf-8 -*-
===============================================================================

Copyright (C) 2013/2021 Laurent Labatut / Laurent Champagnac



 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2
 of the License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 ===============================================================================
"""
import logging
import os
import socket

from pysolbase.SolBase import SolBase

from knockdaemon2.Core.UDPBusinessServerBase import UDPBusinessServerBase
from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)


class UDPBusinessServerDomainLinux(UDPBusinessServerBase):
    """
    Business server
    """

    COUNTER = 'C'
    GAUGE = 'G'
    DTC = 'DTC'
    KNOCK_PREFIX_KEY = 'k.business.'

    def __init__(self, manager, socket_name, ip_host, ip_port, send_back_udp, notify_interval_ms, *args, **kwargs):
        """
        Init
        :param manager: KnockManager
        :type manager: KnockManager
        :param send_back_udp: bool
        :type send_back_udp: bool
        :param notify_interval_ms: int
        :param notify_interval_ms: int
        :param socket_name: str
        :type socket_name: str
        :param ip_host: str
        :type ip_host: str
        :param ip_port: int
        :type ip_port: int
        :param args:
        :param kwargs:
        """

        # Call base
        super(UDPBusinessServerDomainLinux, self).__init__(manager, socket_name, ip_host, ip_port, send_back_udp, notify_interval_ms, *args, **kwargs)

    def _create_socket_and_bind(self):
        """
        Create socket
        """

        if self._soc:
            logger.info("Bypass, _soc set")
            return

        # Listen
        logger.info("Binding")

        # Alloc
        if PTools.get_distribution_type() == "windows":
            # ==========================
            # Ahah, no support for domain socket on Windows
            # ==========================
            logger.warning("Windows detected, discarding domain linux socket listening. You may move to linux, it rocks.")
            return

        # ==========================
        # Linux rocks (and debian rocks more)
        # ==========================

        # noinspection PyUnresolvedReferences
        self._soc = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        if os.path.exists(self._socket_name):
            os.remove(self._socket_name)

        # Switch to non blocking
        self._soc.setblocking(False)

        # Bind
        self._soc.bind(self._socket_name)

        # Buffer
        logger.info("Recv buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
        logger.info("Send buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))

        # Increase recv
        try:
            self._soc.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 1024)
        except Exception as e:
            logger.info("SO_RCVBUF increased failed, ex=%s", SolBase.extostr(e))

        # Buffer
        logger.info("Recv buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
        logger.info("Send buf=%s", self._soc.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))
