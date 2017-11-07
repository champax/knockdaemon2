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
# noinspection PyBroadException
try:
    from collections import OrderedDict
except:
    # noinspection PyPackageRequirements,PyPep8Naming,PyUnresolvedReferences,PyPep8Naming,PyUnresolvedReferences
    from ordereddict import OrderedDict
import logging

from pythonsol.AtomicInt import AtomicInt
from pythonsol.DelayToCount import DelayToCount
from pythonsol.meter.MeterBase import MeterBase

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


class KnockStat(MeterBase):
    """
    Knock daemon statistics.
    """

    def __init__(self):
        """
        Constructor
        """

        # Probe related
        self.exec_probe_dtc = DelayToCount("exec_probe_dtc")
        self.exec_probe_exception = AtomicInt()
        self.exec_probe_timeout = AtomicInt()
        self.exec_probe_count = AtomicInt()
        self.exec_probe_bypass = AtomicInt()

        # Notify related
        self.notify_disco = AtomicInt()
        self.notify_simple_value = AtomicInt()
        self.notify_value = AtomicInt()

        # All related
        self.exec_all_dtc = DelayToCount("exec_all_dtc")
        self.exec_all_inner_exception = AtomicInt()
        self.exec_all_outer_exception = AtomicInt()
        self.exec_all_finally_exception = AtomicInt()
        self.exec_all_count = AtomicInt()
        self.exec_all_too_slow = AtomicInt()

        # Transport related
        self.transport_dtc = DelayToCount("transport_dtc")
        self.transport_call_count = AtomicInt()
        self.transport_ok_count = AtomicInt()
        self.transport_exception_count = AtomicInt()
        self.transport_failed_count = AtomicInt()

        self.transport_queue_max_size = AtomicInt()
        self.transport_queue_discard = AtomicInt()

        # Transport : buffer (protocol, non zipped)
        self.transport_buffer_pending_length = AtomicInt()
        self.transport_buffer_last_length = AtomicInt()
        self.transport_buffer_max_length = AtomicInt()

        # Transport : buffer (wire, may be zipped)
        self.transport_wire_last_length = AtomicInt()
        self.transport_wire_max_length = AtomicInt()

        self.transport_wire_last_ms = AtomicInt()
        self.transport_wire_max_ms = AtomicInt()

        # Superv related (server side)
        self.transport_spv_processed = AtomicInt()
        self.transport_spv_failed = AtomicInt()
        self.transport_spv_total = AtomicInt()

        # Superv related (server side, disco cache)
        self.http_disco_cache_hit = AtomicInt()
        self.http_disco_cache_miss = AtomicInt()
        self.http_disco_cache_nocache_false = AtomicInt()
        self.http_disco_cache_nocache_invalidcount = AtomicInt()
        self.http_disco_cache_add = AtomicInt()
        self.http_disco_cache_count = AtomicInt()

        # Superv related (client side)
        self.transport_client_spv_processed = AtomicInt()
        self.transport_client_spv_failed = AtomicInt()

        # UDP Related
        self.udp_notify_run = AtomicInt()
        self.udp_notify_run_ex = AtomicInt()
        self.udp_notify_run_dtc = DelayToCount("udp_notify_run_dtc")
        self.udp_recv = AtomicInt()
        self.udp_recv_counter = AtomicInt()
        self.udp_recv_gauge = AtomicInt()
        self.udp_recv_dtc = AtomicInt()
        self.udp_recv_unknown = AtomicInt()
        self.udp_recv_ex = AtomicInt()
        self.udp_recv_dtc_dtc = DelayToCount("udp_recv_dtc_dtc")

    def to_dict(self):
        """
        Return a dictionary representation of the instance (name => value)
        :return dict
        :rtype dict
        """

        d = OrderedDict()

        d.update(self.exec_probe_dtc.to_dict())
        d["exec_probe_exception"] = self.exec_probe_exception.get()
        d["exec_probe_timeout"] = self.exec_probe_timeout.get()
        d["exec_probe_count"] = self.exec_probe_count.get()
        d["exec_probe_bypass"] = self.exec_probe_bypass.get()

        d["notify_disco"] = self.notify_disco.get()
        d["notify_simple_value"] = self.notify_simple_value.get()
        d["notify_value"] = self.notify_value.get()

        d.update(self.exec_all_dtc.to_dict())
        d["exec_all_inner_exception"] = self.exec_all_inner_exception.get()
        d["exec_all_outer_exception"] = self.exec_all_outer_exception.get()
        d["exec_all_finally_exception"] = self.exec_all_finally_exception.get()
        d["exec_all_count"] = self.exec_all_count.get()
        d["exec_all_too_slow"] = self.exec_all_too_slow.get()

        d.update(self.transport_dtc.to_dict())
        d["transport_call_count"] = self.transport_call_count.get()
        d["transport_ok_count"] = self.transport_ok_count.get()
        d["transport_exception_count"] = self.transport_exception_count.get()
        d["transport_failed_count"] = self.transport_failed_count.get()

        d["transport_queue_max_size"] = self.transport_queue_max_size.get()
        d["transport_queue_discard"] = self.transport_queue_discard.get()
        d["transport_buffer_max_length"] = self.transport_buffer_max_length.get()

        d["transport_spv_processed"] = self.transport_spv_processed.get()
        d["transport_spv_failed"] = self.transport_spv_failed.get()
        d["transport_spv_total"] = self.transport_spv_total.get()

        d["http_disco_cache_hit"] = self.http_disco_cache_hit.get()
        d["http_disco_cache_miss"] = self.http_disco_cache_miss.get()
        d["http_disco_cache_nocache_false"] = self.http_disco_cache_nocache_false.get()
        d["http_disco_cache_nocache_invalidcount"] = self.http_disco_cache_nocache_invalidcount.get()
        d["http_disco_cache_add"] = self.http_disco_cache_add.get()

        d["transport_client_spv_processed"] = self.transport_client_spv_processed.get()
        d["transport_client_spv_failed"] = self.transport_client_spv_failed.get()

        d["udp_notify_run"] = self.udp_notify_run.get()
        d["udp_notify_run_ex"] = self.udp_notify_run_ex.get()
        d.update(self.udp_notify_run_dtc.to_dict())

        d["udp_recv"] = self.udp_recv.get()
        d["udp_recv_counter"] = self.udp_recv_counter.get()
        d["udp_recv_gauge"] = self.udp_recv_gauge.get()
        d["udp_recv_dtc"] = self.udp_recv_dtc.get()
        d["udp_recv_unknown"] = self.udp_recv_unknown.get()
        d["udp_recv_ex"] = self.udp_recv_ex.get()
        d.update(self.udp_recv_dtc_dtc.to_dict())

        return d
