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

from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.Core.UDPServer import UDPServer

__author__ = 'llabatut'
logger = logging.getLogger(__name__)
logger.info("knockdaemon2 starting")

# Fetch config
config_file = "knockdaemon2.yaml"
logger.info("config_file=%s", config_file)

# Init manager
UDPServer.UDP_SOCKET_NAME = UDPServer.UDP_UNITTEST_SOCKET_NAME

k = KnockManager(config_file)

# Start manager
try:
    k.start()

    isRunning = False

    # Engage run forever loop
    logger.info("knockdaemon2 started")
    SolBase.sleep(20000)
    while isRunning:
        SolBase.sleep(500)
    startLoopExited = True
    logger.info("knockdaemon2 signaled")
except KeyboardInterrupt:
    logger.info("Stop now")
    if k:
        k.stop()
    logger.info("Stop now done")
