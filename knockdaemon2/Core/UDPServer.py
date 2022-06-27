"""
-*- coding: utf-8 -*-
===============================================================================

Copyright (C) 2013/2022 Laurent Labatut / Laurent Champagnac



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

from gevent.pool import Pool

from knockdaemon2.Core.UDPBusinessServerDomainLinux import UDPBusinessServerDomainLinux
from knockdaemon2.Core.UDPBusinessServerIpPort import UDPBusinessServerIpPort

logger = logging.getLogger(__name__)


class UDPServer(object):
    """
    UDP server
    """

    # --------------------------
    # UNIX DOMAIN SOCKET
    # --------------------------
    UDP_SOCKET_NAME = "/var/run/knockdaemon2.udp.socket"
    UDP_UNITTEST_SOCKET_NAME = "/tmp/knockdaemon2.udp.socket"

    # --------------------------
    # IP SOCKET
    # --------------------------
    UDP_IP_SOCKET_HOST = "localhost"
    UDP_IP_SOCKET_PORT = "10040"

    UDP_IP_UNITTEST_SOCKET_HOST = "localhost"
    UDP_IP_UNITTEST_SOCKET_PORT = "63999"

    # --------------------------
    # NOTIFY
    # --------------------------
    NOTIFY_INTERVAL = 59000
    NOTIFY_UNITTEST_INTERVAL = 5000

    def __init__(self, manager, pool_size=128, socket_name=None, ip_host=None, ip_port=None, send_back_udp=False, notify_interval_ms=None):
        """
        Init
        :param manager: KnockManager
        :type manager: KnockManager
        :param pool_size: int
        :type pool_size: int
        :param socket_name: str,None
        :type socket_name: str,None
        :param ip_host: str,None
        :type ip_host: str,None
        :param ip_port: int,None
        :type ip_port: int,None
        :param send_back_udp: bool
        :type send_back_udp: bool
        :param notify_interval_ms: int,None
        :type notify_interval_ms: int,None
        """
        self._manager = manager
        self._pool = Pool(pool_size)
        self._business_server_domain_linux = None
        self._business_server_ip_port = None

        # NAME
        if socket_name:
            self._socket_name = socket_name
        else:
            # If UNITTEST, force
            if "KNOCK_UNITTEST" in os.environ:
                self._socket_name = UDPServer.UDP_UNITTEST_SOCKET_NAME
            else:
                self._socket_name = UDPServer.UDP_SOCKET_NAME

        # WINDOWS HOST
        if ip_host:
            self._ip_host = ip_host
        else:
            # If UNITTEST, force
            if "KNOCK_UNITTEST" in os.environ:
                self._ip_host = UDPServer.UDP_IP_UNITTEST_SOCKET_HOST
            else:
                self._ip_host = UDPServer.UDP_IP_SOCKET_HOST

        # WINDOWS PORT
        if ip_port:
            self._ip_port = ip_port
        else:
            # If UNITTEST, force
            if "KNOCK_UNITTEST" in os.environ:
                self._ip_port = UDPServer.UDP_IP_UNITTEST_SOCKET_PORT
            else:
                self._ip_port = UDPServer.UDP_IP_SOCKET_PORT

        # NOTIFY
        if notify_interval_ms:
            self._notify_interval_ms = notify_interval_ms
        else:
            # If UNITTEST, force
            if "KNOCK_UNITTEST" in os.environ:
                self._notify_interval_ms = UDPServer.NOTIFY_UNITTEST_INTERVAL
            else:
                self._notify_interval_ms = UDPServer.NOTIFY_INTERVAL

        self._send_back_udp = send_back_udp
        self._is_started = False

        logger.info("_notify_interval_ms=%s", self._notify_interval_ms)

        logger.info("pool_size=%s", pool_size)
        logger.info("_socket_name=%s", self._socket_name)
        logger.info("_ip_host=%s", self._ip_host)
        logger.info("_ip_port=%s", self._ip_port)
        logger.info("_send_back_udp=%s", self._send_back_udp)
        logger.info("_notify_interval_ms=%s", self._notify_interval_ms)

    def start(self):
        """
        Start (async)
        """

        # Check
        if self._is_started:
            logger.warning("Already started, bypass")
            return

        # Start
        logger.info("Starting UDPBusinessServerDomainLinux")
        self._business_server_domain_linux = UDPBusinessServerDomainLinux(
            self._manager,
            self._socket_name,
            self._ip_host,
            int(self._ip_port),
            self._send_back_udp,
            self._notify_interval_ms,
            spawn=self._pool)

        # Listen
        self._business_server_domain_linux.start()

        # Start
        self._business_server_ip_port = UDPBusinessServerIpPort(
            self._manager,
            self._socket_name,
            self._ip_host,
            int(self._ip_port),
            self._send_back_udp,
            self._notify_interval_ms,
            spawn=self._pool)

        # Listen
        self._business_server_ip_port.start()

        # Ok
        self._is_started = True

    def stop(self):
        """
        Stop
        """

        # Check
        if not self._is_started:
            logger.warning("Not started, bypass")
            return

        # Stop
        self._is_started = False

        # noinspection PyProtectedMember
        if self._business_server_domain_linux._is_started:
            logger.info("Stopping _business_server_domain_linux")
            self._business_server_domain_linux.stop()
            self._business_server_domain_linux = None

        # noinspection PyProtectedMember
        if self._business_server_ip_port._is_started:
            logger.info("Stopping _business_server_ip_port")
            self._business_server_ip_port.stop()
            self._business_server_ip_port = None
