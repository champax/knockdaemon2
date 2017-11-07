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
import importlib
import logging
import platform
import sys
from collections import OrderedDict
from datetime import datetime
from threading import Lock
from time import time

import anyconfig
import gevent
import os
from gevent.timeout import Timeout
from os.path import dirname, abspath
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters

from knockdaemon2.Core.KnockProbe import KnockConfigurationKeys, KnockProbe
from knockdaemon2.Core.KnockProbeContext import KnockProbeContext
from knockdaemon2.Core.UDPServer import UDPServer
from knockdaemon2.Kindly.Kindly import Kindly
from knockdaemon2.Platform.PTools import PTools
from knockdaemon2.Transport.KnockTransport import KnockTransport

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


class KnockManager(object):
    """
    Knock daemon manager
    """

    def __init__(self, config_file_name, auto_start=True):
        """
        Constructor
        :param config_file_name: Configuration file name
        :type config_file_name: str
        :param auto_start: If true, auto start everything (False used to unittest only)
        :type auto_start: bool
        """

        logger.info("Platform, machine=%s", platform.machine())
        logger.info("Platform, system=%s", platform.system())
        logger.info("Platform, node=%s", platform.node())
        logger.info("Platform, release=%s", platform.release())
        logger.info("Platform, version=%s", platform.version())
        logger.info("Platform, machine=%s", platform.machine())
        logger.info("Platform, processor=%s", platform.processor())
        logger.info("Platform, architecture=%s", platform.architecture())

        logger.info("Platform, python_version=%s", platform.python_version())
        logger.info("Platform, python_version_tuple=%s", platform.python_version_tuple())
        logger.info("Platform, python_compiler=%s", platform.python_compiler())
        logger.info("Platform, python_build=%s", platform.python_build())

        logger.info("PTools, is_cpu_arm=%s", PTools.is_cpu_arm())
        logger.info("PTools, is_os_64=%s", PTools.is_os_64())

        if PTools.get_distribution_type() != "windows":
            logger.info("Os, uname=%s", os.uname())

        logger.info("Manager launching now")

        # Check
        if not FileUtility.get_file_size(config_file_name):
            raise Exception("config_file_name do not exist={0}".format(config_file_name))

        # Auto
        self.auto_start = auto_start

        # File name
        self._config_file_name = config_file_name
        self._config_parser = None

        # Daemon control
        self._locker = Lock()
        self._is_running = False
        self._exec_greenlet = None

        # Transport list
        self._ar_knock_transport = None

        # Probe list
        self._probe_list = list()

        # Probe context
        self._hash_context = dict()

        # Timeout per probe
        self._exectimeout_ms = 10000

        # Disco hash
        self._superv_notify_disco_hash = dict()

        # Value list
        self._superv_notify_value_list = list()

        # Account management
        self._account_hash = dict()

        # Udp server
        self._udp_server = None

        # Init
        self._init_from_config()

    # ==============================
    # INIT FROM CONFIG
    # ==============================

    def _init_config_parser(self):
        """
        Init a config parser
        """

        # Files to load
        ar_to_load = list()

        # Our config
        ar_to_load.append(self._config_file_name)

        # We have _config_file_name.
        # Extract path, load it and all conf.d files matched
        # and merge it into memory....
        config_path = dirname(abspath(self._config_file_name))
        ps = SolBase.get_pathseparator()
        file_match = config_path + ps + "conf.d" + ps + "*.ini"
        logger.info("Using file_match=%s", file_match)

        # Setup
        for cur_file in sorted(glob.glob(file_match)):
            logger.info("Adding cur_file=%s", cur_file)
            ar_to_load.append(cur_file)

        # Ok, ready, load & merge
        d = anyconfig.load(ar_to_load)
        d = Kindly.kindly_anyconfig_fix_ta_shitasse(d)
        return d

    def _init_from_config(self):
        """
        Init manager from configuration
        """

        try:
            # Init
            self._config_parser = self._init_config_parser()

            # Init us
            tag = KnockConfigurationKeys.INI_KNOCKD_TAG
            self._exectimeout_ms = \
                int(self._config_parser[tag][KnockConfigurationKeys.INI_KNOCKD_EXEC_TIMEOUT_MS])

            # Account
            k = KnockConfigurationKeys.INI_KNOCKD_ACC_NAMESPACE
            self._account_hash[k] = self._config_parser[tag][k]

            k = KnockConfigurationKeys.INI_KNOCKD_ACC_KEY
            self._account_hash[k] = self._config_parser[tag][k]

            logger.info("Account hash=%s", self._account_hash)

            # Check them
            if not SolBase.is_string_not_empty(
                    self._account_hash[KnockConfigurationKeys.INI_KNOCKD_ACC_NAMESPACE]):
                raise Exception("Invalid {0}".format(
                    KnockConfigurationKeys.INI_KNOCKD_ACC_NAMESPACE))
            elif not SolBase.is_string_not_empty(
                    self._account_hash[KnockConfigurationKeys.INI_KNOCKD_ACC_KEY]):
                raise Exception("Invalid {0}".format(
                    KnockConfigurationKeys.INI_KNOCKD_ACC_KEY))

            # Init transport
            self._init_transport(KnockConfigurationKeys.INI_TRANSPORT_TAG)

            # Init Udp Listener
            self._init_udp_server(KnockConfigurationKeys.INI_UDP_SERVER_TAG)

            # Init probes
            for s in self._config_parser.iterkeys():
                if s.startswith(KnockConfigurationKeys.INI_PROBE_TAG):
                    self._init_probe(s)

        except Exception as e:
            logger.error("Exception, e=%s", SolBase.extostr(e))
            raise

    def _init_probe(self, section_name):
        """
        Initialize a probe
        :param section_name: Section name
        :type section_name: str
        """

        # Fetch class name and try to allocate
        logger.debug("Trying section_name=%s", section_name)
        class_name = self._config_parser[section_name][KnockConfigurationKeys.INI_PROBE_CLASS]

        # Try alloc
        p = self._try_alloc_class(class_name)

        # Check
        if not isinstance(p, KnockProbe):
            raise Exception("Allocation invalid, not a KnockProbe, having class={0}, instance={1}".format(SolBase.get_classname(p), p))

        logger.debug("Trying init, section_name=%s, class_name=%s", section_name, class_name)
        self._init_probe_internal(section_name, p)

    def _init_probe_internal(self, section_name, p):
        """
        Init
        :param section_name: Section name
        :type section_name: str
        :param p: KnockProbe
        :type p: KnockProbe
        """

        # Set us
        p.set_manager(self)

        # Initialize

        p.init_from_config(self._config_parser, section_name)

        # Ok, register it
        self._probe_list.append(p)
        logger.info("Probe registered, p=%s", p)

    # noinspection PyUnusedLocal
    def _init_udp_server(self, section_name):
        """
        Initialize udp server
        :param section_name: Section name
        :type section_name: str
        """

        # TODO : Config for udp server

        # Alloc
        self._udp_server = UDPServer(self)

        # Start if auto_start
        if self.auto_start:
            self._udp_server.start()

    def _init_transport(self, section_name):
        """
        Initialize transport
        :param section_name: Section name
        :type section_name: str
        """

        # Fetch class name and try to allocate
        logger.debug("Trying section_name=%s", section_name)
        class_name = self._config_parser[section_name][KnockConfigurationKeys.INI_PROBE_CLASS]

        # Try alloc
        t = self._try_alloc_class(class_name)

        # Check
        if not isinstance(t, KnockTransport):
            raise Exception("Allocation invalid, not a KnockTransport, having class={0}, instance={1}".format(SolBase.get_classname(t), t))

        # Initialize
        logger.debug("Trying init, section_name=%s, class_name=%s", section_name, class_name)
        t.init_from_config(self._config_parser, section_name, auto_start=self.auto_start)

        # Ok, register it
        self._ar_knock_transport = [t]
        logger.info("Transport registered, t=%s", t)

    # noinspection PyMethodMayBeStatic
    def _try_alloc_class(self, class_name):
        """
        Try to allocate a class
        :param class_name: class_name (<module_name>.<class>)
        :type class_name: str
        :return object
        :rtype object
        """

        # Got :
        # class_name = <module_name>.<class>
        pos = class_name.rfind(".")
        extracted_module = class_name[0:pos]
        extracted_class = class_name[pos + 1:]

        # Try import
        logger.debug("Trying import, class_name=%s, mod=%s, c=%s",
                     class_name, extracted_module, extracted_class)
        m = importlib.import_module(extracted_module)

        # Try attr
        logger.debug("Trying attr")
        attr = getattr(m, extracted_class)

        # Try alloc
        logger.debug("Trying alloc")
        return attr()

    # ==============================
    # START / STOP
    # ==============================

    def start(self):
        """
        Start        
        """

        with self._locker:
            try:
                lifecyclelogger.info("Start : starting")

                # Check
                if self._is_running:
                    logger.warn("Already running, doing nothing")

                # Start logs
                lifecyclelogger.info("Start : _exectimeout_ms=%s", self._exectimeout_ms)

                # Schedule next write now
                ms_to_next_execute = self._get_next_dynamic_exec_ms()
                logger.info("Initial scheduling, ms_to_next_execute=%s", ms_to_next_execute)
                self._exec_greenlet = gevent.spawn_later(
                    ms_to_next_execute, self._on_scheduled_exec
                )

                # Signal
                self._is_running = True
                lifecyclelogger.info("Start : started")
            except Exception as e:
                logger.error("Exception, e=%s", SolBase.extostr(e))

    def stop(self):
        """
        Stop
        """

        # Signal out of lock (may help greenlet to exit itself)
        self._is_running = False

        with self._locker:
            try:
                lifecyclelogger.info("Stop : stopping")
                # Kill the greenlet
                if self._exec_greenlet:
                    logger.info("_exec_greenlet.kill")
                    SolBase.sleep(0)
                    self._exec_greenlet.kill()
                    logger.info("_exec_greenlet.kill done")
                    # gevent.kill(self._exec_greenlet)
                    self._exec_greenlet = None

                # Stop udp server
                if self._udp_server:
                    logger.info("Stopping udp server (sync)")
                    self._udp_server.stop()
                    self._udp_server = None

                # Stop the transport
                for t in self._ar_knock_transport:
                    t.stop()

                lifecyclelogger.info("Stop : stopped")
            except Exception as e:
                logger.error("Exception, e=%s", SolBase.extostr(e))

    # ==============================
    # DEBUG EXEC
    # ==============================

    def exec_all(self):
        """
        Execute all probes, sequentially and go to supervision afterward.
        """

        # Exec all
        for p in self._probe_list:
            self._try_execute_probe_go(p)

        # Notify all
        self._process_superv_notify()

    # ==============================
    # SCHEDULE EXEC
    # ==============================

    def _on_scheduled_exec(self):
        """
        Scheduled executor
        """

        logger.debug("Entering")
        # Check
        if not self._is_running:
            logger.debug("Not running, bypass.1")
            return

        # Try execute now (without sleep)
        try:
            # Try exec
            logger.debug("Trying _try_execute_all")
            self._try_execute_all()

            # Handle Superv pending buffer
            self._process_superv_notify()
        except Exception as e:
            # This should NOT occur
            logger.error("Process exception, e=%s", SolBase.extostr(e))
            Meters.aii("knock_stat_exec_all_finally_exception")
        finally:
            # Check
            if not self._is_running:
                logger.debug("Not running, bypass.2")
                return

            # Re-schedule
            ms_to_next_execute = self._get_next_dynamic_exec_ms()
            logger.debug("Re-scheduling, ms_to_next_execute=%s", ms_to_next_execute)
            self._exec_greenlet = gevent.spawn_later(
                ms_to_next_execute * 0.001, self._on_scheduled_exec
            )

    # ==============================
    # EXECUTORS
    # ==============================

    def _try_execute_all(self):
        """
        Try execute everything
        """

        logger.debug("Entering")
        ms = SolBase.mscurrent()
        try:
            for p in self._probe_list:
                try:
                    self._try_execute_probe(p)
                except Exception as e:
                    logger.warn("Inner exception, p=%s, ex=%s", p, SolBase.extostr(e))
                    Meters.aii("knock_stat_exec_all_inner_exception")
                finally:
                    SolBase.sleep(0)
        except Exception as e:
            logger.warn("Outer exception, ex=%s", SolBase.extostr(e))
            Meters.aii("knock_stat_exec_all_outer_exception")
        finally:
            ms_elapsed = SolBase.msdiff(ms)
            next_exec_start_at = self._get_next_dynamic_exec_ms()
            next_diff_ms = SolBase.msdiff(next_exec_start_at)

            logger.debug("All probes executed, ms_elapsed=%s", ms_elapsed)
            Meters.dtci("knock_stat_exec_all_dtc", ms_elapsed)
            Meters.aii("knock_stat_exec_all_count")

            # Check execution time
            if next_diff_ms <= 0.0:
                logger.warn("Execution to slow, next_diff_ms=%s, ms_elapsed=%s", next_diff_ms, ms_elapsed)
                Meters.aii("knock_stat_exec_all_too_slow")

    def _try_execute_probe(self, p):
        """
        Try execute a probe
        :param p: Probe to execute
        :type p: KnockProbe
        """

        # Check execute
        c = self._get_probe_context(p)
        if not self._need_exec(p, c):
            logger.debug("Bypass, _need_exec false, p=%s, c=%s", p, c)
            Meters.aii("knock_stat_exec_probe_bypass")
            return

        # Exec
        self._try_execute_probe_go(p)

    def _try_execute_probe_go(self, p):
        """
        Try execute a probe
        :param p: Probe to execute
        :type p: KnockProbe
        """

        # Execute
        logger.debug("Executing, p=%s", p)

        # Current ms
        ms = SolBase.mscurrent()

        # Get
        c = self._get_probe_context(p)

        # Register last exec start and first exec start and exec count
        if c.initial_ms_start == 0.0:
            c.initial_ms_start = SolBase.mscurrent()
        c.exec_count_so_far += 1.0

        # Go
        try:
            # Exec async, with timeout
            exec_timeout_ms = self._exectimeout_ms
            if p.exec_timeout_override_ms:
                exec_timeout_ms = p.exec_timeout_override_ms
                logger.info("Exec timeout override set at probe end, using exec_timeout_ms=%s", exec_timeout_ms)

            # FIRE
            logger.info("Exec now, exec_timeout_ms=%s, p=%s", exec_timeout_ms, p)
            gevent.with_timeout(exec_timeout_ms * 0.001, p.execute)
            logger.info("Exec done, ms=%s, p=%s", SolBase.msdiff(ms), p)
        except Timeout:
            logger.warn("Execute timeout, p=%s", p)
            Meters.aii("knock_stat_exec_probe_timeout")
        except Exception as e:
            logger.warn("Execute exception, p=%s, ex=%s", p, SolBase.extostr(e))
            Meters.aii("knock_stat_exec_probe_exception")
        finally:
            ms_elapsed = SolBase.msdiff(ms)
            logger.debug("Over, p=%s, ms_elapsed=%s", p, ms_elapsed)
            Meters.dtci("knock_stat_exec_probe_dtc", ms_elapsed)
            Meters.aii("knock_stat_exec_probe_count")

    # ==============================
    # SUPERV NOTIFY : DISCOVERY
    # ==============================

    def notify_discovery_n(self, disco_key, d_disco_id_tag):
        """
        Notify discovery (1..n)

        Sample:
        - notify_discovery_n("k.dns", {"HOST": "my_host", "SERVER": "my_server"})
        :param disco_key: discovery key
        :type disco_key: str
        :param d_disco_id_tag: dict {"disco_tag_1": "value", "disco_tag_n": "value"}
        :type d_disco_id_tag: dict
        """

        # We use a sort toward OrderedDict to have consistent and predictive matching
        do = OrderedDict(sorted(d_disco_id_tag.items(), key=lambda t: t[0]))

        # Compute key
        key = "{0}".format(disco_key)
        for disco_id, disco_tag in do.iteritems():
            assert isinstance(disco_id, (str, unicode)), "disco_id must be str,unicode, got={0}, value={1}".format(SolBase.get_classname(disco_id), disco_id)
            assert isinstance(disco_tag, (str, unicode)), "disco_tag must be str,unicode, got={0}, value={1}".format(SolBase.get_classname(disco_tag), disco_tag)
            key += "|{0}|{1}".format(disco_id, disco_tag)

        if key in self._superv_notify_disco_hash:
            # Hashed, exit
            return
        else:
            # Add
            tu = (disco_key, do)
            logger.debug("ADDING tu=%s", tu)
            self._superv_notify_disco_hash[key] = tu

            # Stats
            Meters.aii("knock_stat_notify_disco")

    # ==============================
    # SUPERV NOTIFY : VALUE
    # ==============================

    def notify_value_n(self, counter_key, d_disco_id_tag, counter_value, ts=None, d_opt_tags=None):
        """
        Notify value

        Example :
        - notify_value_n("k.dns.time", {"HOST": "my_host", "SERVER": "my_server"}, 1.5)

        :param counter_key: Counter key (str)
        :type counter_key: str
        :param d_disco_id_tag: None (if no discovery) or dict of {disco_id: disco_tag}
        :type d_disco_id_tag: None, dict
        :param counter_value: Counter value
        :type counter_value: object
        :param ts: timestamp (epoch), or None to use current
        :type ts: None, float
        :param d_opt_tags: None,dict (additional tags)
        :type d_opt_tags: None,dict

        """

        # Strict mode : we refuse keys with [ or ] or with .discovery
        assert counter_key.find("[") == -1, "counter_key : [] chars are not allowed, got counter_key={0}".format(counter_key)
        assert counter_key.find("]") == -1, "counter_key : [] chars are not allowed, got counter_key={0}".format(counter_key)
        assert counter_key.find(".discovery") == - 1, "counter_key : '.discovery' is not allowed, got counter_key={0}".format(counter_key)

        # Stat
        Meters.aii("knock_stat_notify_value")

        # Fix up value for Superv
        counter_value = self._to_superv_value(counter_value)

        # Sort
        if d_disco_id_tag:
            dd = OrderedDict(sorted(d_disco_id_tag.items(), key=lambda t: t[0]))

            # Validate
            for k, v in dd.iteritems():
                assert isinstance(k, (str, unicode)), "k must be str,unicode, got class={0}, k={1}".format(SolBase.get_classname(k), k)
                assert isinstance(v, (str, unicode)), "v must be str,unicode, got class={0}, v={1}".format(SolBase.get_classname(v), v)
        else:
            dd = None

        # Append
        if not ts:
            ts = time()

        self._superv_notify_value_list.append((counter_key, dd, counter_value, ts, d_opt_tags))

    # ==============================
    # SUPERV : TOOLS
    # ==============================

    def _reset_superv_notify(self):
        """
        Reset Superv pending notify
        """

        if self._superv_notify_disco_hash and len(self._superv_notify_disco_hash) > 0:
            logger.warn("Discarding pending _superv_notify_disco_hash=%s",
                        self._superv_notify_disco_hash)
        if self._superv_notify_value_list and len(self._superv_notify_value_list) > 0:
            logger.warn("Discarding pending _superv_notify_value_list=%s",
                        self._superv_notify_value_list)

        # Reset
        self._superv_notify_disco_hash = dict()
        self._superv_notify_value_list = list()

    def _process_superv_notify(self):
        """
        Process Superv notify
        """

        logger.debug("Notifying transport")

        # Node
        node_hash = dict()
        node_hash["host"] = SolBase.get_machine_name()

        # Send to transports
        clear_hash = True
        for t in self._ar_knock_transport:
            b = t.process_notify(
                self._account_hash, node_hash, self._superv_notify_disco_hash,
                self._superv_notify_value_list)
            if not b:
                if len(self._ar_knock_transport) == 1:
                    # Only only one transport, do not clear the hashes
                    logger.info("Got false from process_notify and only one transport, will not empty the hashes, t=%s", t)
                    clear_hash = False
                else:
                    # Several transport, we clear
                    logger.warn("Got false from process_notify and multi transport, will empty the hashes, t=%s", t)

        # We reset if required
        if clear_hash:
            self._superv_notify_disco_hash = dict()
            self._superv_notify_value_list = list()

    def get_transport_by_type(self, transport_class):
        """
        Get transport by type
        :param transport_class: transport class to match
        :return: knockdaemon2.Transport.KnockTransport.KnockTransport
        :rtype knockdaemon2.Transport.KnockTransport.KnockTransport
        """

        for t in self._ar_knock_transport:
            if isinstance(t, transport_class):
                return t
        raise Exception("Transport not found, transport_class={0}".format(transport_class))

    # ==============================
    # TOOLS
    # ==============================

    # noinspection PyMethodMayBeStatic
    def _to_superv_value(self, v):
        """
        Convert a value suitable for Superv
        :param v: value to convert
        :return: value updated
        """

        if isinstance(v, float):
            return str(v).upper()
        elif isinstance(v, bool):
            if v:
                return 1
            else:
                return 0
        elif isinstance(v, datetime):
            return int(v.strftime('%s'))
        else:
            return v

    # noinspection PyMethodMayBeStatic
    def _need_exec_compute_next_start_ms(self, p, c):
        """
        Compute next start ms for this probe context
        :param p: KnockProbe
        :type p: KnockProbe
        :param c: KnockProbeContext
        :type c: KnockProbeContext
        :return: float
        :rtype float
        """

        # Previously, we were based on previous exec start (ms_last_exec)
        # Which can derived a bit, since based on previous exec time
        # We are now based on first exec date and exec count

        # Now :
        exec_interval_ms = float(p.exec_interval_ms)
        first_start_ms = c.initial_ms_start
        exec_count_so_far = c.exec_count_so_far

        # Next ms to start base on first_start_ms and exec_count_so_far
        if first_start_ms == 0.0:
            # NOW
            return SolBase.mscurrent()
        else:
            next_start_ms = first_start_ms + (exec_count_so_far * exec_interval_ms)
            return next_start_ms

    # noinspection PyMethodMayBeStatic
    def _need_exec(self, p, c):
        """
        Check if a probe need an execution
        :param p: KnockProbe
        :type p: KnockProbe
        :param c: KnockProbeContext
        :type c: KnockProbeContext
        :return True if execution is required.
        :rtype bool
        """

        # Check
        if not p.exec_enabled:
            # Disable => no
            return False

        # Probe   : got exec_interval_ms
        # Compute next start ms
        next_start_ms = self._need_exec_compute_next_start_ms(p, c)

        # Check
        cur_ms = SolBase.mscurrent()
        if next_start_ms <= cur_ms:
            # Interval reached => yes
            return True
        else:
            # Interval not reached => no
            return False

    # noinspection PyMethodMayBeStatic
    def _need_exec_ms(self, p, c):
        """
        Check if a probe need an execution and return when this execution must be performed.
        :param p: KnockProbe
        :type p: KnockProbe
        :param c: KnockProbeContext
        :type c: KnockProbeContext
        :return The millis within the probe should be executed, or sys.float_info.max if no execution is required.
        :rtype float
        """

        if not p.exec_enabled:
            # Disabled => never
            return sys.float_info.max

        # Compute next start
        next_start_ms = self._need_exec_compute_next_start_ms(p, c)

        # Check
        cur_ms = SolBase.mscurrent()
        if next_start_ms <= cur_ms:
            # Interval reached => now
            return 0.0
        else:
            # next_start_ms in the future (so gt than cur_ms)
            # compute delay to it
            d = next_start_ms - cur_ms
            return d

    def _get_next_dynamic_exec_ms(self):
        """
        Get next execute to schedule, based on all probes and their context.
        :return:
        """
        ms = sys.float_info.max
        for p in self._probe_list:
            c = self._get_probe_context(p)
            ms = min(ms, self._need_exec_ms(p, c))
        return ms

    def _get_probe_context(self, p):
        """
        Get context related to a probe
        :param p: KnockProbe
        :type p: KnockProbe
        :return KnockProbeContext
        :rtype KnockProbeContext
        """

        key = id(p)
        if key not in self._hash_context:
            self._hash_context[key] = KnockProbeContext()
        return self._hash_context[key]
