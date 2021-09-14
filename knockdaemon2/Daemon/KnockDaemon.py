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
import sys
from logging.handlers import SysLogHandler

from gevent import util
from pysolbase.SolBase import SolBase
from pysoldaemon.daemon.Daemon import Daemon

from knockdaemon2.Core.KnockManager import KnockManager

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
                       timeout_ms,
                       logtosyslog=True,
                       logtosyslog_facility=SysLogHandler.LOG_LOCAL0,
                       logtoconsole=False,
                       app_name="knockdaemon2"
                       ):

        # Us
        self.is_running = True
        self.start_loop_exited = False

        # Base
        # noinspection PyProtectedMember
        Daemon._internal_init(self, pidfile, stdin, stdout, stderr, logfile, loglevel,
                              on_start_exit_zero, max_open_files, change_dir, timeout_ms,
                              logtosyslog, logtosyslog_facility, logtoconsole, app_name)

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
            default="/etc/knock/knockdaemon2.yaml",
            action="store",
            help="knockdaemon2 ini file [default: /etc/knock/knockdaemon2.yaml]"
        )

        return arg_parser

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def _on_reload(self, *args, **kwargs):
        """
        Test
        """
        logger.debug("Called")

    # noinspection PyMethodMayBeStatic
    def _on_status(self):
        """
        Test
        """
        logger.warning("Called")

        # Flush out all call stacks
        try:
            with open("/tmp/knockdaemon2.run_info.txt", "w") as outfile:
                util.print_run_info(
                    thread_stacks=True,
                    greenlet_stacks=True,
                    limit=None,
                    file=outfile,
                )
        except Exception as e:
            s = SolBase.extostr(e)
            logger.warning("Ex=%s", s)

    def _on_start(self):
        """
        Test
        """
        logger.info("knockdaemon2 starting")

        # Fetch config
        config_file = self.vars["c"]
        logger.info("config_file=%s", config_file)

        # Init manager
        self.k = KnockManager(config_file)

        # Start manager
        self.k.start()

        # Engage run forever loop
        logger.info("knockdaemon2 started")
        while self.is_running:
            SolBase.sleep(500)
        self.start_loop_exited = True
        logger.debug("knockdaemon2 signaled")

    def _on_stop(self):
        """
        Test
        """
        logger.info("knockdaemon2 stopping")

        # Signal
        self.is_running = False

        # We cannot wait (https://github.com/gevent/gevent/issues/799)
        logger.info("knockdaemon2 stopped")


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
