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
import sys
from pythonsol.daemon.Daemon import Daemon
from pythonsol.SolBase import SolBase
from knockdaemon.Core.KnockManager import KnockManager

# Override logging to file (no syslog)
SolBase.voodoo_init()
SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file=None, log_to_syslog=False)
logger = logging.getLogger(__name__)


class KnockDaemon(Daemon):
    """
    Test
    """

    def __init__(self):
        """
        Constructor
        """
        self.is_running = False
        self.start_loop_exited = False
        self.k = None

        Daemon.__init__(self)

    def _internal_init(self,
                       pidfile,
                       stdin, stdout, stderr, logfile, loglevel,
                       on_start_exit_zero,
                       max_open_files,
                       change_dir,
                       timeout_ms):

        # Us
        self.is_running = True
        self.start_loop_exited = False

        # Base
        # noinspection PyProtectedMember
        Daemon._internal_init(self, pidfile, stdin, stdout, stderr, logfile, loglevel,
                              on_start_exit_zero, max_open_files, change_dir, timeout_ms)

        # Log
        logger.debug("Done, self.class=%s", SolBase.get_classname(self))

    @classmethod
    def get_daemon_instance(cls):
        """
        Get a new daemon instance
        :return CustomDaemon
        :rtype CustomDaemon
        """
        return KnockDaemon()

    @classmethod
    def initialize_arguments_parser(cls):
        """
        Initialize the parser.
        :param cls: class.
        :return ArgumentParser
        :rtype ArgumentParser
        """

        # Call base
        arg_parser = Daemon.initialize_arguments_parser()

        # Requires our config
        arg_parser.add_argument(
            "-c",
            metavar="c",
            type=str,
            default="/etc/knock/knockdaemon.ini",
            action="store",
            help="knockdaemon ini file [default: /etc/knock/knockdaemon.ini]"
        )

        return arg_parser

    # noinspection PyUnusedLocal
    def _on_reload(self, *args, **kwargs):
        """
        Test
        """
        logger.debug("Called")

    def _on_status(self):
        """
        Test
        """
        logger.debug("Called")

    def _on_start(self):
        """
        Test
        """
        logger.info("KnockDaemon starting")

        # Fetch config
        config_file = self.vars["c"]
        logger.info("config_file=%s", config_file)

        # Init manager
        self.k = KnockManager(config_file)

        # Start manager
        self.k.start()

        # Engage run forever loop
        logger.info("KnockDaemon started")
        while self.is_running:
            SolBase.sleep(500)
        self.start_loop_exited = True
        logger.debug("KnockDaemon signaled")

    def _on_stop(self):
        """
        Test
        """
        logger.info("KnockDaemon stopping")

        # Signal
        self.is_running = False

        # Wait for completion
        while not self.start_loop_exited:
            SolBase.sleep(10)

        logger.info("KnockDaemon stopped")


def run():
    """
    Start bouzin
    """
    try:
        KnockDaemon.main_helper(sys.argv, {})
    except Exception as e:
        logger.error("Exception, exiting -1, ex=%s", SolBase.extostr(e))
        sys.exit(-1)


if __name__ == "__main__":
    run()
