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
import ujson

import re
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class VarnishStat(KnockProbe):
    """
    Probe
    """

    AR_CONFIG_FILE = [
        # Debian
        "/etc/default/varnish",
        # Varnish
        "/etc/varnish/varnish.params",
    ]

    KEYS = [
        # float => per second
        # int   => current (aka cur)
        # k.x   => internal

        # started :
        # 1  : RUNNING
        # 0  : FAILED

        # DOC
        # thread_queue_len      Length of session queue (INFO) Length of session queue waiting for threads. NB: Only updates once per second. See also parameter queue_max.
        # sess_queued           Sessions queued for thread (INFO) Number of times session was queued waiting for a thread. See also parameter queue_max.
        # sess_pipe_overflow    Count of sessions dropped due to the session pipe overflowing.
        # backend_conn          Backend conn. success (INFO)
        # backend_unhealthy     Backend conn. not attempted (INFO)
        # backend_busy          Backend conn. too many (INFO)
        # backend_fail          Backend conn. failures (INFO)
        # backend_reuse         Backend conn. reuses (INFO) Count of backend connection reuses  This counter is increased whenever we reuse a recycled connection.
        # backend_toolate       Backend conn. was closed (INFO)
        # backend_recycle       Backend conn. recycles (INFO) Count of backend connection recycles  This counter is increased whenever we have a keep-alive  connection that is put back into the pool of connections.  It has not yet been used, but it might be, unless the backend  closes it.
        # backend_retry         Backend conn. retry (INFO)

        # http://manpages.ubuntu.com/manpages/wily/man7/varnish-counters.7.html
        # man varnish-counters

        # TODO : From config : thread_pool_max / queue_max + compute percent usage

        # CURRENT : INTERNAL
        ("k.varnish.started", "int", "k.varnish.started"),

        # STAT Millis (Not so relevant at is goes to the stats socket, which is not the standard process pipeline of incoming request, but we add it for consistency)
        # This include the invocation stuff
        ("k.varnish.stat.ms", "float", "k.varnish.stat.ms"),

        # CURRENT : UPTIME
        ("MAIN.uptime", "int", "k.varnish.main.uptime"),
        ("MGT.uptime", "int", "k.varnish.mgt.uptime"),

        # PERSEC : SESSION
        ("MAIN.sess_conn", "float", "k.varnish.sess_conn"),
        ("MAIN.sess_drop", "float", "k.varnish.sess_drop"),
        ("MAIN.sess_fail", "float", "k.varnish.sess_fail"),
        ("MAIN.sess_pipe_overflow", "float", "k.varnish.sess_pipe_overflow"),
        ("MAIN.sess_queued", "float", "k.varnish.sess_queued"),
        ("MAIN.sess_dropped", "float", "k.varnish.sess_dropped"),

        # PER SEC : CACHE
        ("MAIN.cache_hit", "float", "k.varnish.cache_hit"),
        ("MAIN.cache_miss", "float", "k.varnish.cache_miss"),

        # COMPUTED : HIT RATE
        # (last("k.varnish.cache_hit[{#ID}]") + 1) / (last("k.varnish.cache_hit[{#ID}]") + last("k.varnish.cache_miss[{#ID}]") + 1)
        # custom multiplier : 100
        ("k.varnish.calc.cache_hit_rate", "computed", "k.varnish.calc.cache_hit_rate"),

        # PER SEC : BACKENDS
        ("MAIN.backend_conn", "float", "k.varnish.backend_conn"),
        ("MAIN.backend_unhealthy", "float", "k.varnish.backend_unhealthy"),
        ("MAIN.backend_busy", "float", "k.varnish.backend_busy"),
        ("MAIN.backend_fail", "float", "k.varnish.backend_fail"),
        ("MAIN.backend_reuse", "float", "k.varnish.backend_reuse"),
        ("MAIN.backend_toolate", "float", "k.varnish.backend_toolate"),
        ("MAIN.backend_recycle", "float", "k.varnish.backend_recycle"),
        ("MAIN.backend_retry", "float", "k.varnish.backend_retry"),

        # CURRENT : POOL, THREAD COUNT
        ("MAIN.pools", "int", "k.varnish.cur.pools"),
        ("MAIN.threads", "int", "k.varnish.cur.threads"),

        # CURRENT : SESSIONS WAITING FOR THREADS
        ("MAIN.thread_queue_len", "int", "k.varnish.cur.thread_queue_len"),

        # PER SEC : THREADS
        ("MAIN.threads_limited", "float", "k.varnish.threads_limited"),
        ("MAIN.threads_created", "float", "k.varnish.threads_created"),
        ("MAIN.threads_destroyed", "float", "k.varnish.threads_destroyed"),
        ("MAIN.threads_failed", "float", "k.varnish.threads_failed"),

        # PER SEC : SESSION, REQ, BACKEND REQ
        ("MAIN.s_sess", "float", "k.varnish.req.sess"),
        ("MAIN.s_req", "float", "k.varnish.req.req"),
        ("MAIN.backend_req", "float", "k.varnish.req.backend"),

        # SKIP CHILD PROCESS -> we use uptime
        ("MGT.child_start", "skip", "k.varnish.child_start"),
        ("MGT.child_exit", "skip", "k.varnish.child_exit"),
        ("MGT.child_stop", "skip", "k.varnish.child_stop"),
        ("MGT.child_died", "skip", "k.varnish.child_died"),
        ("MGT.child_dump", "skip", "k.varnish.child_dump"),
        ("MGT.child_panic", "skip", "k.varnish.child_panic"),

        # SKIP (hit/miss enough)
        ("MAIN.cache_hitpass", "skip", "k.varnish.cache_hitpass"),
    ]

    def __init__(self):
        """
        Constructor
        """

        KnockProbe.__init__(self)

        self.category = "/web/varnish"

    # noinspection PyMethodMayBeStatic
    def try_load_json(self):
        """
        Try to load varnishstat -j
        :return: dict,None
        :rtype dict,None
        """

        logger.info("Invoke varnishstat -j now")
        ms_start = SolBase.mscurrent()
        ec, so, se = ButcherTools.invoke("varnishstat -j")
        ms = SolBase.msdiff(ms_start)
        if ec != 0:
            logger.warn("varnishstat -j invoke failed (requires varnish >= 3.0.7), ec=%s, so=%s, se=%s", ec, so, se)
            return None

        # Process
        try:
            logger.info("Json loads now")
            d_json = ujson.loads(so)
            logger.info("Json loaded, d_json=%s", d_json)

            # Append millis
            d_json["k.varnish.stat.ms"] = {u"flag": u"dummy", u"type": u"dummy", u"description": u"dummy", u"value": ms}

            # Ok
            return d_json
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            return None

    # noinspection PyMethodMayBeStatic
    def try_load_text(self):
        """
        Try to load varnishstat -1
        :return: dict,None
        :rtype dict,None
        """

        logger.info("Invoke varnishstat -1 now")
        ms_start = SolBase.mscurrent()
        ec, so, se = ButcherTools.invoke("varnishstat -1")
        ms = SolBase.msdiff(ms_start)
        if ec != 0:
            logger.warn("varnishstat -1 invoke failed, ec=%s, so=%s, se=%s", ec, so, se)
            return None

        # Process
        d_json = dict()
        try:
            logger.info("Text parsing loads now")
            # Remove multiple spaces
            buf = re.sub(" +", " ", so)

            # Split
            ar_buf = buf.split("\n")

            # Browse
            for b in ar_buf:
                # Got :
                # Symbolic entry name
                # Value
                # Per-second average over process lifetime, or a period if the value can not be averaged
                # Descriptive text

                # Skip empty
                b = b.strip()
                if len(b) == 0:
                    continue

                # Split
                ar_temp = b.split(" ")

                # Get
                name = ar_temp[0]
                v = ar_temp[1]

                # Simulate a json output (we use value only)
                d_json[name] = dict()
                d_json[name]["value"] = v

            # Ok
            logger.info("Json loaded, d_json=%s", d_json)

            # Append millis
            d_json["k.varnish.stat.ms"] = {u"flag": u"dummy", u"type": u"dummy", u"description": u"dummy", u"value": ms}

            # Over
            return d_json
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            return None

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Exec
        """

        located_f = None
        for cur_f in VarnishStat.AR_CONFIG_FILE:
            if FileUtility.is_file_exist(cur_f):
                located_f = cur_f
                logger.info("Located located_f=%s", located_f)
                break

        if not located_f:
            logger.info("Give up (no file found in %s)", VarnishStat.AR_CONFIG_FILE)
            return

        logger.info("Varnish detected (%s found)", located_f)

        # -------------------------------
        # P0 : Fire discoveries
        # -------------------------------
        logger.info("Firing discoveries (default)")
        pool_id = "default"
        self.notify_discovery_n("k.varnish.discovery", {"ID": pool_id})

        # -------------------------------
        # We support varnish 3.0.7 json
        # With fallback to text only for previous versions
        # -------------------------------

        # Process
        try:
            d_json = self.try_load_json()

            # Try text if failed
            if not d_json:
                d_json = self.try_load_text()

            # Check if we have stuff
            if not d_json:
                logger.warn("varnishstat invoke failed (no d_json), notify instance down and give up")
                self.notify_value_n("k.varnish.started", {"ID": pool_id}, 0)
                return

            # Ok
            self.process_json(d_json, pool_id)

        except Exception as e:
            # FAILED
            logger.warn("varnishstat processing failed, notify instance down and give up, ex=%s", SolBase.extostr(e))
            self.notify_value_n("k.varnish.started", {"ID": pool_id}, 0)

    def process_json(self, d_json, pool_id):
        """
        Process json dict
        :param d_json: dict
        :type d_json: dict
        :param pool_id: str
        :type pool_id: str
        """

        logger.info("Json loaded, d_json=%s", d_json)

        logger.info("Invoke reply ok, firing notify now")
        for k, knock_type, knock_key in VarnishStat.KEYS:
            # Try
            if k not in d_json:
                if k.find("k.varnish.") != 0:
                    logger.warn("Unable to locate k=%s in d_json", k)
                else:
                    logger.info("Unable to locate k=%s in d_json (this is expected)", k)
                continue

            # Ok, fetch and cast
            v = d_json[k]["value"]
            if knock_type == "int":
                v = int(v)
            elif knock_type == "float":
                v = float(v)
            elif knock_type == "str":
                v = str(v)
            elif knock_type == "skip":
                logger.debug("Skipping type=%s", knock_type)
                continue
            else:
                logger.warn("Not managed type=%s", knock_type)

            # Notify
            self.notify_value_n(knock_key, {"ID": pool_id}, v)

        # Good, notify & exit
        logger.info("varnishstat ok, notify started=1 and return, pool_id=%s", pool_id)
        self.notify_value_n("k.varnish.started", {"ID": pool_id}, 1)
