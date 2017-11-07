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

from knockdaemon2.Transport.KnockTransport import KnockTransport


class TestTransport(KnockTransport):
    """
    A Knock executable probe.
    You have to implement "execute" at higher level.
    """

    def __init__(self):
        """
        Constructor
        """

        # Base
        KnockTransport.__init__(self)

        # Go
        self.notify_call_count = 0
        self.node_hash = None
        self.notify_hash = None
        self.notify_values = None
        self.custom_key_b = None
        self.stop_count = 0

    def init_from_config(self, config_parser, section_name, auto_start=True):
        """
        Initialize from configuration
        :param config_parser: dict
        :type config_parser: dict
        :param section_name: Ini file section for our probe
        :type section_name: str
        :param auto_start: bool
        :type auto_start: bool
        """

        # Go
        self.custom_key_b = config_parser[section_name]["custom_key_b"]

    def process_notify(self, account_hash, node_hash, notify_hash, notify_values):
        """
        Process notify
        :param account_hash: Hash str to value
        :type account_hash; dict
        :param node_hash: Hash str to value
        :type node_hash; dict
        :param notify_hash: Hash str to (disco_key, disco_id, tag)
        :type notify_hash; dict
        :param notify_values: List of (superv_key, tag, value)
        :type notify_values; list
        """
        self.notify_call_count += 1
        self.node_hash = node_hash
        self.notify_hash = notify_hash
        self.notify_values = notify_values

        # We return False (do NOT empty hash/list inside manager)
        return False

    def stop(self):
        """
        Stop
        """
        self.stop_count += 1
