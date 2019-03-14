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
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    import logging
    from pysolbase.SolBase import SolBase
    from knockdaemon2.Core.KnockManager import KnockManager
    from knockdaemon2.Core.UDPServer import UDPServer

    from knockdaemon2.Windows.Wmi.Wmi import Wmi

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
            if SolBase.get_machine_name().lower().find("klchwin") >= 0:
                UDPServer.UDP_IP_SOCKET_PORT = UDPServer.UDP_IP_UNITTEST_SOCKET_PORT

            # Fetch config
            config_file = SolBase.get_pathseparator().join(["C:", "champax", "kd_conf_local", "knockdaemon2", "knockdaemon2.yaml"])
            logger.info("config_file=%s", config_file)

            # Init manager
            logger.info("Init : Manager")
            k = KnockManager(config_file)

            # Wmi start (between Manager init and start)
            logger.info("Start : Wmi")
            Wmi.wmi_start()

            # Start manager
            k.start()

            # Engage run forever loop
            logger.info("knockdaemon2 started")
            while True:
                SolBase.sleep(250)
        except KeyboardInterrupt:
            logger.info("Stop now")
            logger.info("Stop : Wmi")
            Wmi.wmi_stop()
            logger.info("Stop : Manager")
            if k:
                k.stop()
            logger.info("Stop now done")


    if __name__ == "__main__":
        run()
