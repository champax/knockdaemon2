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
from threading import Lock

import gevent
from gevent.queue import Empty
from greenlet import GreenletExit
from influxdb import InfluxDBClient
from influxdb.line_protocol import make_lines
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolmeters.Meters import Meters

from knockdaemon2.Core.Tools import Tools
from knockdaemon2.Transport.Dedup import Dedup
from knockdaemon2.Transport.KnockTransport import KnockTransport

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


class InfluxAsyncTransport(KnockTransport):
    """
    Influx Http transport
    """

    QUEUE_WAIT_SEC_PER_LOOP = None

    def __init__(self):
        """
        Constructor
        """

        self._http_client = HttpClient()

        self._influx_mode = "knock"
        self._influx_timeout_ms = 20000
        self._influx_host = None
        self._influx_port = None
        self._influx_login = None
        self._influx_password = None
        self._influx_database = None
        self._influx_ssl = False
        self._influx_ssl_verify = False
        self._influx_db_created = False
        self._influx_dedup = True

        # Locker
        self._locker = Lock()

        # Run
        self._is_running = False
        self._greenlet = None
        self._dt_last_send = SolBase.datecurrent()

        # Dedup
        self.dedup_instance = Dedup()
        self.last_http_ok_ms = SolBase.mscurrent()

        # Wait ms if send is bypassed before re-trying
        self._http_send_bypass_wait_ms = 1000

        # Minimum http send interval. If reached, a send will occurs
        # (even if _http_send_max_bytes is not reached).
        self._http_send_min_interval_ms = 60000

        # Upon http failure, time to wait before next http request
        # Recommended : _http_send_min_interval_ms*2
        self._http_ko_interval_ms = 10000

        # Max items in send queue (if reached, older items are kicked)
        self._max_items_in_queue = 36000

        # Call base
        KnockTransport.__init__(self)

        # Override
        self.meters_prefix = "influxasync_"
        self.load_http_uri = False

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

        # Call base, hacking autostart
        KnockTransport.init_from_config(self, d_yaml_config, d, auto_start=False)

        # Load our stuff
        self._influx_host = d["influx_host"]
        self._influx_port = d["influx_port"]
        self._influx_login = d["influx_login"]
        self._influx_password = d["influx_password"]
        self._influx_database = d["influx_database"]
        self._influx_ssl = d["influx_ssl"]
        self._influx_ssl_verify = d["influx_ssl_verify"]

        try:
            self._http_send_bypass_wait_ms = d["http_send_bypass_wait_ms"]
        except KeyError:
            logger.debug("Key http_send_bypass_wait_ms not present, using default, d=%s", d)

        try:
            self._http_send_min_interval_ms = d["http_send_min_interval_ms"]
        except KeyError:
            logger.debug("Key http_send_min_interval_ms not present, using default, d=%s", d)

        try:
            self._max_items_in_queue = d["max_items_in_queue"]
        except KeyError:
            logger.debug("Key max_items_in_queue not present, using default, d=%s", d)

        try:
            self._http_ko_interval_ms = d["http_ko_interval_ms"]
        except KeyError:
            logger.debug("Key http_ko_interval_ms not present, using default, d=%s", d)

        # Mode : "knock" or "influx"
        self._influx_mode = d.get("influx_mode", "knock")
        if self._influx_mode not in ["knock", "influx"]:
            raise Exception("Invalid _influx_mode={0}, need 'knock' or 'influx'".format(self._influx_mode))

        # Timeout
        self._influx_timeout_ms = int(d.get("influx_timeout_ms", 20000))

        # Dedup
        self._influx_dedup = bool(d.get("influx_dedup", True))

        # Override meter prefix
        self.meters_prefix = "influxasync_" + self._influx_host + "_" + str(self._influx_port) + "_"

        logger.info("influx_ssl: %s", self._influx_ssl)
        logger.info("influx_host: %s", self._influx_host)

        # Logs
        lifecyclelogger.info("_influx_mode=%s", self._influx_mode)
        lifecyclelogger.info("_influx_timeout_ms=%s", self._influx_timeout_ms)
        lifecyclelogger.info("_influx_host=%s", self._influx_host)
        lifecyclelogger.info("_influx_port=%s", self._influx_port)
        lifecyclelogger.info("_influx_login=%s", self._influx_login)
        lifecyclelogger.info("_influx_password=%s", self._influx_password)
        lifecyclelogger.info("_influx_database=%s", self._influx_database)
        lifecyclelogger.info("_influx_ssl=%s", self._influx_ssl)
        lifecyclelogger.info("_influx_ssl_verify=%s", self._influx_ssl_verify)

        # Autostart hack : finish him
        if auto_start:
            self.greenlet_start()

    def greenlet_start(self):
        """
        Start
        """

        with self._locker:
            # Signal
            logger.info("Send Greenlet : starting")
            self._is_running = True

            # Check
            if self._greenlet:
                logger.warning("_greenlet already set, doing nothing")
                return

            # Fire
            self._greenlet = gevent.spawn(self.greenlet_run)
            logger.info("Send greenlet : started")

    def greenlet_stop(self):
        """
        Stop
        """

        with self._locker:
            # Signal
            logger.info("Send greenlet : stopping")
            self._is_running = False

            # Check
            if not self._greenlet:
                logger.warning("_greenlet not set, doing nothing")
                return

            # Kill
            logger.info("_greenlet.kill")
            self._greenlet.kill()
            logger.info("_greenlet.kill done")
            # gevent.kill(self._greenlet)
            self._greenlet = None
            logger.info("Send greenlet : stopped")

    def greenlet_run(self):
        """
        Run
        """
        try:
            logger.info("Entering loop")
            while self._is_running:
                try:
                    # ------------------------------
                    # Wait for the queue
                    # ------------------------------
                    logger.debug("Queue : Waiting")
                    try:
                        # Call (blocking)
                        self._queue_to_send.peek(True, self.QUEUE_WAIT_SEC_PER_LOOP)
                    except Empty:
                        # Next try
                        SolBase.sleep(0)
                        continue

                    # ------------------------------
                    # GOT SOMETHING IN THE QUEUE, TRY TO SEND
                    # ------------------------------

                    logger.debug("Queue : Signaled")
                    go_fast = self._try_send_to_http()
                    if not go_fast:
                        SolBase.sleep(self._http_send_bypass_wait_ms)
                except GreenletExit:
                    logger.debug("GreenletExit in loop2")
                    return
                except Exception as e:
                    logger.warning("Exception in loop2=%s", SolBase.extostr(e))
                    continue
        except GreenletExit:
            logger.debug("GreenletExit in loop1")
        finally:
            logger.info("Exiting loop")

    def stop(self):
        """
        Stop
        """

        # Stop
        self.greenlet_stop()

    def _requeue_pending_array(self, ar_pending):
        """
        Requeue pending array at head for re-emission on next http try
        :param ar_pending: list
        :type ar_pending: list
        """

        q_in = self._queue_to_send.qsize()

        ms_start = SolBase.mscurrent()
        ar_pending.reverse()
        ms_reverse = SolBase.msdiff(ms_start)

        ms_start = SolBase.mscurrent()
        for item in ar_pending:
            self._queue_to_send.queue.appendleft(item)
        ms_requeue = SolBase.msdiff(ms_start)

        logger.debug(
            "Re-queued, ms_reverse=%s, ms_requeue=%s, ar_pending.len=%s, q.len.in/out=%s/%s",
            ms_reverse, ms_requeue,
            len(ar_pending), q_in,
            self._queue_to_send.qsize())

    def process_notify(self, account_hash, node_hash, notify_values):
        """
        Process notify
        :param account_hash: Hash bytes to value
        :type account_hash; dict
        :param node_hash: Hash bytes to value
        :type node_hash; dict
        :param notify_values: List of (counter_key, d_tags, counter_value, ts, d_values). Cleared upon success.
        :type notify_values; list
        """

        # If not running, exit
        if not self._is_running:
            logger.warning("Not running, processing not possible")
            return False

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
        # list : List of (counter_key, d_tags, counter_value, ts, d_values). Cleared upon success.

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

        # ---------------------------
        # DEDUP
        # ---------------------------

        if self._influx_dedup:
            logger.info("dedup on (this is experimental)")
            # Compute limit ms (we keep margin, so we got on the past, based on last http ok and http interval)
            limit_ms = self.last_http_ok_ms - (self._http_send_min_interval_ms * 2)

            # Dedup incoming
            remaining_notify_values = self.dedup_instance.dedup(notify_values=notify_values, limit_ms=limit_ms)
        else:
            logger.info("dedup off")
            remaining_notify_values = notify_values

        # ---------------------------
        # PROCESS NORMALLY
        # ---------------------------

        # We build influx format
        ar_influx = Tools.to_influx_format(account_hash, node_hash, remaining_notify_values)

        # Influxdb python client do not support firing pre-serialized json
        # So we use the line protocol
        # We serialize this block right now in a single line buffer
        d_points = {"points": ar_influx}
        buf = make_lines(d_points, precision=None).encode('utf8')

        # Check max
        if self._queue_to_send.qsize() >= self._max_items_in_queue:
            # Too much, kick
            logger.warning("Max queue reached, discarding older item")
            self._queue_to_send.get(block=True)
            Meters.aii(self.meters_prefix + "knock_stat_transport_queue_discard")
        elif self._queue_to_send.qsize() == 0:
            # We were empty, we add a new one.
            # To avoid firing http asap, override last send date now
            self._dt_last_send = SolBase.datecurrent()

        # Put
        logger.debug("Queue : put")
        self._queue_to_send.put(buf)

        # Max queue size
        Meters.ai(self.meters_prefix + "knock_stat_transport_queue_max_size").set(max(self._queue_to_send.qsize(), Meters.aig(self.meters_prefix + "knock_stat_transport_queue_max_size")))

        # Done
        return True

    def _try_send_to_http(self):
        """
        Check if we can send the pending queue to server
        :return bool
        :rtype bool
        """

        # NOTE :
        # _queue_to_send : it's a queue of  pre-serialized line buffer (binary buffer) to send
        # So, _queue_to_send => queue of list(bytes)

        try:
            ms_extract = SolBase.mscurrent()

            # Boolean (for unittest)
            self._http_pending = True

            # Try to pump
            buf_pending_array = list()
            buf_pending_length = 0
            while True:
                # Get
                try:
                    buf = self._queue_to_send.get_nowait()
                except Empty:
                    break

                # Store
                buf_pending_array.append(buf)
                buf_pending_length += len(buf)

                # Check max (non-zipped)
                if buf_pending_length > self._http_send_max_bytes:
                    # Max size reached, over
                    break

            # Log
            logger.debug("Extracted for send, ms=%s, len=%s, bytes=%s", SolBase.msdiff(ms_extract), len(buf_pending_array), buf_pending_length)

            # Stats
            Meters.ai(self.meters_prefix + "knock_stat_transport_buffer_pending_length").set(buf_pending_length)

            # -------------------
            # DETECT WHAT TO DO
            # -------------------
            go_to_http = False
            retry_fast = False
            if buf_pending_length == 0:
                # -------------------
                # NOTHING
                # --------------------
                logger.debug("HttpCheck : no buf, http-no-go")
            elif buf_pending_length > self._http_send_max_bytes:
                # --------------------
                # MAX SIZE REACHED : go to HTTP and re-send ASAP
                # --------------------
                logger.debug("HttpCheck : maxed (%s/%s), http-go",
                             buf_pending_length, self._http_send_max_bytes)
                go_to_http = True
                retry_fast = True
            elif self._queue_to_send.qsize() == 0:
                # --------------------
                # EVERYTHING PUMPED AND NOT MAXED
                # --------------------

                ms_since_last_send = int(SolBase.datediff(self._dt_last_send))
                if ms_since_last_send < self._http_send_min_interval_ms:
                    # --------------------
                    # Minimum interval NOT reached : do NOT go to HTTP
                    # --------------------
                    logger.debug(
                        "HttpCheck : not maxed, min interval not reached (%s/%s), http-no-go",
                        ms_since_last_send,
                        self._http_send_min_interval_ms)
                else:
                    # --------------------
                    # Minimum interval reached : go to HTTP
                    # --------------------
                    logger.debug(
                        "HttpCheck : not maxed, min interval reached (%s/%s), http-go",
                        ms_since_last_send,
                        self._http_send_min_interval_ms)
                    go_to_http = True
            else:
                # --------------------
                # NOT POSSIBLE
                # --------------------
                logger.warning("HttpCheck : Impossible case (not maxed, not empty)")

            # --------------------
            # HTTP NO GO
            # --------------------

            if not go_to_http:
                # Re-queue reversed (ie preserve order)
                logger.debug("go_to_http False, re-queue now")
                self._requeue_pending_array(buf_pending_array)

                # Over
                return False

            # --------------------
            # HTTP GO
            # --------------------

            # buf_pending_array : list of serialized protocol lines

            # Send to http
            logger.debug("go_to_http true")
            b = self._send_to_http_influx(buf_pending_array, buf_pending_length)
            if not b:
                logger.warning("go_to_http failed, re-queue now, then sleep=%s", self._http_ko_interval_ms)
                self._requeue_pending_array(buf_pending_array)

                # Wait a bit
                SolBase.sleep(self._http_ko_interval_ms)

                # Over, go fast (we already waited)
                return True

            # Success, check go fast
            return retry_fast
        finally:
            self._http_pending = False
            Meters.ai(self.meters_prefix + "knock_stat_transport_buffer_pending_length").set(0)

    def _send_to_http_influx(self, ar_lines, total_len):
        """
        Send to http
        :param ar_lines: list of bytes (list of influx line buffers)
        :type ar_lines: list
        :param total_len: total len of all list items
        :type total_len: int
        :return True if success
        :rtype bool
        """

        ms = SolBase.mscurrent()
        try:
            Meters.aii(self.meters_prefix + "knock_stat_transport_call_count")

            if self._influx_mode == "influx":
                # --------------------
                # INFLUX CLIENT
                # --------------------

                # A) Client
                client = InfluxDBClient(
                    host=self._influx_host,
                    port=self._influx_port,
                    username=self._influx_login,
                    password=self._influx_password,
                    database=self._influx_database,
                    ssl=self._influx_ssl,
                    verify_ssl=self._influx_ssl_verify,
                    retries=0, )

                # B) Create DB
                if not self._influx_db_created:
                    try:
                        # Create DB
                        client.create_database(self._influx_database)
                    except Exception as e:
                        logger.warning("Influx create database failed, assuming ok, ex=%s", SolBase.extostr(e))
                    finally:
                        # Assume success
                        self._influx_db_created = True

                # Write lines
                try:
                    ms = SolBase.mscurrent()
                    logger.info("Push now (influx), ar_lines=%s", ar_lines)
                    ri = client.write_points(ar_lines, protocol="line")

                    # Call ok, store
                    self.last_http_ok_ms = SolBase.mscurrent()
                finally:
                    logger.info("Push done (influx), ms=%s", SolBase.msdiff(ms))

                # Check
                if not ri:
                    raise Exception("write_points returned false, ar_lines={0}".format(repr(ar_lines)))
            elif self._influx_mode == "knock":
                # --------------------
                # KNOCK CLIENT
                # --------------------

                # DB
                if not self._influx_db_created:
                    try:
                        http_rep = Tools.influx_create_database(self._http_client, host=self._influx_host, port=self._influx_port, username=self._influx_login, password=self._influx_password, database=self._influx_database, timeout_ms=self._influx_timeout_ms, ssl=self._influx_ssl, verify_ssl=self._influx_ssl_verify)
                        if not 200 <= http_rep.status_code < 300:
                            raise Exception("Need http 2xx, got http_req={0}".format(http_rep))
                    except Exception as e:
                        logger.warning("Influx create database failed, assuming ok, ex=%s", SolBase.extostr(e))
                    finally:
                        # Assume success
                        self._influx_db_created = True

                # PUSH
                try:
                    ms = SolBase.mscurrent()
                    logger.info("Push now (knock), ar_lines.len=%s", len(ar_lines))
                    http_rep = Tools.influx_write_data(self._http_client, host=self._influx_host, port=self._influx_port, username=self._influx_login, password=self._influx_password, database=self._influx_database, ar_data=ar_lines, timeout_ms=self._influx_timeout_ms, ssl=self._influx_ssl, verify_ssl=self._influx_ssl_verify)
                    if not 200 <= http_rep.status_code < 300:
                        raise Exception("Need http 2xx, got http_req={0}".format(http_rep))

                    # Call ok, store
                    self.last_http_ok_ms = SolBase.mscurrent()
                finally:
                    logger.info("Push done (knock), ms=%s", SolBase.msdiff(ms))
            else:
                # Invalid
                raise Exception("Invalid _influx_mode={0}".format(self._influx_mode))

            # Stats (non zip)
            Meters.ai(self.meters_prefix + "knock_stat_transport_buffer_last_length").set(total_len)
            Meters.ai(self.meters_prefix + "knock_stat_transport_buffer_max_length").set(
                max(
                    Meters.aig(self.meters_prefix + "knock_stat_transport_buffer_last_length"),
                    Meters.aig(self.meters_prefix + "knock_stat_transport_buffer_max_length"),
                )
            )

            # Stats (zip) [do not apply, we hack]
            Meters.ai(self.meters_prefix + "knock_stat_transport_wire_last_length").set(total_len)
            Meters.ai(self.meters_prefix + "knock_stat_transport_wire_max_length").set(
                max(
                    Meters.aig(self.meters_prefix + "knock_stat_transport_wire_last_length"),
                    Meters.aig(self.meters_prefix + "knock_stat_transport_wire_max_length"),
                )
            )

            # Stats
            Meters.aii(self.meters_prefix + "knock_stat_transport_ok_count")

            # Stats (we have no return from Influx client....)
            # We hack (may be slow and may be non accurate due to last \n)
            spv_processed = 0
            for cur_buf in ar_lines:
                spv_processed += cur_buf.count("\n")
            Meters.aii(self.meters_prefix + "knock_stat_transport_client_spv_processed", spv_processed)

            return True

        except Exception as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
            Meters.aii(self.meters_prefix + "knock_stat_transport_exception_count")

            # Here, HTTP not ok
            return False
        finally:
            ms_elapsed = int(SolBase.msdiff(ms))
            Meters.dtci(self.meters_prefix + "knock_stat_transport_dtc", ms_elapsed)
            Meters.ai(self.meters_prefix + "knock_stat_transport_wire_last_ms").set(ms_elapsed)
            Meters.ai(self.meters_prefix + "knock_stat_transport_wire_max_ms").set(
                max(
                    Meters.aig(self.meters_prefix + "knock_stat_transport_wire_last_ms"),
                    Meters.aig(self.meters_prefix + "knock_stat_transport_wire_max_ms"),
                )
            )

            self._dt_last_send = SolBase.datecurrent()
