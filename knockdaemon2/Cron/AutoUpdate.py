"""
-*- coding: utf-8 -*-
===============================================================================

Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac



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
import sys
from random import randint

from pysolbase.SolBase import SolBase

from knockdaemon2.Cron.AutoUpdateBase import ExitOnError
from knockdaemon2.Cron.Debian.AutoUpdateDebian import AutoUpdateDebian
from knockdaemon2.Cron.Redhat.AutoUpdateRedhat import AutoUpdateRedhat
from knockdaemon2.Platform.PTools import PTools

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


def random_sleep():
    """
    Random sleep
    """

    # Random sleep
    time_to_sleep = randint(0, 15000)
    logger.info("Sleeping, ms=%s", time_to_sleep)
    SolBase.sleep(time_to_sleep)
    logger.info("Sleep complete, firing auto-update")


def cron():
    """
    Cli wrapper
    :return:
    :rtype:
    """
    try:
        SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file='/var/log/knock-autoupdate.log', log_to_syslog=False, log_to_console=False)

        # Detect platform type
        distribution_type = PTools.get_distribution_type()
        logger.info("Detected distribution_type=%s", distribution_type)

        # Go
        if distribution_type == "debian":
            random_sleep()
            AutoUpdateDebian()
        elif distribution_type == "redhat":
            random_sleep()
            AutoUpdateRedhat()
        else:
            logger.warn("Not supported distribution_type=%s, cannot check for updates", distribution_type)

    except ExitOnError as err:
        sys.exit(err.exit_code)
    except Exception as err:
        logger.critical(SolBase.extostr(err))
        sys.exit(127)
    sys.exit(0)


try:
    if __name__ == '__main__':
        cron()
except Exception as e:
    logger.critical(SolBase.extostr(e))
    sys.exit(127)
