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
from pythonsol.SolBase import SolBase
from knockdaemon2.Core.KnockManager import KnockManager

# CMD : /usr/share/python/knockdaemon2/bin/python /usr/share/python/knockdaemon2/bin/knockdaemon2
# -pidfile=/var/run/knockdaemon2.pid -stderr=/var/log/knockdaemon2.err -stdout=/var/log/knockdaemon2.log -maxopenfiles=4096
# -user=root
# -c=/etc/knock/knockdaemon2/knockdaemon2.ini start
#
# REQUIRES : A valid /etc/knock/knockdaemon2/ folder
from knockdaemon2.Core.UDPServer import UDPServer

logger = logging.getLogger(__name__)

SolBase.voodoo_init()
SolBase.logging_init(log_level="INFO", force_reset=True)


def run():
    """
    Start bouzin
    """
    k = None
    try:
        logger.info("knockdaemon2 starting")

        # -------------------------------
        # IF machine is lchgui : force UDP socket name
        # TODO : Rewrite this later on
        # -------------------------------
        if SolBase.get_machine_name().find("klchgui") >= 0:
            UDPServer.UDP_SOCKET_NAME = UDPServer.UDP_UNITTEST_SOCKET_NAME

        # Fetch config
        config_file = "/etc/knock/knockdaemon2_lchgui/knockdaemon2.ini"
        logger.info("config_file=%s", config_file)

        # Init manager
        k = KnockManager(config_file)

        # Start manager
        k.start()

        # Engage run forever loop
        logger.info("knockdaemon2 started")
        while True:
            SolBase.sleep(250)
    except KeyboardInterrupt:
        logger.info("Stop now")
        if k:
            k.stop()
        logger.info("Stop now done")


if __name__ == "__main__":
    run()
