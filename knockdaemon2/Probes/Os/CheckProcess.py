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

import json
import logging

import ntpath
import psutil
from os.path import dirname, abspath
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    from knockdaemon2.Windows.Wmi.Wmi import Wmi

logger = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
class CheckProcess(KnockProbe):
    """
    Probe
    """

    JSON_CONFIG_FILE = "process_json_configfile"

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.json_config_file = None
        self.process_config = None
        self.category = "/os/process"

    def init_from_config(self, config_parser, section_name):
        """
        Initialize from configuration
        :param config_parser: dict
        :type config_parser: dict
        :param section_name: Ini file section for our probe
        :type section_name: str
        """

        # Base
        KnockProbe.init_from_config(self, config_parser, section_name)

        # Go
        self.json_config_file = config_parser[section_name][CheckProcess.JSON_CONFIG_FILE]

        # --------------------
        # Patches (fucking paths)
        # We extract file name and rebase to config root dir
        # --------------------
        file_name = ntpath.basename(self.json_config_file)
        # noinspection PyProtectedMember
        root_dir = dirname(abspath(self._knock_manager._config_file_name))
        self.json_config_file = SolBase.get_pathseparator().join([root_dir, file_name])
        logger.info("Rebased json_config_file=%s", self.json_config_file)

        # Ok
        self.process_config = json.load(open(self.json_config_file, 'r'))
        logger.info("process_config=%s", self.process_config)

        # Default to linux
        for k, d in self.process_config.iteritems():
            if "os" not in d:
                logger.info("Switching k=%s to os=linux (default)", k)
                d["os"] = "linux"
            logger.info("Got process k=%s, d=%s", k, d)

        # ----------------------------------
        # If OS is windows, we MUST register the request to fetch for
        # ----------------------------------

        if PTools.get_distribution_type() == "windows":
            self._windows_register_wmi()

    def _execute_linux(self):
        """
        Execute
        """

        # Issue #63 : bypass
        # if True:
        #            return

        for checker, param in self.process_config.iteritems():
            if param["os"] != "linux":
                logger.info("Bypassing checker=%s due to os=%s", checker, param["os"])
                continue

            logger.info("Processing checker=%s, param=%s", checker, param)
            pid_file = param['pid']
            startup = param['startup']
            checker = str(checker)

            # 2 cases : str (legacy) or list (new code & config)
            if isinstance(startup, list):
                logger.info("Using startup as list, startup=%s", startup)
                ar_startup = startup
            else:
                logger.info("Using startup as str (legacy), startup=%s", startup)
                ar_startup = [startup]

            # Browse
            logger.info("Checking ar_startup=%s", ar_startup)
            found_startup = None
            for cur_startup in ar_startup:
                try:
                    logger.info("Check cur_startup=%s", cur_startup)
                    with open(cur_startup):
                        found_startup = cur_startup
                except IOError as e:
                    logger.warn("IOError for cur_startup=%s, ex=%s", cur_startup, SolBase.extostr(e))
                    continue
                except Exception as e:
                    logger.warn("Exception for cur_startup=%s, ex=%s", cur_startup, SolBase.extostr(e))
                    continue

            # Check
            if not found_startup:
                logger.info("No valid found_startup, giveup")
                continue

            # Ok
            logger.info("Got found_startup=%s, processing checker=%s against pid=%s", found_startup, checker, pid_file)

            # add discovery
            self.notify_discovery_n("k.proc.discovery", {"PROCNAME": checker})

            # read pid
            try:
                logger.info("Reading pid_file=%s", pid_file)
                pid = int(open(pid_file, "r").readline())
                pid_file_present = "ok"
            except IOError as e:
                logger.warn("IOError for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
                pid_file_present = "missing"
                pid = 0
            except ValueError as e:
                logger.warn("ValueError for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
            except Exception as e:
                logger.warn("Exception for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
            finally:
                self.notify_value_n("k.proc.pidfile", {"PROCNAME": checker}, pid_file_present)

            # psutil
            try:
                logger.info("Process call now for pid=%s", pid)
                psutil.Process(pid)
            except psutil.NoSuchProcess as e:
                logger.warn("NoSuchProcess (Process) for pid=%s, ex=%s", pid, SolBase.extostr(e))
                self.notify_value_n("k.proc.running", {"PROCNAME": checker}, "crash")
                continue
            except Exception as e:
                logger.warn("Exception (Process) for pid=%s, ex=%s", pid, SolBase.extostr(e))
                self.notify_value_n("k.proc.running", {"PROCNAME": checker}, "crash")
                continue

            self.notify_value_n("k.proc.running", {"PROCNAME": checker}, "ok")

            num_fds = 0
            memory_used = 0
            cpu_used = 0
            nb_process = 0
            for process in psutil.process_iter():
                # Get stats for senior and junior
                if process.ppid == pid or process.pid == pid:
                    nb_process += 1
                    # noinspection PyProtectedMember
                    p = psutil.Process(process._pid)

                    d = p.as_dict()
                    logger.info("as_dict=%s", d)

                    # as_dict :
                    #
                    # d = {'username': 'root',
                    #      'num_ctx_switches': pctxsw(voluntary=10, involuntary=0),
                    #      'pid': 1903,
                    #      'memory_full_info': None,
                    #      'connections': None,
                    #      'cmdline': ['nginx: master process /usr/sbin/nginx -g daemon on; master_process on;'],
                    #      'create_time': 1460448473.98,
                    #      'memory_info_ex': pmem(rss=1925120, vms=150462464, shared=1519616, text=1339392, lib=0, data=3153920, dirty=0),
                    #      'ionice': pionice(ioclass=0, value=4),
                    #      'num_fds': None,
                    #      'memory_maps': None,
                    #      'cpu_percent': 0.0,
                    #      'terminal': None,
                    #      'ppid': 1,
                    #      'cwd': None,
                    #      'nice': 0,
                    #      'status': 'sleeping',
                    #      'cpu_times': pcputimes(user=0.0, system=0.0, children_user=0.0, children_system=0.0),
                    #      'io_counters': None,
                    #      'memory_info': pmem(rss=1925120, vms=150462464, shared=1519616, text=1339392, lib=0, data=3153920, dirty=0),
                    #      'threads': [pthread(id=1903, user_time=0.0, system_time=0.0)], 'open_files': None, 'name': 'nginx', 'num_threads': 1,
                    #      'exe': None,
                    #      'uids': puids(real=0, effective=0, saved=0), 'gids': pgids(real=0, effective=0, saved=0),
                    #      'cpu_affinity': [0, 1, 2, 3],
                    #      'memory_percent': 0.030791102026644132,
                    #      'environ': None}

                    # TODO : debug io counters as root
                    read_bytes = 0
                    write_bytes = 0
                    try:
                        io_stat = p.io_counters()
                        read_bytes += io_stat[2]
                        write_bytes += io_stat[3]
                        self.notify_value_n("k.proc.io.read_bytes", {"PROCNAME": checker}, read_bytes)
                        self.notify_value_n("k.proc.io.write_bytes", {"PROCNAME": checker}, write_bytes)

                    except psutil.AccessDenied as e:
                        logger.warn(
                            "io_counters failed, checker=%s, pid_file=%s, e=%s",
                            checker, pid_file,
                            SolBase.extostr(e))
                    except NotImplementedError:
                        # patch rapsberry NotImplementedError: couldn't find /proc/xxxx/io (kernel too old?)
                        logger.info("Couldn't find /proc/xxxx/io (possible kernel too old), discarding k.proc.io.read_bytes / k.proc.io.write_bytes")

                    cpu_user = d["cpu_times"].user
                    cpu_system = d["cpu_times"].system

                    rss_memory = d["memory_info"].rss

                    memory_used += rss_memory

                    # FD : can be None
                    # TODO : debug num_fds as root
                    v = d.get("num_fds")
                    if v:
                        num_fds += v
                    else:
                        logger.warn("num_fds None")

                    cpu_used += cpu_system + cpu_user

            self.notify_value_n("k.proc.io.num_fds", {"PROCNAME": checker}, num_fds)
            self.notify_value_n("k.proc.memory_used", {"PROCNAME": checker}, memory_used)
            self.notify_value_n("k.proc.cpu_used", {"PROCNAME": checker}, cpu_used)
            self.notify_value_n("k.proc.nbprocess", {"PROCNAME": checker}, nb_process)

    # ======================================
    # WINDOWS
    # ======================================

    # noinspection SqlDialectInspection,SqlNoDataSourceInspection,PyProtectedMember
    def _windows_register_wmi(self):
        """
        Register WQL inside wmi
        """

        try:
            logger.info("Windows mode, registering WQL into Wmi for process fetch")

            # "WQL_ConnectedUsers": {"type": "wql", "statement": "SELECT LogonType FROM Win32_LogonSession WHERE LogonType=10", "read": "count", "min_client": "Windows Vista", "min_server": "Windows Server 2008", },
            wql_where = ""
            for k, d in self.process_config.iteritems():
                if d["os"] != "windows":
                    continue
                p_name = d["name"]
                if isinstance(p_name, (str, unicode)):
                    # DIRECT
                    if len(wql_where) > 0:
                        wql_where += " or Name='%s'" % p_name
                    else:
                        wql_where += "Name='%s'" % p_name
                elif isinstance(p_name, (tuple, list)):
                    for cur_name in p_name:
                        if len(wql_where) > 0:
                            wql_where += " or Name='%s'" % cur_name
                        else:
                            wql_where += "Name='%s'" % cur_name

            # Finish it
            if len(wql_where) > 0:
                # Got some, register
                wql = "SELECT Name, HandleCount, WorkingSetSize, UserModeTime, KernelModeTime, ReadTransferCount, WriteTransferCount FROM Win32_Process WHERE " + wql_where
                Wmi._WMI_INSTANCES["WQL_Processes"] = {
                    "type": "wql",
                    "statement": wql,
                    "read": "list",
                    "min_client": "Windows Vista", "min_server": "Windows Server 2008",
                }
                logger.info("Registered WMI WQL_Processes=%s", Wmi._WMI_INSTANCES["WQL_Processes"])
            else:
                logger.info("No windows process to handle, bypass")

        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))

    # noinspection PyMethodMayBeStatic
    def _get_wmi_process(self, d, name):
        """
        Get wmi process dict
        :param d: dict
        :type d: dict
        :param name: process name
        :type name: str,unicode
        :return list of dict
        :rtype list
        """

        ar_out = list()
        for cur_d in d["WQL_Processes"]:
            if cur_d.get("Name") == name:
                ar_out.append(cur_d)
        return ar_out

    def _execute_windows(self):
        """
        Exec
        """

        try:
            d, age_ms = Wmi.wmi_get_dict()
            logger.info("Using wmi with age_ms=%s", age_ms)

            # Browse
            for checker, param in self.process_config.iteritems():
                # Bypass linux
                if param["os"] != "windows":
                    logger.info("Bypassing checker=%s due to os=%s", checker, param["os"])
                    continue

                # Check Wmi
                if "WQL_Processes" not in d:
                    logger.warn("WQL_Processes not in d, bypassing checker=%s", checker)

                # Handle list or direct
                p_name = param["name"]
                if isinstance(p_name, (str, unicode)):
                    ar_name = [p_name]
                else:
                    ar_name = p_name

                # Browse
                for p_name in ar_name:
                    # Name
                    logger.info("Processing p_name=%s", p_name)

                    # Ok, get process dict (can retrieve several hits)
                    ar_process = self._get_wmi_process(d, p_name)
                    if len(ar_process) == 0:
                        logger.warn("Got no process for p_name=%s, bypass", p_name)
                        continue

                    # Ok got some
                    logger.info("Got %s process for p_name=%s", len(ar_process), p_name)

                    # -------------------------
                    # Ok so
                    # -------------------------
                    # Disco id
                    pid = checker

                    # Disco
                    self.notify_discovery_n("k.proc.discovery", {"PROCNAME": pid})

                    # Stat dict
                    p_stat = dict()

                    # Init static stuff (windows : we got the process, it is running)
                    p_stat["k.proc.pidfile"] = "ok"
                    p_stat["k.proc.running"] = "ok"
                    p_stat["k.proc.nbprocess"] = len(ar_process)
                    p_stat["k.proc.running"] = "ok"

                    # Init
                    p_stat["k.proc.io.num_fds"] = 0
                    p_stat["k.proc.memory_used"] = 0
                    p_stat["k.proc.cpu_used"] = 0
                    p_stat["k.proc.io.read_bytes"] = 0
                    p_stat["k.proc.io.write_bytes"] = 0

                    # Browse
                    for cur_d in ar_process:
                        # Handle count
                        p_stat["k.proc.io.num_fds"] += int(cur_d.get("HandleCount", 0))
                        # In bytes
                        p_stat["k.proc.memory_used"] += int(cur_d.get("WorkingSetSize", 0))
                        # Cpu used
                        # We need cumulative values, we have, it comes in millis, we need seconds
                        cpu_time = int(cur_d.get("KernelModeTime", 0)) + int(cur_d.get("UserModeTime", 0))
                        cpu_time /= 1000
                        p_stat["k.proc.cpu_used"] += cpu_time
                        # R/W
                        p_stat["k.proc.io.read_bytes"] = int(cur_d.get("ReadTransferCount", 0))
                        p_stat["k.proc.io.write_bytes"] = int(cur_d.get("WriteTransferCount", 0))

                    # Ok
                    for k, v in p_stat.iteritems():
                        logger.info("Got %s=%s", k, v)

                    # Notify
                    for k, v in p_stat.iteritems():
                        self.notify_value_n(k, {"PROCNAME": pid}, v)
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
