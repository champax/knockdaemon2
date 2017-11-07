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

from pysolbase.SolBase import SolBase

logger = logging.getLogger(__name__)


class Tools(object):
    """
    Tools
    """

    # ==========================================
    # INFLUX CONVERT
    # ==========================================

    @classmethod
    def to_influx_format(cls, account_hash, node_hash, notify_values):
        """
        Process notify
        :param account_hash: Hash str to value
        :type account_hash; dict
        :param node_hash: Hash str to value
        :type node_hash; dict
        :param notify_values: List of (superv_key, tag, value, d_opt_tags). Cleared upon success.
        :type notify_values; list
        :return list of dict
        :rtype list
        """

        # We receive :
        # dict string/string
        # account_hash => {'acc_key': 'tamereenshort', 'acc_namespace': 'unittest'}
        #
        # dict string/string
        # node_hash => {'host': 'klchgui01'}
        #
        # dict string (formatted) => tuple (disco_name, disco_id, disco_value)
        # notify_hash => {'test.dummy|TYPE|one': ('test.dummy', 'TYPE', 'one'), 'test.dummy|TYPE|all': ('test.dummy', 'TYPE', 'all'), 'test.dummy|TYPE|two': ('test.dummy', 'TYPE', 'two')}
        #
        # list : tuple (probe_name, disco_value, value, timestamp)
        # notify_values => <type 'list'>: [('test.dummy.count', 'all', 100, 1503045097.626604), ('test.dummy.count', 'one', 90, 1503045097.626629), ('test.dummy.count[two]', None, 10, 1503045097.626639), ('test.dummy.error', 'all', 5, 1503045097.62668), ('test.dummy.error', 'one', 3, 1503045097.626704), ('test.dummy.error', 'two', 2, 1503045097.626728)]

        # We must send blocks like :
        # [
        #     {
        #         "measurement": "cpu_load_short",
        #         "tags": {"host": "server01", "region": "us-west"},
        #         "time": "2009-11-10T23:00:00Z",
        #         "fields": {"value": 0.64}
        #     },
        #     ...
        #     {....}
        # ]

        # Get host
        assert len(node_hash) == 1, "len(node_hash) must be 1, got node_hash={0}".format(node_hash)
        c_host = node_hash["host"]
        logger.info("Processing c_host=%s", c_host)

        # Process data and build output dict
        ar_out = list()
        for probe_name, dd, value, timestamp, d_opt_tags in notify_values:
            # We got a unix timestamp (1503045097.626604)
            # Convert it to required date format
            dt_temp = SolBase.dt_ensure_utc_naive(SolBase.epoch_to_dt(timestamp))
            s_dt_temp = dt_temp.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Init
            d_tags = {"host": c_host, "ns": account_hash["acc_namespace"]}

            # Discovery
            if dd:
                d_tags.update(dd)

            # Add optional tags
            if d_opt_tags:
                d_tags.update(d_opt_tags)

            # Build
            d_temp = {
                "measurement": probe_name,
                "tags": d_tags,
                "time": s_dt_temp,
                "fields": {"value": value}
            }
            logger.info("Built, d_temp=%s", d_temp)
            ar_out.append(d_temp)

        # Over
        return ar_out
