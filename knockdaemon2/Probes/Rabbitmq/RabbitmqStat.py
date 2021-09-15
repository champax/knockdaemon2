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
import re

from pysolbase.FileUtility import FileUtility

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class RabbitmqStat(KnockProbe):
    """
    Probe
    """
    FILTER_COUNTER_PER_QUEUE = re.compile(r'^message_stats\.(.*)_details\.rate$')

    KEYS = [
        # INTERNAL
        ("k.rabbitmq.started", "int", "k.rabbitmq.started", "custom"),

        # Nodes (current)
        ("k.rabbitmq.node.count", "int", "k.rabbitmq.node.count", "sum"),
        ("k.rabbitmq.node.running.count", "int", "k.rabbitmq.node.running.count", "sum"),

        # Queues (current)
        ("k.rabbitmq.queue.consumers", "int", "k.rabbitmq.queue.consumers", "sum"),
        ("k.rabbitmq.queue.messages", "int", "k.rabbitmq.queue.messages", "sum"),
        ("k.rabbitmq.queue.message_ready", "int", "k.rabbitmq.queue.message_ready", "sum"),
        ("k.rabbitmq.queue.messages_unacknowledged", "int", "k.rabbitmq.queue.messages_unacknowledged", "sum"),
        ("k.rabbitmq.queue.slave_nodes", "int", "k.rabbitmq.queue.slave_nodes", "sum"),
        ("k.rabbitmq.queue.synchronised_slave_nodes", "int", "k.rabbitmq.queue.synchronised_slave_nodes", "sum"),

        # Rates (copyright NASA?)
    ]

    AR_QUEUES = [
        ("backing_queue_status.avg_ack_egress_rate", 13),
        ("backing_queue_status.avg_ack_ingress_rate", 14),
        ("backing_queue_status.avg_egress_rate", 15),
        ("backing_queue_status.avg_ingress_rate", 16),
        ("message_stats.ack_details.rate", 17),
        ("message_stats.confirm_details.rate", 18),
        ("message_stats.deliver_details.rate", 19),
        ("message_stats.deliver_get_details.rate", 20),
        ("message_stats.deliver_no_ack_details.rate", 21),
        ("message_stats.disk_reads_details.rate", 22),
        ("message_stats.disk_writes_details.rate", 23),
        ("message_stats.get_details.rate", 24),
        ("message_stats.get_no_ack_details.rate", 25),
        ("message_stats.publish_details.rate", 26),
        ("message_stats.publish_in_details.rate", 27),
        ("message_stats.publish_out_details.rate", 28),
        ("message_stats.redeliver_details.rate", 29),
        ("message_stats.return_unroutable_details.rate", 30),
        ("messages_details.rate", 31),
        ("messages_ready_details.rate", 32),
        ("messages_unacknowledged_details.rate", 33),
        ("reductions_details.rate", 34),
    ]

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self._d_aggregate = None
        self.category = "/nosql/rabbitmq"

    def _execute_linux(self):
        """
        Execute
        """

        self._execute_native()

    def _notify_down(self):
        """
        Notify down
        """

        self.notify_value_n("k.rabbitmq.started", {"PORT": "default"}, 0)

    def _execute_native(self):
        """
        Exec, native
        :return:
        """
        # ---------------------------
        # DETECT CONFIGS
        # ---------------------------

        # Centos : /etc/rabbitmq/rabbitmq.config
        # All : /etc/rabbitmq/enabled_plugins

        rabbit_found = False
        for f in ["/etc/rabbitmq/rabbitmq.config", "/etc/rabbitmq/enabled_plugins"]:
            if FileUtility.is_file_exist(f):
                rabbit_found = True
                break

        # Check
        if not rabbit_found:
            logger.info("No rabbitmq detected, give up")
            return

        # Must have rabbitmqadmin installed (otherwise signal DOWN)
        ec, so, se = ButcherTools.invoke("rabbitmqadmin --help")
        if ec != 0:
            logger.error("Unable to invoke rabbitmqadmin (you may have to install it), signaling down, ec=%s, so=%s, se=%s", ec, repr(so), repr(so))
            self._notify_down()
            return

        # ----------------
        # NODES
        # ----------------
        nodes_ec, nodes_so, nodes_se = ButcherTools.invoke("rabbitmqadmin list nodes name type running uptime")
        if nodes_ec != 0:
            logger.error("Nodes : invoke failed toward rabbitmqadmin (you may have to install it), signaling down, ec=%s, so=%s, se=%s", ec, repr(so), repr(so))
            self._notify_down()
            return

        # ----------------
        # QUEUES
        # ----------------
        queues_ec, queues_so, queues_se = ButcherTools.invoke(
            "rabbitmqadmin list queues vhost name auto_delete consumers durable idle_since messages message_ready messages_unacknowledged node slave_nodes synchronised_slave_nodes "
            "backing_queue_status.avg_ack_egress_rate backing_queue_status.avg_ack_ingress_rate backing_queue_status.avg_egress_rate backing_queue_status.avg_ingress_rate "
            "message_stats.ack_details.rate message_stats.confirm_details.rate message_stats.deliver_details.rate message_stats.deliver_get_details.rate message_stats.deliver_no_ack_details.rate "
            "message_stats.disk_reads_details.rate message_stats.disk_writes_details.rate message_stats.get_details.rate message_stats.get_no_ack_details.rate message_stats.publish_details.rate "
            "message_stats.publish_in_details.rate message_stats.publish_out_details.rate message_stats.redeliver_details.rate message_stats.return_unroutable_details.rate messages_details.rate messages_ready_details.rate messages_unacknowledged_details.rate reductions_details.rate")
        if queues_ec != 0:
            logger.error("Queues : invoke failed toward rabbitmqadmin (you may have to install it), signaling down, ec=%s, so=%s, se=%s", ec, repr(so), repr(so))
            self._notify_down()
            return

        # ----------------
        # Process buffer
        # ----------------
        if not self.process_rabbitmq_buffers(nodes_se, queues_so):
            self._notify_down()
            return

    def process_rabbitmq_buffers(self, nodes_buf, queues_buf):
        """
        Process buffers
        :param nodes_buf: str
        :type nodes_buf: str
        :param queues_buf: str
        :type queues_buf: str
        :return bool
        :rtype bool
        """

        self._process_nodes_buffer(nodes_buf)
        self._process_queues_buffer(queues_buf)

        # Signal started
        self.notify_value_n("k.rabbitmq.started", {"PORT": "default"}, 1)

        # Over
        return True

    def _process_nodes_buffer(self, s):
        """
        Process nodes buffers
        :param s: str
        :type s: str
        """

        # Init
        node_count = 0
        node_running_count = 0

        # Browse
        ar = s.split("\n")
        for cur_line in ar:
            # Clean and check
            cur_line = cur_line.strip()
            if len(cur_line) == 0:
                continue
            elif not cur_line.startswith("|"):
                continue

            # Ok split
            ar_temp = cur_line.split("|")
            logger.debug("Processing ar_temp=%s", ar_temp)

            # If we have "name", its the header, we bypass
            if ar_temp[1].strip() == "name":
                continue

            # Ok, got values
            v_running = ar_temp[3].strip()

            # Compute
            node_count += 1
            if v_running.lower() == "true":
                node_running_count += 1

        # Over
        self.notify_value_n("k.rabbitmq.node.count", {"PORT": "default"}, node_count)
        self.notify_value_n("k.rabbitmq.node.running.count", {"PORT": "default"}, node_running_count)

    # noinspection PyMethodMayBeStatic
    def _process_queues_buffer(self, s):
        """
        Process queues buffers
        :param s: str
        :type s: str
        """

        # per queue
        d_per_queue = dict()

        # Global dict
        d_global = dict()
        d_global["consumers"] = 0
        d_global["messages"] = 0
        d_global["message_ready"] = 0
        d_global["messages_unacknowledged"] = 0
        d_global["slave_nodes"] = 0
        d_global["synchronised_slave_nodes"] = 0

        # Global dict, rates
        d_global["backing_queue_status.avg_ack_egress_rate"] = 0.0
        d_global["backing_queue_status.avg_ack_ingress_rate"] = 0.0
        d_global["backing_queue_status.avg_egress_rate"] = 0.0
        d_global["backing_queue_status.avg_ingress_rate"] = 0.0
        d_global["message_stats.ack_details.rate"] = 0.0
        d_global["message_stats.confirm_details.rate"] = 0.0
        d_global["message_stats.deliver_details.rate"] = 0.0
        d_global["message_stats.deliver_get_details.rate"] = 0.0
        d_global["message_stats.deliver_no_ack_details.rate"] = 0.0
        d_global["message_stats.disk_reads_details.rate"] = 0.0
        d_global["message_stats.disk_writes_details.rate"] = 0.0
        d_global["message_stats.get_details.rate"] = 0.0
        d_global["message_stats.get_no_ack_details.rate"] = 0.0
        d_global["message_stats.publish_details.rate"] = 0.0
        d_global["message_stats.publish_in_details.rate"] = 0.0
        d_global["message_stats.publish_out_details.rate"] = 0.0
        d_global["message_stats.redeliver_details.rate"] = 0.0
        d_global["message_stats.return_unroutable_details.rate"] = 0.0
        d_global["messages_details.rate"] = 0.0
        d_global["messages_ready_details.rate"] = 0.0
        d_global["messages_unacknowledged_details.rate"] = 0.0
        d_global["reductions_details.rate"] = 0.0

        # Parse line by line
        for cur_line in s.split("\n"):
            # Clean and check
            cur_line = cur_line.strip()
            if len(cur_line) == 0:
                continue
            elif not cur_line.startswith("|"):
                continue

            # Ok split
            ar_temp = cur_line.split("|")
            logger.debug("Processing ar_temp=%s", ar_temp)

            # If we have "vhost", its the header, we bypass
            if ar_temp[1].strip() == "vhost":
                continue

            # Consumers and messages
            d = dict()
            queue = ar_temp[2].strip()

            d["consumers"] = ar_temp[4].strip()
            d["messages"] = ar_temp[7].strip()
            d["message_ready"] = ar_temp[8].strip()
            d["messages_unacknowledged"] = ar_temp[9].strip()
            d_per_queue[queue] = dict()

            # Cast to int
            for k, v in d.items():
                if len(v) > 0:
                    d[k] = int(v)
                else:
                    d[k] = 0

            # Nodes
            v_slave_nodes = ar_temp[11].strip()
            if len(v_slave_nodes) > 0:
                d["slave_nodes"] = len(v_slave_nodes.split(" "))
            else:
                d["slave_nodes"] = 0

            v_synchronised_slave_nodes = ar_temp[12].strip()
            if len(v_synchronised_slave_nodes) > 0:
                d["synchronised_slave_nodes"] = len(v_synchronised_slave_nodes.split(" "))
            else:
                d["synchronised_slave_nodes"] = 0

            # Rates (to float)
            for cur_name, cur_idx in RabbitmqStat.AR_QUEUES:
                cur_s = ar_temp[cur_idx].strip()
                # noinspection PyBroadException
                try:
                    d[cur_name] = float(cur_s)
                except Exception:
                    d[cur_name] = 0.0

            # Push to global
            for k, v in d.items():
                d_global[k] += v

            d_per_queue[queue] = d

        # Over
        for k, v in d_global.items():
            self.notify_value_n("k.rabbitmq.queue." + k, {"PORT": "default"}, v)
        for queue, counters in d_per_queue.items():
            additional_fields = {}
            for k in counters.keys():
                matches = self.FILTER_COUNTER_PER_QUEUE.match(k)
                if matches:
                    knock_key = "m.%s.persec" % matches.groups()[0]
                    additional_fields[knock_key] = counters[k]
            for k in ('messages',):
                self.notify_value_n("k.rabbitmq.per_queue." + k, {"PORT": "default", 'QUEUE': queue}, counters[k], d_values=additional_fields)
