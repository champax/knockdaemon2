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
from queue import Queue

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


class KnockTransport(object):
    """
    Knock transport
    """

    def __init__(self):
        """
        Constructor
        """

        # Meters prefix
        self.meters_prefix = ""

        # Queue
        self._queue_to_send = Queue()

        # Max
        self._http_send_max_bytes = 64000

    def init_from_config(self, d_yaml_config, d, auto_start=True):
        """
        Initialize from configuration
        :param d_yaml_config: dict
        :type d_yaml_config: dict
        :param d: local dict
        :type d: dict
        :param auto_start: bool
        :type auto_start: bool
        """
        raise NotImplementedError()

    def process_notify(self, account_hash, node_hash, notify_values):
        """
        Process notify
        :param account_hash: Hash bytes to value
        :type account_hash; dict
        :param node_hash: Hash bytes to value
        :type node_hash; dict
        :param notify_values: List of (superv_key, tag, value)
        :type notify_values; list
        :return True if success
        :rtype bool
        """
        raise NotImplementedError()

    def stop(self):
        """
        Stop
        """
        raise NotImplementedError()
