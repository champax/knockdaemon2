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

import glob
import json
import logging

import re
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class UwsgiStat(KnockProbe):
    """
    Probe
    """
    AR_UWSGI_CONF = [
        # Debian
        "/usr/share/uwsgi/conf/default.ini",
        # Centos
        "/etc/uwsgi.ini",
    ]

    KEYS = [
        # float => per second
        # int   => current (aka cur)
        # k.x   => internal

        # STARTED
        ("k.uwsgi.started", "int", "k.uwsgi.started"),

        # STAT Millis (Not so relevant at is goes to the stats socket, which is not the standard process pipeline of incoming request, but we add it for consistency)
        # This include the invocation stuff
        ("k.uwsgi.stat.ms", "float", "k.uwsgi.stat.ms"),

        # GLOBAL : current queues
        ("uwsgi.global.listen_queue", "int", "k.uwsgi.cur.listen_queue"),
        ("uwsgi.global.signal_queue", "int", "k.uwsgi.cur.signal_queue"),

        # LOCKS : Current counts
        ("uwsgi.locks.total_lock_count", "int", "k.uwsgi.locks.cur.count"),

        # SOCKET : current queue/count
        ("uwsgi.sockets.queue", "int", "k.uwsgi.soc.cur.queue"),
        ("uwsgi.sockets.s_count", "int", "k.uwsgi.soc.cur.count"),

        # CORE : count
        ("uwsgi.cores.c_count", "int", "k.uwsgi.cores.cur.count"),

        # CORE : count in_request / idle (computed)
        ("uwsgi.cores.in_request", "int", "k.uwsgi.cores.cur.in_request"),
        ("uwsgi.cores.idle", "int", "k.uwsgi.cores.cur.idle"),

        # CORE : req/sec
        ("uwsgi.cores.offloaded_requests", "float", "k.uwsgi.cores.ps.offloaded_requests"),
        ("uwsgi.cores.routed_requests", "float", "k.uwsgi.cores.ps.routed_requests"),
        ("uwsgi.cores.static_requests", "float", "k.uwsgi.cores.ps.static_requests"),

        # CORE : error/sec
        ("uwsgi.cores.read_errors", "float", "k.uwsgi.cores.read_errors"),
        ("uwsgi.cores.write_errors", "float", "k.uwsgi.cores.write_errors"),

        # WORKERS : count
        ("uwsgi.workers.w_count", "int", "k.uwsgi.workers.cur.count"),

        # WORKERS : currents (SKIP, need configs)
        ("uwsgi.workers.rss", "skip", "k.uwsgi.workers.cur.rss"),
        ("uwsgi.workers.vsz", "skip", "k.uwsgi.workers.cur.vsz"),

        # WORKERS : currents
        ("uwsgi.workers.signal_queue", "int", "k.uwsgi.workers.cur.signal_queue"),

        # WORKERS : currents : average response time (float)
        ("uwsgi.workers.avg_rt", "float", "k.uwsgi.workers.cur.avg_rt"),

        # WORKERS : scoreboard (great ^^)
        ("uwsgi.workers.status_busy", "int", "k.uwsgi.workers.sc.busy"),
        ("uwsgi.workers.status_cheap", "int", "k.uwsgi.workers.sc.cheap"),
        ("uwsgi.workers.status_idle", "int", "k.uwsgi.workers.sc.idle"),
        ("uwsgi.workers.status_pause", "int", "k.uwsgi.workers.sc.pause"),
        ("uwsgi.workers.status_sig", "int", "k.uwsgi.workers.sc.sig"),

        # WORKERS : per sec
        ("uwsgi.workers.exceptions", "float", "k.uwsgi.workers.ps.exceptions"),
        ("uwsgi.workers.harakiri_count", "float", "k.uwsgi.workers.ps.harakiri_count"),
        ("uwsgi.workers.requests", "float", "k.uwsgi.workers.ps.requests"),
        ("uwsgi.workers.signals", "float", "k.uwsgi.workers.ps.signals"),

        # WORKERS : tx / sec
        ("uwsgi.workers.tx", "float", "k.uwsgi.workers.ps.tx"),
    ]

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)

        self.category = "/app/uwsgi"

        # Aggregate dict
        self.d_uwsgi_aggregate = dict()

        # Total worker count accross all instance
        self._total_avg_rt = 0
        self._total_workers_count = 0

    # noinspection PyMethodMayBeStatic
    def _get_stuff_from_file(self, file_name, stuff):
        """
        Get stats socket from file
        :param stuff: str
        :type stuff: str
        :param file_name: str
        :type file_name: str
        :return: str,None
        :rtype str,None
        """

        try:

            # Check
            logger.info("Checking file_name=%s", file_name)
            if not FileUtility.is_file_exist(file_name):
                logger.debug("No stuff found (conf missing), file_name=%s", file_name)
                return None

            # Load
            logger.info("Loading file_name=%s", file_name)
            buf = FileUtility.file_to_textbuffer(file_name, "ascii")
            if not buf:
                logger.info("No stuff found (no buf, no read), file_name=%s", file_name)
                return None

            # Split
            ar = buf.split("\n")

            # Browse
            stuff_found = None
            count = 0
            for line in ar:
                line = line.strip()
                if len(line) == 0:
                    continue

                if line.startswith(stuff):
                    ar_temp = line.split("=", 1)
                    if len(ar_temp) != 2:
                        logger.warning("Found, split failed, stuff_found=%s, ar_temp=%s", stuff_found, ar_temp)
                    else:
                        stuff_found = ar_temp[1].strip()
                        logger.info("Found, stuff_found=%s", stuff_found)
                        count += 1

            if count > 1:
                logger.warn("Found multiple stuff in buffer, count=%s", count)

            logger.info("Return stuff=%s, stuff_found=%s", stuff, stuff_found)
            return stuff_found

        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            return None

    def _uwsgi_buffer_merge(self, d_uwsgi):
        """
        Merge uwsgi stat buffer
        :param d_uwsgi: d_uwsgi buffer (from uwsgi)
        :type d_uwsgi: dict
        :return: merged dict
        :rtype dict
        """

        # Well, the doc is... hummm, in code
        # Some references...
        # http://www.cnblogs.com/codeape/p/4015872.html

        # Ok, so... We got something like :
        # {
        # "version": "2.0.7-debian",
        # "listen_queue": 0,
        # "listen_queue_errors": 0,
        # "signal_queue": 0,
        # "load": 0,
        # "pid": 74133,
        # "uid": 33,
        # "gid": 33,
        # "cwd": "/var/www/totoo_frontends",
        # "locks": [{"user 0": 0}, { "signal": 0 }, { "filemon": 0 }, { "timer": 0 }, { "rbtimer": 0 }, { "cron": 0 }, { "rpc": 0 }, { "snmp": 0 } ],
        # "sockets": [
        #   {
        #     "name": "/run/uwsgi/app/totoo_frontends/socket",
        #     "proto": "uwsgi",
        #     "queue": 0,
        #     "max_queue": 0,
        #     "shared": 0,
        #     "can_offload": 0
        #   },
        #   .......
        # ],
        # "workers": [
        #   {
        #     "id": 1, "pid": 74141, "accepting": 1, "requests": 0, "delta_requests": 0, "exceptions": 0, "harakiri_count": 0, "signals": 0, "signal_queue": 0, "status": "idle", "rss": 0, "vsz": 0, "running_time": 0, "last_spawn": 1462230277, "respawn_count": 1, "tx": 0, "avg_rt": 0,
        #     "apps": [],
        #     "cores": [
        #       {
        #         "id": 0,
        #         "requests": 0,
        #         "static_requests": 0,
        #         "routed_requests": 0,
        #         "offloaded_requests": 0,
        #         "write_errors": 0,
        #         "read_errors": 0,
        #         "in_request": 0,
        #         "vars": [
        #         ]
        #       }
        #     ]
        #   },
        #   ......

        # --------------------------------
        # A) Output dict
        # --------------------------------
        d_acc_global = dict()
        d_acc_lock = dict()
        d_acc_socket = dict()
        d_acc_worker = dict()
        d_acc_core = dict()

        # --------------------------------
        # B) Process everything
        # - acc_global:
        # => listen_queue (skip)       the maximum value of queues in sockets
        # => signal_queue (skip)       length of master(worker0)"s signal queue
        # --------------------------------
        d_acc_global["listen_queue"] = d_uwsgi["listen_queue"]
        d_acc_global["signal_queue"] = d_uwsgi["signal_queue"]

        # --------------------------------
        # - acc_lock:
        # => total_lock_count (sum)    total lock counts accross all locks
        # --------------------------------
        d_acc_lock["total_lock_count"] = 0
        for d_lock in d_uwsgi["locks"]:
            for k, v in d_lock.iteritems():
                logger.debug("Processing, lock, k=%s, v=%s", k, v)
                d_acc_lock["total_lock_count"] += v

        # --------------------------------
        # - acc_socket
        # => s_count
        # => queue (sum)
        # --------------------------------
        d_acc_socket["s_count"] = 0
        d_acc_socket["queue"] = 0
        for d_socket in d_uwsgi["sockets"]:
            d_acc_socket["s_count"] += 1
            d_acc_socket["queue"] += d_socket["queue"]

        # --------------------------------
        # - acc_worker
        # => w_count (sum 1)
        # => requests (sum)             total request counts
        # => exceptions (sum)           total core ex
        # => harakiri_count (sum)       total harakiri count (we should set a trigger is this is zero ^^)
        # => signals (sum)              number of managed uwsgi signals
        # => signal_queue (sum)         uwsgi signals queue
        # => rss (sum)                  RSS memory (bytes)
        # => vsz (sum)                  address space (bytes)
        # => tx (sum)                   transmitted data
        # => avg_rt (hum hum)           average response time for the worker (in micro seconds) => will sum it, then divide it by w_count at the end
        # => status_idle (sum)
        # => status_busy (sum)
        # => status_pause (sum)
        # => status_cheaped (sum)
        # => status_sig (sum)
        # Notes on status
        # "idle" -> waiting for connection
        # "cheap" -> not running (cheaped)
        # "pause" -> paused (SIGTSTP)
        # # "sig" -> running a signal handler
        # "busy" -> running a request
        # --------------------------------
        d_acc_worker["w_count"] = 0
        d_acc_worker["requests"] = 0
        d_acc_worker["exceptions"] = 0
        d_acc_worker["harakiri_count"] = 0
        d_acc_worker["signals"] = 0
        d_acc_worker["signal_queue"] = 0
        d_acc_worker["rss"] = 0
        d_acc_worker["vsz"] = 0
        d_acc_worker["tx"] = 0
        d_acc_worker["avg_rt"] = 0
        d_acc_worker["status_idle"] = 0
        d_acc_worker["status_busy"] = 0
        d_acc_worker["status_pause"] = 0
        d_acc_worker["status_cheap"] = 0
        d_acc_worker["status_sig"] = 0
        total_status = 0
        for d_workers in d_uwsgi["workers"]:
            d_acc_worker["w_count"] += 1
            d_acc_worker["requests"] += d_workers["requests"]
            d_acc_worker["exceptions"] += d_workers["exceptions"]
            d_acc_worker["harakiri_count"] += d_workers["harakiri_count"]
            d_acc_worker["signals"] += d_workers["signals"]
            d_acc_worker["signal_queue"] += d_workers["signal_queue"]
            d_acc_worker["rss"] += d_workers["rss"]
            d_acc_worker["vsz"] += d_workers["vsz"]
            d_acc_worker["tx"] += d_workers["tx"]
            # Micro to millis here
            d_acc_worker["avg_rt"] += (d_workers["avg_rt"] / 1000.0)
            # Status processing
            key = "status_" + d_workers["status"]
            if key not in d_acc_worker:
                logger.warn("Un-managed worker status key=%s, d_workers=%s", key, d_workers)
            else:
                d_acc_worker[key] += 1
                total_status += 1

        # Check status vs workers count (log only)
        if total_status != d_acc_worker["w_count"]:
            logger.warn("Mismatch, w_count=%s, total_status=%s", d_acc_worker["w_count"], total_status)

        # Post process avg_rt for ALL instance
        self._total_avg_rt += d_acc_worker["avg_rt"]
        self._total_workers_count = d_acc_worker["w_count"]

        # Post process avg_rt
        # It is already a processing average, we average it again :(
        if d_acc_worker["w_count"] > 0:
            d_acc_worker["avg_rt"] = d_acc_worker["avg_rt"] / d_acc_worker["w_count"]
        else:
            d_acc_worker["avg_rt"] = 0

        # --------------------------------
        # - acc_core
        # => c_count (sum 1)
        # => static_requests (sum)      total static requests (file server mode, i never used it....)
        # => routed_requests (sum)      total routed requests (routing mode, i never used it....)
        # => offloaded_requests (sum)   total offloaded request
        # => write_errors (sum)
        # => read_errors (sum)
        # => in_request (sum)           1 : processing request, 0 : not processing
        # --------------------------------
        d_acc_core["c_count"] = 0
        d_acc_core["static_requests"] = 0
        d_acc_core["routed_requests"] = 0
        d_acc_core["offloaded_requests"] = 0
        d_acc_core["write_errors"] = 0
        d_acc_core["read_errors"] = 0
        d_acc_core["in_request"] = 0
        # Yeah i know, i re-browse again, shut-up basterds
        for d_workers in d_uwsgi["workers"]:
            for d_core in d_workers["cores"]:
                d_acc_core["c_count"] += 1
                d_acc_core["static_requests"] += d_core["static_requests"]
                d_acc_core["routed_requests"] += d_core["routed_requests"]
                d_acc_core["offloaded_requests"] += d_core["offloaded_requests"]
                d_acc_core["write_errors"] += d_core["write_errors"]
                d_acc_core["read_errors"] += d_core["read_errors"]
                d_acc_core["in_request"] += d_core["in_request"]

        # Post process : idle
        d_acc_core["idle"] = d_acc_core["c_count"] - d_acc_core["in_request"]

        # --------------------------------
        # C) Merge everything in output dict, with key prefixes
        # (yeah dirty, but my brain is in better condition with previous code than direct addressing - for complains, contact the moon)
        # --------------------------------
        d_out = dict()
        for k, v in d_acc_global.iteritems():
            d_out["uwsgi.global." + k] = v

        for k, v in d_acc_lock.iteritems():
            d_out["uwsgi.locks." + k] = v

        for k, v in d_acc_socket.iteritems():
            d_out["uwsgi.sockets." + k] = v

        for k, v in d_acc_worker.iteritems():
            d_out["uwsgi.workers." + k] = v

        for k, v in d_acc_core.iteritems():
            d_out["uwsgi.cores." + k] = v

        # Over, debugs plz
        for k, v in d_out.iteritems():
            logger.debug("OUTPUT : %s => %s", k, v)

        # Fatality
        return d_out

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Execute
        """

        # Reset (we persist accross run, this is critical)
        self.d_uwsgi_aggregate = dict()
        self._total_avg_rt = 0
        self._total_workers_count = 0

        # Conf
        located_f = None
        for cur_f in UwsgiStat.AR_UWSGI_CONF:
            # Check if uwsgi is here (todo : better stuff plz)
            if FileUtility.is_file_exist(cur_f):
                located_f = cur_f

        if not located_f:
            logger.info("No uwsgi (no file in %s)", UwsgiStat.AR_UWSGI_CONF)
            return

        logger.info("Located uwsgi, located_f=%s", located_f)

        # Default stats soc
        default_stats_soc = self._get_stuff_from_file(located_f, "stats")

        # ---------------------------
        # B) DETECT INSTANCES AND PROCESS THEM
        # ---------------------------

        conf_files = glob.glob("/etc/uwsgi/apps-enabled/*.ini") + glob.glob("/etc/uwsgi.d/*.ini")
        for cur_app_file in conf_files:
            # -----------------------
            # B1) Fetch app id
            # -----------------------
            logger.info("Processing cur_app_file=%s", cur_app_file)

            # Fetch
            cur_uwsgi_id = self._get_stuff_from_file(cur_app_file, "id")
            if not cur_uwsgi_id:
                logger.warn("Cannot locate id, cur_app_file=%s", cur_app_file)
                continue

            # -----------------------
            # B1_BIS) Fire Discovery ASAP
            # -----------------------
            uwsgi_instance_list = list()
            d_instance_cur = dict()
            d_instance_cur["{#ID}"] = cur_uwsgi_id
            uwsgi_instance_list.append(d_instance_cur)
            self.notify_discovery_n("k.uwsgi.discovery", {"ID": cur_uwsgi_id})

            # -----------------------
            # B1_TER) Locate "stats" in config
            # -----------------------
            # Fetch
            cur_stats_soc = self._get_stuff_from_file(cur_app_file, "stats")

            # Select soc
            if default_stats_soc:
                # ???
                effective_stats_soc = re.sub("%\(deb-confname\)", cur_uwsgi_id, default_stats_soc)
            elif cur_stats_soc:
                effective_stats_soc = cur_stats_soc
            else:
                # No stats
                logger.info("No stats, signal down and reloop")
                self._push_result("k.uwsgi.started", cur_uwsgi_id, 0)
                continue

            # -----------------------
            # B2) STAT FETCH FROM SOCKET
            # -----------------------

            # Go bash
            ms_stat_start = SolBase.mscurrent()
            ec, so, se = ButcherTools.invoke("uwsgi --connect-and-read " + effective_stats_soc)
            ms_stat = SolBase.msdiff(ms_stat_start)
            if ec != 0:
                logger.warning("Invoke fail, go sudo, ex=%s, so=%s, se=%s", ec, so, se)
                ec, so, se = ButcherTools.invoke("sudo uwsgi --connect-and-read " + effective_stats_soc)
                if ec != 0:
                    logger.warning("Invoke fail, give up, ex=%s, so=%s, se=%s", ec, so, se)
                    continue

            # Log
            logger.debug("Got ec=%s, so=%s, se=%s", ec, repr(so), repr(se))

            # Check
            if len(se) == 0:
                logger.warn("No se, give up")
                continue

            # -----------------------
            # B3) JSON AND MERGE
            # -----------------------
            d_json = json.loads(se)

            d_uwsgi = self._uwsgi_buffer_merge(d_json)

            # Append response time
            d_uwsgi["k.uwsgi.stat.ms"] = ms_stat

            # -----------------------
            # B4) BROWSE RESULT AND PUSH DATAS
            # -----------------------

            # Socket ok, parsing ok, merge ok : instance up
            self._push_result("k.uwsgi.started", cur_uwsgi_id, 1)

            # Browse our stuff and try to locate
            for k, knock_type, knock_key in UwsgiStat.KEYS:
                # Important : we have a 2 layers keys

                # Try
                if k not in d_uwsgi:
                    if k.find("k.uwsgi.") != 0:
                        logger.warn("Unable to locate k=%s in d_out", k)
                    continue

                # Ok, fetch and cast
                v = d_uwsgi[k]
                if knock_type == "int":
                    v = int(v)
                elif knock_type == "float":
                    v = float(v)
                elif knock_type == "skip":
                    continue
                else:
                    logger.warn("Not managed type=%s", knock_type)

                # Use our wrapper (will populate d_uwsgi_aggregate)
                self._push_result(knock_key, cur_uwsgi_id, v)

        # ---------------------------
        # B) PROCESS "ALL" AGGREGATE INSTANCE
        # ---------------------------

        if len(self.d_uwsgi_aggregate) == 0:
            # Go nothing, possible no uwsgi instance, over
            logger.info("No d_uwsgi_aggregate, give up")
            return

        # Notify disco
        self.notify_discovery_n("k.uwsgi.discovery", {"ID": "ALL"})

        # Aggreg firing
        for k, v in self.d_uwsgi_aggregate.iteritems():
            if k == "k.uwsgi.started":
                # For uwsgi aggregate, push 1 always # TODO : Check this
                v = 1
            elif k == "k.uwsgi.workers.cur.avg_rt":
                # For avg_rt, compute directly and bypass stuff (ALL instance only)
                if self._total_workers_count > 0:
                    v = self._total_avg_rt / self._total_workers_count
                else:
                    v = 0
                logger.info("ALL : Computed avg_rt=%s, total_rt=%s, total_workers=%s", v, self._total_avg_rt, self._total_workers_count)

            # And notify
            self.notify_value_n(k, {"ID": "ALL"}, v)

    def _push_result(self, key, uwsgi_id, value):
        """
        Push a value and keep "self.d_uwsgi_aggregate" up-to-date
        :param key; str
        :type key: str
        ;param uwsgi_id: str
        :type uwsgi_id: str
        :param value: object
        :type value: object
        """

        # Fire
        self.notify_value_n(key, {"ID": uwsgi_id}, value)

        # Keep up to date (sum for all)
        if key not in self.d_uwsgi_aggregate:
            self.d_uwsgi_aggregate[key] = value
        else:
            self.d_uwsgi_aggregate[key] += value
