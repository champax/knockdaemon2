# -*- coding: utf-8 -*-
"""

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
import os

from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Platform.PTools import PTools

logger = logging.getLogger(__name__)


class KnockProbe(object):
    """
    A Knock executable probe.
    You have to implement "execute" at higher level.
    """

    def __init__(self, linux_support=True, windows_support=False):
        """
        Constructor
        :param linux_support: bool
        :type linux_support: bool
        :param windows_support: bool
        :type windows_support: bool
        """

        self._knock_manager = None
        self.key = None
        self.d_local_conf = None
        self.probe_class = None
        self.exec_interval_ms = 60000
        self.exec_enabled = True

        self.linux_support = linux_support
        self.windows_support = windows_support
        self.platform = PTools.get_distribution_type()
        self.platform_supported = self.is_supported_on_platform()

        self.class_name = SolBase.get_classname(self)

        # Category. Not used for HttpAsyncTransport, push toward Influx tag "category".
        # To be overriden at higher level.
        # Format is : "/categ<0>/.../categ<n>"
        self.category = "/undef"

        # Timeout override (can be usefull for some slow probes that are executed not often)
        self.exec_timeout_override_ms = None

        # Probes timestamp override
        # If set (by KnockManager), notify timestamp will be this one
        # NEVER override this in probe implementation, KnockManager handle this (configuration based)
        self.notify_ts_override = None

    def set_manager(self, knock_manager):
        """
        Set manager
        :param knock_manager: A KnockManager instance
        :type knock_manager: KnockManager
        """
        self._knock_manager = knock_manager

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

        self.d_local_conf = d
        self.key = k
        self.probe_class = d["class_name"]
        self.exec_enabled = d["exec_enabled"]
        self.exec_interval_ms = d["exec_interval_sec"] * 1000

        self._check_and_fix_limits()

    def _check_and_fix_limits(self):
        """
        Check and set limits
        """

        # If unittest, do nothing
        if "KNOCK_UNITTEST" in os.environ.data:
            return

        # Lower limits for important stuff
        if self.exec_interval_ms < 10000:
            self.exec_interval_ms = 10000

    def is_supported_on_platform(self):
        """
        Return if current probe is supported on current platform
        :return bool
        :rtype bool
        """
        if PTools.get_distribution_type() == "windows":
            return self.windows_support
        else:
            return self.linux_support

    def execute(self):
        """
        Execute a probe.
        IMPORTANT note on execute() behavior :
        A) ALL discovery MUST be notified ASAP, BEFORE checking instance(s) themselves (ie: BEFORE io/socket)
        B1) Instance checks must be fired after A
        B2) "running" key must be notified correctly (and will be nodata backed at server level)

        In all cases, execute will be stopped if execution time is too long, so it is CRITICAL than discoveries are fired in high prio.

        Reasons :
        - Discoveries register instances at server level
        - "running" key (for each discovered instance) will be backed by a nodata trigger
        - SO : as discoveries are send ASAP, even if instance is down, even is execute() exec is cut => the nodata trigger on running keys will be fired
        """
        dt = PTools.get_distribution_type()
        if dt == "windows":
            # WINDOWS
            if not self.windows_support:
                logger.info("Not supported on [%s], probe=%s", dt, self)
            else:
                self._execute_windows()
        else:
            # LINUX
            if not self.linux_support:
                logger.info("Not supported on [%s], probes=%s", dt, self)
            else:
                self._execute_linux()

    def _execute_linux(self):
        """
        Execute a probe (linux)
        """
        raise NotImplementedError()

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        raise NotImplementedError()

    def notify_discovery_n(self, disco_key, d_disco_id_tag):
        """
        Notify discovery (1..n)

        Sample:
        - notify_discovery_n("k.dns", {"HOST": "my_host", "SERVER": "my_server"})
        :param disco_key: discovery key
        :type disco_key: str
        :param d_disco_id_tag: dict {"disco_tag_1": "value", "disco_tag_n": "value"}
        :type d_disco_id_tag: dict
        """

        self._knock_manager.notify_discovery_n(disco_key, d_disco_id_tag)

    def notify_value_n(self, counter_key, d_disco_id_tag, counter_value, ts=None, additional_fields=None):
        """
        Notify value

        Example :
        - notify_value_n("k.dns.time", {"HOST": "my_host", "SERVER": "my_server"}, 1.5)

        :param counter_key: Counter key (str)
        :type counter_key: str
        :param d_disco_id_tag: None (if no discovery) or dict of {disco_id: disco_tag}
        :type d_disco_id_tag: None, dict
        :param counter_value: Counter value
        :type counter_value: object
        :param ts: timestamp (epoch), or None to use current
        :type ts: None, float
        :param additional_fields: dict
        :type additional_fields: dict

        """

        # Timestamp to use
        if ts is None:
            # Use override if set, else use provided value (None or set)
            if self.notify_ts_override is not None:
                logger.debug("Using notify_ts_override, ts=%s, notify_ts_override=%s", ts, self.notify_ts_override)
                Meters.aii("knock_stat_ts_override")
                ts = self.notify_ts_override

        # Notify manager
        self._knock_manager.notify_value_n(counter_key, d_disco_id_tag, counter_value, ts, {"category": self.category}, additional_fields)

    def __str__(self):
        """
        To string override
        :return: A string
        :rtype string
        """

        return "kprobe:ms={0}*s={1}*c={2}*on={3}*ux={4}*win={5}*pl={6}*sup={7}*k={8}*ntso={9}".format(
            self.exec_interval_ms,
            self.probe_class,
            self.class_name,
            self.exec_enabled,
            self.linux_support,
            self.windows_support,
            self.platform,
            self.platform_supported,
            self.key,
            self.notify_ts_override,
        )
