"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2022 Laurent Labatut / Laurent Champagnac
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
import inspect
import logging
import os
import platform
import sys
from collections import OrderedDict
from os.path import dirname, abspath
from threading import Lock, Event
from time import time

import gevent
import yaml
from gevent.timeout import Timeout
from greenlet import GreenletExit
from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolmeters.Meters import Meters
from yaml import SafeLoader

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Core.KnockProbeContext import KnockProbeContext
from knockdaemon2.Core.UDPServer import UDPServer
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

        logger.info("Os, uname=%s", os.uname())

        logger.info("Manager launching now")

        # Check
        if not FileUtility.get_file_size(config_file_name):
            raise Exception("config_file_name do not exist={0}".format(config_file_name))

        # Auto
        self.auto_start = auto_start

        # Lifecycle
        self._lifecycle_greenlet = None
        self._lifecycle_exit = Event()

        # Lifecycle interval
        self._lifecycle_last_ms = SolBase.mscurrent()
        self._lifecycle_interval_ms = 5000

        # File name
        self._config_file_name = config_file_name
        self._d_yaml_config = None

        # Probed
        self._probes_d_dir = "/etc/knock/knockdaemon2/probes.d/"

        # Daemon control
        self._locker = Lock()
        self._is_running = False
        self._exec_greenlet = None

        # Transport list
        self._ar_knock_transport = list()

        # Probe list
        self.probe_list = list()

        # Probe context
        self._hash_context = dict()

        # Timeout per probe
        self._exectimeout_ms = 10000

        # Value list
        self.superv_notify_value_list = list()

        # Account management
        self._account_hash = dict()

        # Udp server
        self._udp_server = None

        # Init
        self._init_from_config()

    # ==============================
    # INIT FROM CONFIG
    # ==============================

    def _init_config_yaml(self):
        """
        Init configuration
        :return dict
        :rtype dict
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
        file_match = config_path + ps + "conf.d" + ps + "*.yaml"
        logger.info("Using file_match=%s", file_match)

        # Setup
        for cur_file in sorted(glob.glob(file_match)):
            logger.info("Adding cur_file=%s", cur_file)
            ar_to_load.append(cur_file)

        # Ok, ready, load & merge
        d_conf = {}
        for cur_file in ar_to_load:
            logger.info("Loading cur_file=%s", cur_file)
            with open(cur_file, 'r') as yml_file:
                cur_d = yaml.load(yml_file, Loader=SafeLoader)

            logger.info("Merging cur_d=%s", cur_d)

            # update will replace existing keys, this is not what we want...
            d_conf = KnockManager.dict_merge(d_conf, cur_d)

        # Ok
        logger.info("Got effective d_conf=%s", d_conf)
        return d_conf

    @classmethod
    def dict_merge(cls, d1, d2):
        """
        Merge dict, without loosing existing values in d1
        :param d1: dict (destination)
        :type d1: dict
        :param d2: dict (values to be added)
        :type d2: dict
        :return: dict
        :rtype dict
        """

        if not isinstance(d1, dict):
            raise Exception("need a dict")
        elif not isinstance(d2, dict):
            raise Exception("need a dict")

        for cur_k, cur_v in d2.items():
            if cur_k in d1:
                # Need both dict to merge, otherwise d2 wins
                if not isinstance(cur_v, dict) or not isinstance(d1[cur_k], dict):
                    d1[cur_k] = cur_v
                    continue

                rec_d1 = d1[cur_k]
                rec_d2 = d2[cur_k]
                rec_merged = cls.dict_merge(rec_d1, rec_d2)
                d1[cur_k] = rec_merged
            else:
                # Just assign
                d1[cur_k] = cur_v

        return d1

    def _init_from_config(self):
        """
        Init manager from configuration
        """

        try:
            # Init
            logger.info("Init now")
            self._d_yaml_config = self._init_config_yaml()

            # Init us
            if "exectimeout_ms" in self._d_yaml_config["knockd"]:
                self._exectimeout_ms = self._d_yaml_config["knockd"]["exectimeout_ms"]

            # Account for managed instance, which is optional now due to influx support
            if "acc_namespace" in self._d_yaml_config["knockd"]:
                self._account_hash["acc_namespace"] = self._d_yaml_config["knockd"]["acc_namespace"]
                self._account_hash["acc_key"] = self._d_yaml_config["knockd"]["acc_key"]

                logger.info("Account hash=%s", self._account_hash)
            else:
                logger.warning("No acc_namespace defined in configuration, using default, transports may not be able to push datas to remote managed instance")
                self._account_hash = {
                    "acc_namespace": "unset",
                    "acc_key": "unset"
                }

            # Check them
            if not len(self._account_hash["acc_namespace"]) > 0:
                raise Exception("Invalid acc_namespace")
            elif not len(self._account_hash["acc_key"]) > 0:
                raise Exception("Invalid acc_key")

            # Lifecycle
            try:
                self._lifecycle_interval_ms = self._d_yaml_config["knockd"]["lifecycle_interval_ms"]
            except KeyError:
                logger.info("Key lifecycle_interval_ms not present, using default=%s", self._lifecycle_interval_ms)
            logger.info("_lifecycle_interval_ms=%s", self._lifecycle_interval_ms)

            # Probes.d
            try:
                self._probes_d_dir = self._d_yaml_config["knockd"]["_probes_d_dir"]
            except KeyError:
                logger.info("Key _probes_d_dir not present, using default=%s", self._probes_d_dir)
            logger.info("_probes_d_dir=%s", self._probes_d_dir)

            # Init transports
            logger.info("Init transports")
            if "transports" in self._d_yaml_config and self._d_yaml_config["transports"] is not None:
                for k, d in self._d_yaml_config["transports"].items():
                    self._init_transport(k, d)
            else:
                logger.warning("No transports defined, daemon will run in noop mode, please configure some transports")

            # Init Udp Listener
            logger.info("Init udp")
            self._init_udp_server()

            # Init probes
            logger.info("Init probes")
            for k, d in self._d_yaml_config["probes"].items():
                self._init_probe(k, d)

            # Init custom probes
            logger.info("Init custom probes")
            ar_probes, _ = self.try_dynamic_load_probe(self._probes_d_dir)
            logger.info("Init custom probes, loaded count=%s", len(ar_probes))
            idx = 0
            for p in ar_probes:
                # Need a key for this one, we use the and id
                k = "custom_probes_" + str(idx)
                logger.info("Initializing custom probes, k=%s, p=%s", k, p)

                d_local_conf = {
                    "class_name": SolBase.get_classname(p),
                    "exec_enabled": True,
                    "exec_interval_sec": 60,
                }
                self._init_probe_internal(k, d_local_conf, p)

            # Over
            logger.info("Completed")
        except Exception as e:
            logger.error("Exception, e=%s", SolBase.extostr(e))
            raise

    def _init_probe(self, k, d):
        """
        Initialize a probe
        :param k: str
        :type k: str
        :param d: local conf
        :type d: dict
        """

        # Fetch class name and try to allocate
        logger.debug("Trying d=%s", d)
        class_name = d["class_name"]

        # Try alloc
        p = self._try_alloc_class(class_name)

        # Check
        if not isinstance(p, KnockProbe):
            raise Exception("Allocation invalid, not a KnockProbe, having class={0}, instance={1}".format(SolBase.get_classname(p), p))

        logger.debug("Trying init, d=%s", d)
        self._init_probe_internal(k, d, p)

    def _init_probe_internal(self, k, d, p):
        """
        Init
        :param k: str
        :type k: str
        :param d: local conf
        :type d: dict
        :param p: KnockProbe
        :type p: KnockProbe
        """

        # Set us
        p.set_manager(self)

        # Initialize
        p.init_from_config(k, self._d_yaml_config, d)

        # Ok, register it
        self.probe_list.append(p)
        logger.info("Probe registered, p=%s", p)

    def _init_udp_server(self):
        """
        Initialize udp server
        """

        # TODO : Config for udp server

        # Alloc
        self._udp_server = UDPServer(self)

        # Start if auto_start
        if self.auto_start:
            self._udp_server.start()

    def _init_transport(self, k, d):
        """
        Initialize transport
        :param k: key
        :type k: str
        :param d: dict
        :type d: dict
        """

        # Go
        logger.info("Trying transport, k=%s, d=%s", k, d)

        if "class_name" not in d:
            logger.info("Bypassing transport due to non class_name in d=%s", d)
            return

        # Fetch class name and try to allocate
        class_name = d["class_name"]

        # Try alloc
        t = self._try_alloc_class(class_name)

        # Check
        if not isinstance(t, KnockTransport):
            raise Exception("Allocation invalid, not a KnockTransport, having class={0}, instance={1}".format(SolBase.get_classname(t), t))

        # Initialize
        logger.debug("Trying init transport now")
        t.init_from_config(self._d_yaml_config, d, auto_start=self.auto_start)

        # Ok, register it
        self._ar_knock_transport.append(t)
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
                    logger.warning("Already running, doing nothing")

                # Start logs
                lifecyclelogger.info("Start : _exectimeout_ms=%s", self._exectimeout_ms)

                # Signal
                self._is_running = True

                # Start lifecycle
                self.lifecycle_start()

                # Schedule next write now
                ms_to_next_execute = self._get_next_dynamic_exec_ms()
                logger.info("Initial scheduling, ms_to_next_execute=%s", ms_to_next_execute)
                self._exec_greenlet = gevent.spawn_later(
                    ms_to_next_execute, self._on_scheduled_exec
                )

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

                # Kill lifecycle
                self.lifecycle_stop()

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
        for p in self.probe_list:
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
            for p in self.probe_list:
                try:
                    self._try_execute_probe(p)
                except Exception as e:
                    logger.warning("Inner exception, p=%s, ex=%s", p, SolBase.extostr(e))
                    Meters.aii("knock_stat_exec_all_inner_exception")
                finally:
                    SolBase.sleep(0)
        except Exception as e:
            logger.warning("Outer exception, ex=%s", SolBase.extostr(e))
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
                logger.warning("Execution to slow, next_diff_ms=%s, ms_elapsed=%s", next_diff_ms, ms_elapsed)
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

        # Increment
        c.exec_count_so_far += 1.0

        # Go
        try:
            # Exec async, with timeout
            exec_timeout_ms = self._exectimeout_ms
            if p.exec_timeout_override_ms:
                exec_timeout_ms = p.exec_timeout_override_ms
                logger.debug("Exec timeout override set at probe end, using exec_timeout_ms=%s", exec_timeout_ms)

            # FIRE
            with Timeout(exec_timeout_ms * 0.001):
                ms_elapsed = None
                logger.debug("Exec now, exec_timeout_ms=%s, p=%s", exec_timeout_ms, p)
                p.execute()
                ms_elapsed = SolBase.msdiff(ms)
                logger.debug("Exec done, ms=%s, p=%s", ms_elapsed, p)
        except Timeout:
            logger.warning("Execute timeout, p=%s", p)
            Meters.aii("knock_stat_exec_probe_timeout")
        except Exception as e:
            logger.warning("Execute exception, p=%s, ex=%s", p, SolBase.extostr(e))
            Meters.aii("knock_stat_exec_probe_exception")
        finally:
            if ms_elapsed is None:
                ms_elapsed = SolBase.msdiff(ms)
            # noinspection PyUnboundLocalVariable
            Meters.dtci("knock_stat_exec_probe_dtc", ms_elapsed)
            Meters.aii("knock_stat_exec_probe_count")

    # ==============================
    # SUPERV NOTIFY : VALUE
    # ==============================

    def notify_value_n(self, counter_key, d_tags, counter_value, ts=None, d_values=None):
        """
        Notify value

        Example :
        - notify_value_n("k.dns.time", {"HOST": "my_host", "SERVER": "my_server"}, 1.5)

        :param counter_key: Counter key (str)
        :type counter_key: str
        :param d_tags: Dict of tags
        :type d_tags: None, dict
        :param counter_value: Counter value
        :type counter_value: object
        :param ts: timestamp (epoch), or None to use current
        :type ts: None, float
        :param d_values: Additional counter values (dict)
        :type d_values: dict
        """

        # Strict mode : we refuse keys with [ or ] or with .discovery
        if not counter_key.find("[") == -1:
            raise Exception("counter_key : [] chars are not allowed, got counter_key={0}".format(counter_key))
        elif not counter_key.find("]") == -1:
            raise Exception("counter_key : [] chars are not allowed, got counter_key={0}".format(counter_key))
        elif not counter_key.find(".discovery") == - 1:
            raise Exception("counter_key : '.discovery' is not allowed, got counter_key={0}".format(counter_key))

        # Value must NOT be a tuple or a list, it must an int,float,bool,string
        if not isinstance(counter_value, (int, float, bool, str)):
            raise Exception("counter_value must be an int, float, bool, basestring k=%s, v=%s type=%s" % (counter_key, counter_value, type(counter_value)))

        if d_values is None:
            d_values = dict()
        if d_tags is None:
            d_tags = dict()

        # Stat
        Meters.aii("knock_stat_notify_value")

        # PID : d_opt_tags : we may receive "PID" in this dict from client libs
        # This will put pressure on supervision backends
        # If we have it, we remove it
        if "PID" in d_tags:
            del d_tags["PID"]

        # Ordered
        d_tags = OrderedDict(sorted(d_tags.items(), key=lambda t: t[0]))

        # Validate
        for k, v in d_tags.items():
            if not isinstance(k, str):
                raise Exception("tags : k must be str, got class={0}, k={1}".format(SolBase.get_classname(k), k))
            elif not isinstance(v, str):
                raise Exception("tags : v must be str, got class={0}, v={1}".format(SolBase.get_classname(v), v))

        # Append
        if not ts:
            ts = time()

        self.superv_notify_value_list.append((counter_key, d_tags, counter_value, ts, d_values))

    # ==============================
    # SUPERV : TOOLS
    # ==============================

    def _reset_superv_notify(self):
        """
        Reset Superv pending notify
        """

        if self.superv_notify_value_list and len(self.superv_notify_value_list) > 0:
            logger.warning("Discarding pending superv_notify_value_list=%s", self.superv_notify_value_list)

        # Reset
        self.superv_notify_value_list = list()

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
                self._account_hash,
                node_hash,
                self.superv_notify_value_list)
            if not b:
                if len(self._ar_knock_transport) == 1:
                    # Only one transport and failed, do not clear the hashes
                    logger.debug("Got false from process_notify and only one transport, will not empty the hashes, t=%s", t)
                    clear_hash = False
                else:
                    # Several transport, we clear in call cases
                    logger.warning("Got false from process_notify and multi transport, will empty the hashes, t=%s", t)

        # We reset if required
        if clear_hash:
            self.superv_notify_value_list = list()

    def get_first_transport_by_type(self, transport_class):
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

    def get_first_meters_prefix_by_type(self, transport_class):
        """
        Get transport meter prefix by type
        :param transport_class: transport class to match
        :return: str
        :rtype str
        """

        return self.get_first_transport_by_type(transport_class).meters_prefix

    # ==============================
    # TOOLS
    # ==============================

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

        # Interval in ms
        exec_interval_ms = p.exec_interval_ms

        # Current
        cur_ms = SolBase.mscurrent()

        # Diff
        diff_ms = cur_ms - next_start_ms

        # Check
        if next_start_ms <= cur_ms:
            if diff_ms > (exec_interval_ms * 2):
                # Interval reached, but GREATER than exec_interval_ms * 2
                # This mean we are late, we skip this one (and we full reset, so we execute again asap)
                logger.warning(
                    "Interval reached but diff_ms > exec_interval_ms*2 (full skip / full reset), cur_ms=%s, next_start_ms=%s, interval*2=%s, diff=%s, p=%s",
                    cur_ms,
                    next_start_ms,
                    exec_interval_ms * 2,
                    cur_ms - next_start_ms,
                    p
                )
                c.exec_count_so_far = 0.0
                c.initial_ms_start = 0.0
                return False
            else:
                # Interval reached and we are not later => yes
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
        for p in self.probe_list:
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

    # =====================================
    # LIFECYCLE
    # =====================================

    def lifecycle_start(self):
        """
        Start
        """

        # Signal
        logger.info("Lifecycle greenlet : starting")

        # Check
        if self._lifecycle_greenlet:
            logger.warning("_lifecycle_greenlet already set, doing nothing")
            return

        # Fire
        self._lifecycle_exit.clear()
        self._lifecycle_greenlet = gevent.spawn(self.lifecycle_run)
        SolBase.sleep(0)
        logger.info("Lifecycle greenlet : started")

    def lifecycle_stop(self):
        """
        Stop
        """

        # Signal
        logger.info("Lifecycle greenlet : stopping, self=%s", id(self))
        self._is_running = False

        # Check
        if not self._lifecycle_greenlet:
            logger.debug("_lifecycle_greenlet not set, doing nothing")
            return

        # Kill
        logger.info("_lifecycle_greenlet.kill")
        self._lifecycle_greenlet.kill()
        SolBase.sleep(0)
        logger.info("_lifecycle_greenlet.kill done")
        # gevent.kill(self._lifecycle_greenlet)
        self._lifecycle_greenlet = None

        # Wait for completion
        logger.info("Lifecycle greenlet : waiting")
        SolBase.sleep(0)
        self._lifecycle_exit.wait()
        SolBase.sleep(0)
        logger.info("Lifecycle greenlet : stopped")

    def lifecycle_run(self):
        """
        Run
        """
        try:
            logger.info("Entering loop")
            while self._is_running:
                try:
                    # Check
                    if SolBase.msdiff(self._lifecycle_last_ms) < self._lifecycle_interval_ms:
                        SolBase.sleep(100)
                        continue

                    # Set
                    self._lifecycle_last_ms = SolBase.mscurrent()

                    # Flush stuff
                    Meters.write_to_logger()

                    # Check transport
                    if len(self._ar_knock_transport) == 0:
                        logger.warning("No transport defined, daemon running in noop mode, please configure at least one transport")

                    # ---------------------
                    # Loop over transports
                    # ---------------------
                    for cur_transport in self._ar_knock_transport:
                        # noinspection PyProtectedMember
                        lifecyclelogger.info(
                            "Running (pf=%s), "
                            "q.c/bytes/limit=%s/%s/%s, "
                            "q.max=%s, "
                            "discard.c/c_bytes=%s/%s, "
                            "transp_buf.len.pend/last/max=%s/%s/%s, "
                            "transp_wire.len.last/max=%s/%s, "
                            "transp_wire.ms.last/max=%s/%s, "
                            "http.count:ok/ex/fail=%s:%s/%s/%s, "
                            "spv.ok/ko=%s/%s, "
                            "id=%s",
                            cur_transport.meters_prefix,

                            cur_transport._queue_to_send.qsize(),
                            cur_transport._current_queue_bytes,
                            cur_transport._max_bytes_in_queue,

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_queue_max_size"),

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_queue_discard"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_queue_discard_bytes"),

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_buffer_pending_length"),

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_buffer_last_length"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_buffer_max_length"),

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_wire_last_length"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_wire_max_length"),

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_wire_last_ms"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_wire_max_ms"),

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_call_count"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_ok_count"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_exception_count"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_failed_count"),

                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_spv_processed"),
                            Meters.aig(cur_transport.meters_prefix + "knock_stat_transport_spv_failed"),
                            id(cur_transport),
                        )

                    # UDP
                    lifecyclelogger.info(
                        "Running, UDP, "
                        "recv.count:C/G/DTC=%s:%s/%s/%s, "
                        "recv.unk/ex=%s/%s, "
                        "notif.count/ex=%s/%s, "
                        "self=%s",
                        Meters.aig("knock_stat_udp_recv"),
                        Meters.aig("knock_stat_udp_recv_counter"),
                        Meters.aig("knock_stat_udp_recv_gauge"),
                        Meters.aig("knock_stat_udp_recv_dtc"),
                        Meters.aig("knock_stat_udp_recv_unknown"),
                        Meters.aig("knock_stat_udp_recv_ex"),
                        Meters.aig("knock_stat_udp_notify_run"),
                        Meters.aig("knock_stat_udp_notify_run_ex"),
                        id(self),
                    )

                except GreenletExit:
                    logger.info("GreenletExit in loop2")
                    self._lifecycle_exit.set()
                    return
                except Exception as e:
                    logger.warning("Exception in loop2=%s", SolBase.extostr(e))
        except GreenletExit:
            logger.info("GreenletExit in loop1")
            self._lifecycle_exit.set()
        finally:
            logger.info("Exiting loop")
            self._lifecycle_exit.set()
            SolBase.sleep(0)

    @classmethod
    def try_dynamic_load_probe(cls, probe_dir):
        """
        Dynamic load and allocate all probes in specified dir
        :param probe_dir: str
        :type probe_dir: str
        :return: tuple (list of KnockProbes allocated, list of files created)
        :rtype tuple
        """

        # If we are in test, we do not load
        if "KNOCK_UNITTEST" in os.environ:
            return [], []

        ar_files = list()
        ar_probes = list()

        # Go
        logger.info("Trying to load probes, probe_dir=%s", probe_dir)
        if not FileUtility.is_dir_exist(probe_dir):
            logger.info("Directory not present, give up, probe_dir=%s", probe_dir)
            return ar_probes, ar_files

        # Locate __init__py., if not found, add it toward all dir if required
        if not FileUtility.is_file_exist(probe_dir + "__init__.py"):
            FileUtility.append_text_to_file(probe_dir + "__init__.py", "# auto-generated by knockdaemon2", encoding="utf8")
            logger.info("Added %s", probe_dir + "__init__.py")
            ar_files.append(probe_dir + "__init__.py")

        # Browse
        for filename in glob.glob(probe_dir + "*.py"):
            dn = os.path.dirname(filename)
            bn = os.path.basename(filename)
            module_name = os.path.splitext(bn)[0]
            try:
                # Path
                logger.info("Adding to path, dn=%s", dn)
                sys.path.append(dn)
                # Load
                logger.info("Importing module_name=%s, from filename=%s", module_name, filename)
                cur_module = importlib.import_module(module_name)
                # Browse
                for name, obj in inspect.getmembers(cur_module):
                    logger.debug("checking, name=%s", name)
                    if inspect.isclass(obj):
                        logger.debug("module_name=%s, name=%s, obj=%s, cn=%s", module_name, name, obj, SolBase.get_classname(obj))
                        # Bypass raw
                        if obj == KnockProbe:
                            continue
                        # Check inheritance
                        if issubclass(obj, KnockProbe):
                            logger.info("Detected KnockProbe, module_name=%s, name=%s, obj=%s, cn=%s", module_name, name, obj, SolBase.get_classname(obj))

                            # Mro (may be usefull later on when we will support multiple derivation in a single .py)
                            mro = inspect.getmro(obj)
                            logger.info("mro=%s", mro)

                            # Try to allocate
                            i_obj = obj()
                            logger.info("Allocated, i_obj=%s", i_obj)
                            ar_probes.append(i_obj)
            except Exception as e:
                logger.warning("Exception while loading probes, ex=%s", SolBase.extostr(e))

        # Over
        return ar_probes, ar_files
