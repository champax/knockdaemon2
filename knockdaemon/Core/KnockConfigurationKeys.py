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

logger = logging.getLogger(__name__)


class KnockConfigurationKeys(object):
    """
    Configuration keys
    """

    INI_KNOCKD_TAG = "knockd"
    INI_KNOCKD_EXEC_TIMEOUT_MS = "exectimeout_ms"
    INI_KNOCKD_ACC_NAMESPACE = "acc_namespace"
    INI_KNOCKD_ACC_KEY = "acc_key"

    INI_PROBE_TAG = "knock_"
    INI_PROBE_CLASS = "class_name"
    INI_PROBE_EXEC_INTERVAL_SEC = "exec_interval_sec"
    INI_PROBE_EXEC_ENABLED = "exec_enabled"

    INI_TRANSPORT_TAG = "transport"
    INI_UDP_SERVER_TAG = "udp_server"
    INI_TRANSPORT_CLASS = "class_name"
