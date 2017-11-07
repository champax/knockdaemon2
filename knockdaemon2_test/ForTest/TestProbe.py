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
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class TestProbe(KnockProbe):
    """
    A Knock executable probe.
    You have to implement "execute" at higher level.
    """

    def __init__(self):
        """
        Constructor
        """

        # Base (both support)
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        # Go
        self.custom_key_b = None
        self.exec_count = 0

        # Exec ms array
        self.ar_exec_start = list()

        # Sleep ms
        self.sleep_ms_in_exec = 0

    def init_from_config(self, config_parser, section_name):
        """
        Initialize from configuration
        :param config_parser: dict
        :type config_parser: dict
        :param section_name: Ini file section for our probe
        :type section_name: str
        """

        # Base
        KnockProbe.init_from_config(self, config_parser, section_name)

        # Go
        self.custom_key_b = config_parser[section_name]["custom_key_b"]

    def _execute_linux(self):
        """
        Execute a probe.
        """
        logger.info("Go")
        self._execute_all()

    def _execute_windows(self):
        """
        Execute a probe.
        """
        logger.info("Go")
        self._execute_all()

    def _execute_all(self):
        """
        Execute a probe.
        """
        logger.info("Go")
        try:
            # Exec ms array
            self.ar_exec_start.append(SolBase.mscurrent())

            if self.sleep_ms_in_exec > 0:
                logger.info("Forcing sleep_ms_in_exec=%s", self.sleep_ms_in_exec)
                SolBase.sleep(self.sleep_ms_in_exec)
                logger.info("Sleep done")

            self.exec_count += 1

            # Discovery
            self.notify_discovery_n("test.dummy.discovery", {"TYPE": "all"})
            self.notify_discovery_n("test.dummy.discovery", {"TYPE": "one"})
            self.notify_discovery_n("test.dummy.discovery", {"TYPE": "two"})

            # Values
            self.notify_value_n("test.dummy.count", {"TYPE": "all"}, 100)
            self.notify_value_n("test.dummy.count", {"TYPE": "one"}, 90)
            self.notify_value_n("test.dummy.count", {"TYPE": "two"}, 10)

            self.notify_value_n("test.dummy.error", {"TYPE": "all"}, 5)
            self.notify_value_n("test.dummy.error", {"TYPE": "one"}, 3)
            self.notify_value_n("test.dummy.error", {"TYPE": "two"}, 2)
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
        finally:
            logger.info("Finally")

    def __str__(self):
        """
        To string override
        :return: A string
        :rtype string
        """

        return "{0}*e={1}".format(
            KnockProbe.__str__(self),
            self.exec_count,

        )
