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
# noinspection PyUnresolvedReferences
import ujson
from datetime import datetime
from greenlet import GreenletExit

import gevent
from gevent.queue import Queue, Empty
from gevent.threading import Lock
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest
from pysolmeters.Meters import Meters

from knockdaemon2.Transport.KnockTransport import KnockTransport

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


class HttpAsyncTransport(KnockTransport):
    """
    Http transport
    """

    QUEUE_WAIT_SEC_PER_LOOP = None

    def __init__(self):
        """
        Constructor
        """
        KnockTransport.__init__(self)
        self.http_uri = None

        # Locker
        self._locker = Lock()

        # Pending
        self._http_pending = False

        # Async stuff to send
        self._queue_to_send = Queue()

        # Max items in send queue (if reached, older items are kicked)
        self._max_items_in_queue = 36000

        # Upon http failure, time to wait before next http request
        # Recommended : _http_send_min_interval_ms*2
        self._http_ko_interval_ms = 10000

        # Minimum http send interval. If reached, a send will occurs
        # (even if _http_send_max_bytes is not reached).
        self._http_send_min_interval_ms = 60000

        # Maximum http send size to fire. If reached, a send occurs, with immediate retry.
        # 256 KB default.
        self._http_send_max_bytes = 1 * 256 * 1024

        # Wait ms if send is bypassed before re-trying
        self._http_send_bypass_wait_ms = 1000

        # Timeout ms
        self._http_network_timeout_ms = 60000

        # Zip on
        self._zip_enabled = True

        # Run
        self._is_running = False
        self._greenlet = None
        self._dt_last_send = SolBase.datecurrent()

        # Http client instance
        self.http_client = HttpClient()

        # Meters prefix
        self.meters_prefix = "httpasync_"

        # To rewrite
        self.load_http_uri = True

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

        if self.load_http_uri:
            self.http_uri = d["http_uri"]

        try:
            self._max_items_in_queue = d["max_items_in_queue"]
        except KeyError:
            logger.debug("Key max_items_in_queue not present, using default, d=%s", d)

        try:
            self._http_ko_interval_ms = d["http_ko_interval_ms"]
        except KeyError:
            logger.debug("Key http_ko_interval_ms not present, using default, d=%s", d)

        try:
            self._http_send_min_interval_ms = d["http_send_min_interval_ms"]
        except KeyError:
            logger.debug("Key http_send_min_interval_ms not present, using default, d=%s", d)

        try:
            self._http_send_max_bytes = d["http_send_max_bytes"]
        except KeyError:
            logger.debug("Key http_send_max_bytes not present, using default, d=%s", d)

        try:
            self._http_send_bypass_wait_ms = d["http_send_bypass_wait_ms"]
        except KeyError:
            logger.debug("Key http_send_bypass_wait_ms not present, using default, d=%s", d)

        try:
            self._zip_enabled = d["zip_enabled"]
        except KeyError:
            logger.debug("Key zip_enabled not present, using default, d=%s", d)

        # Limits
        self._check_and_fix_limits()

        lifecyclelogger.info("http_uri=%s", self.http_uri)
        lifecyclelogger.info("_max_items_in_queue=%s", self._max_items_in_queue)
        lifecyclelogger.info("_http_ko_interval_ms=%s", self._http_ko_interval_ms)
        lifecyclelogger.info("_http_send_min_interval_ms=%s", self._http_send_min_interval_ms)
        lifecyclelogger.info("_http_send_max_bytes=%s", self._http_send_max_bytes)
        lifecyclelogger.info("_http_send_bypass_wait_ms=%s", self._http_send_bypass_wait_ms)
        lifecyclelogger.info("_zip_enabled=%s", self._zip_enabled)

        # Start
        if auto_start:
            self.greenlet_start()

    def _check_and_fix_limits(self):
        """
        Check and set limits
        """

        # Disable this
        pass

        # # If unittest, do nothing
        # if "KNOCK_UNITTEST" in os.environ.data:
        #     return
        #
        # # Lower limits for important stuff
        # if self._http_send_min_interval_ms < 30000:
        #     self._http_send_min_interval_ms = 30000
        #
        # if self._http_ko_interval_ms < 10000:
        #     self._http_ko_interval_ms = 10000
        #
        # if self._http_send_bypass_wait_ms < 1000:
        #     self._http_send_bypass_wait_ms = 1000

    def process_notify(self, account_hash, node_hash, notify_hash, notify_values):
        """
        Process notify TODO need server implementation of multiseries time series
        :param account_hash: Hash str to value
        :type account_hash; dict
        :param node_hash: Hash str to value
        :type node_hash; dict
        :param notify_hash: Hash str to (disco_key, disco_id, tag). Cleared upon success.
        :type notify_hash; dict
        :param notify_values: List of (superv_key, tag, value). Cleared upon success.
        :type notify_values; list
        """

        # If not running, exit
        if not self._is_running:
            logger.warn("Not running, processing not possible")
            return False

        # Fix value
        ar_nv = list()

        for notify_value in notify_values:
            if len(notify_value) == 5:
                k, tag, v, ts, categ = notify_value
            else:
                k, tag, v, ts, categ, _ = notify_value
            if isinstance(v, float):
                v = str(v).upper()
            elif isinstance(v, bool):
                if v:
                    v = 1
                else:
                    v = 0
            elif isinstance(v, datetime):
                v = int(v.strftime('%s'))
            ar_nv.append((k, tag, v, ts, categ))

        # We serialize this block right now
        d = dict()
        d["a"] = account_hash
        d["n"] = node_hash
        d["h"] = notify_hash
        d["v"] = ar_nv
        buf = ujson.dumps(d)

        # Check max
        if self._queue_to_send.qsize() >= self._max_items_in_queue:
            # Too much, kick
            logger.warn("Max queue reached, discarding older item")
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
        Meters.ai(self.meters_prefix + "knock_stat_transport_queue_max_size").set(
            max(
                self._queue_to_send.qsize(),
                Meters.aig(self.meters_prefix + "knock_stat_transport_queue_max_size")
            )
        )

        # Done
        return True

    def _send_to_http(self, buf):
        """
        Process notify
        :param buf: str
        :type buf: str
        :return True if success
        :rtype bool
        """

        ms = SolBase.mscurrent()
        try:
            Meters.aii(self.meters_prefix + "knock_stat_transport_call_count")

            # Data
            logger.debug("Buf length=%s", len(buf))
            logger.debug("Buf data=%s", repr(buf))

            # If zip enabled, zip it
            if self._zip_enabled:
                buf_to_send = buf.encode("zlib")
            else:
                buf_to_send = buf

            # Stats (non zip)
            Meters.ai(self.meters_prefix + "knock_stat_transport_buffer_last_length").set(len(buf))

            Meters.ai(self.meters_prefix + "knock_stat_transport_buffer_max_length").set(
                max(
                    Meters.aig(self.meters_prefix + "knock_stat_transport_buffer_last_length"),
                    Meters.aig(self.meters_prefix + "knock_stat_transport_buffer_max_length"),
                )
            )

            # Stats (zip)
            Meters.ai(self.meters_prefix + "knock_stat_transport_wire_last_length").set(len(buf_to_send))
            Meters.ai(self.meters_prefix + "knock_stat_transport_wire_max_length").set(
                max(
                    Meters.aig(self.meters_prefix + "knock_stat_transport_wire_last_length"),
                    Meters.aig(self.meters_prefix + "knock_stat_transport_wire_max_length"),
                )
            )

            # ------------------------
            # Http post / NEW CODE
            # ------------------------

            # TODO : Socks / Proxy over http

            # Setup request
            hreq = HttpRequest()

            # Config
            hreq.connection_timeout_ms = self._http_network_timeout_ms
            hreq.network_timeout_ms = self._http_network_timeout_ms
            hreq.general_timeout_ms = self._http_network_timeout_ms
            hreq.keep_alive = True
            hreq.https_insecure = False

            # Uri
            hreq.uri = self.http_uri

            # Headers
            if self._zip_enabled:
                # Headers
                hreq.headers["Content-Encoding"] = "gzip"
                hreq.headers["Accept-Encoding"] = "gzip"

            # Data to send
            hreq.post_data = buf_to_send

            # Fire http now
            logger.info("Firing http now, hreq=%s", hreq)
            hresp = self.http_client.go_http(hreq)

            # Get response
            if hresp.status_code == 200:
                # Get post data
                pd = hresp.buffer

                # Try zip
                try:
                    pd = pd.decode("zlib")
                except Exception as ex:
                    logger.debug("Unable to decode zlib, should be a normal buffer, ex=%s",
                                 SolBase.extostr(ex))

                # Load
                rd = ujson.loads(pd)
                logger.debug("Http reply=%s", rd)
                if "st" in rd and rd["st"] == 200:
                    logger.info("HTTP OK, req.buf.len/zip=%s/%s", len(buf), len(buf_to_send))

                    # Stats
                    Meters.aii(self.meters_prefix + "knock_stat_transport_ok_count")

                    # Stats
                    ok_count = rd["sp"]["ok"]
                    ko_count = rd["sp"]["ko"]
                    Meters.aii(self.meters_prefix + "knock_stat_transport_client_spv_processed", ok_count)
                    Meters.aii(self.meters_prefix + "knock_stat_transport_client_spv_failed", ko_count)
                    return True
                else:
                    logger.warn("HTTP HS, r=%s", hresp)
                    Meters.aii(self.meters_prefix + "knock_stat_transport_failed_count")
            else:
                logger.warn("HTTP KO, uri=%s, r=%s", self.http_uri, hresp)
                Meters.aii(self.meters_prefix + "knock_stat_transport_failed_count")

            return False
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
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
                logger.warn("_greenlet already set, doing nothing")
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
                logger.warn("_greenlet not set, doing nothing")
                return

            # Kill
            logger.info("_greenlet.kill")
            self._greenlet.kill()
            logger.info("_greenlet.kill done")
            # gevent.kill(self._greenlet)
            self._greenlet = None
            logger.info("Send greenlet : stopped")

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

    def _try_send_to_http(self):
        """
        Check if we can send the pending queue to server
        :return bool
        :rtype bool
        """

        # NOTE :
        # _queue_to_send : it's a queue of pre-serialized JSON buffer to send.
        # So, _queue_to_send => queue of binary items
        #
        # We extract them, accumulate them in an array, send them to Http
        # (using d["par"])
        # This JSON is then also serialized.
        #
        # Currently :
        # a) extract from queue, accumulate in buf_pending_array, then try to send
        # => This requires extraction, often for nothing (every 500 ms)
        # => This requires array reverse + requeue at head
        #
        # So :
        # b) We may move to an hybrib queue
        # => normal items (binary)
        # => Pre-extracted and re-queue array (so array item, but only at head)
        # ===> may be a tuple (array, totalbytes)
        # => This will avoid extraction (array at head : use it + try concat other items)
        # => Simple requeue (just requeue at head buf_pending_array)

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
                logger.warn("HttpCheck : Impossible case (not maxed, not empty)")

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

            # Serialize
            d = dict()
            d["par"] = buf_pending_array
            d["o"] = {"zip": True}
            buf_to_send = ujson.dumps(d)

            # Send to http
            logger.debug("go_to_http true")
            b = self._send_to_http(buf_to_send)
            if not b:
                logger.warn("go_to_http failed, re-queue now, then sleep=%s", self._http_ko_interval_ms)
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
                        self._queue_to_send.peek(True, HttpAsyncTransport.QUEUE_WAIT_SEC_PER_LOOP)
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
                    logger.warn("Exception in loop2=%s", SolBase.extostr(e))
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


