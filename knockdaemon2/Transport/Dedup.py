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
from collections import OrderedDict

from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

logger = logging.getLogger(__name__)


class Dedup(object):
    """
    Class to handle probes values de-duplication.
    Working on a 1 minute window.
    Intended for backend that do not perform dedup on their end.
    Pretty dirty.
    Internal structure :
    dict : dedup_key
    => dict : minute window => added ms
    """

    # ============================
    # HELPERS
    # ============================

    @classmethod
    def get_dedup_key(cls, probe_name, dd, d_opt_tags):
        """
        Get dedup key (computed using probe names and tags, ordered).
        :param probe_name: str
        :type probe_name: str
        :param dd: dict,None
        :type dd: dict,None
        :param d_opt_tags: dict,None
        :type d_opt_tags: dict,None
        :return str
        :rtype str
        """

        # Init
        d_tags = {}

        # Discovery
        if dd:
            d_tags.update(dd)

        # Add optional tags
        if d_opt_tags:
            d_tags.update(d_opt_tags)

        # Sorted and fire
        do = OrderedDict(sorted(d_tags.items(), key=lambda t: t[0]))

        # Key
        key = probe_name + "_tags"
        for k, v in do.iteritems():
            key += "_" + str(k) + ":" + str(v)

        return key

    @classmethod
    def epoch_to_dt_without_sec(cls, timestamp):
        """
        Epoch to date without seconds and millis (ie rounded to minute).
        :param timestamp: float
        :type timestamp: float
        :return datetime
        :rtype datetime
        """
        dt_temp = SolBase.dt_ensure_utc_naive(SolBase.epoch_to_dt(timestamp))

        # Remove millis and seconds
        dt_temp = dt_temp.replace(microsecond=0)
        dt_temp = dt_temp.replace(second=0)

        return dt_temp

    # ============================
    # MEMBERS
    # ============================

    def __init__(self):
        """
        Constructor
        """

        # Dedup hash
        self.d_dedup = dict()

    def dedup(self, notify_values, limit_ms):
        """
        Purge internal dedup dict (kicking all values added before limit_ms).
        Then dedup provided notify values and return them.
        :param notify_values: list
        :type notify_values: list
        :param limit_ms: Limit ms
        :type limit_ms: int
        :return list
        :rtype list
        """

        # Purge
        self._purge(limit_ms)

        # Dedup
        return self._dedup(notify_values)

    def _purge(self, limit_ms):
        """
        Purge internal dedup dict (kicking all values added before limit_ms).
        :param limit_ms: Limit ms
        :type limit_ms: int
        """

        to_del1 = list()
        for cur_dedup_key, cur_d in self.d_dedup.iteritems():
            to_del2 = list()
            for cur_window, cur_added_ms in cur_d.iteritems():
                if cur_added_ms < limit_ms:
                    to_del2.append(cur_window)
            for cur_window in to_del2:
                    del cur_d[cur_window]
            if len(cur_d) == 0:
                Meters.aii("dedup.purge_window")
                to_del1.append(cur_dedup_key)
        for cur_dedup_key in to_del1:
            Meters.aii("dedup.purge_key")
            del self.d_dedup[cur_dedup_key]

        # Stats
        c = 0
        for cur_dedup_key, cur_d in self.d_dedup.iteritems():
            c += len(cur_d)
        Meters.ai("dedup.cur_hash_key_len").set(len(self.d_dedup))
        Meters.ai("dedup.cur_hash_window_len").set(c)

    def _dedup(self, notify_values):
        """
        Purge internal dedup dict (kicking all values added before limit_ms).
        Then dedup provided notify values and return them.
        :param notify_values: list
        :type notify_values: list
        :return list
        :rtype list
        """

        out_list = list()

        # Browse incoming
        for probe_name, dd, value, timestamp, d_opt_tags, additional_fields in notify_values:
            # Get key
            in_dedup_key = self.get_dedup_key(probe_name, dd, d_opt_tags)

            # Get window
            in_window = self.epoch_to_dt_without_sec(timestamp)

            # Check if we have a hit (meaning we already have a value for current key and current windows)
            if in_dedup_key in self.d_dedup:
                if in_window in self.d_dedup[in_dedup_key]:
                    # We have a hit, this one is discarded
                    Meters.aii("dedup.discard_window_hit")
                else:
                    # We have a miss, we keep this one
                    out_list.append((probe_name, dd, value, timestamp, d_opt_tags,additional_fields))

                    # We register (add)
                    Meters.aii("dedup.keep_window_miss")
                    self.d_dedup[in_dedup_key][in_window] = SolBase.mscurrent()
            else:
                # We have a miss, we keep this one
                out_list.append((probe_name, dd, value, timestamp, d_opt_tags,additional_fields))

                # We register (init)
                Meters.aii("dedup.keep_key_miss")
                self.d_dedup[in_dedup_key] = {in_window: SolBase.mscurrent()}

        # Over
        return out_list
