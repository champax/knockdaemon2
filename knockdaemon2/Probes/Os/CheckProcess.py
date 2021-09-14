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

import json
import logging
import ntpath
from os.path import dirname, abspath

import psutil
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    pass

logger = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
class CheckProcess(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.json_config_file = None
        self.process_config = None
        self.category = "/os/process"

    def init_from_config(self, k, d_yaml_config, d):
        """
        Initialize from configuration
        :param k: str
        :type k: str
        :param d_yaml_config: full conf
        :type d_yaml_config: d
        :param d: local conf
        :type d: dict
        """

        # Base
        KnockProbe.init_from_config(self, k, d_yaml_config, d)

        # Go
        self.json_config_file = d["process_json_configfile"]

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
        for k, d in self.process_config.items():
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

        for checker, param in self.process_config.items():
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
                    logger.warning("IOError for cur_startup=%s, ex=%s", cur_startup, SolBase.extostr(e))
                    continue
                except Exception as e:
                    logger.warning("Exception for cur_startup=%s, ex=%s", cur_startup, SolBase.extostr(e))
                    continue

            # Check
            if not found_startup:
                logger.info("No valid found_startup, giveup")
                continue

            # Ok
            logger.info("Got found_startup=%s, processing checker=%s against pid=%s", found_startup, checker, pid_file)

            # read pid
            pid_file_present = "missing"
            pid = 0
            try:
                logger.info("Reading pid_file=%s", pid_file)
                pid = int(open(pid_file, "r").readline())
                pid_file_present = "ok"
            except IOError as e:
                logger.warning("IOError for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
                pid_file_present = "missing"
                pid = 0
            except ValueError as e:
                logger.warning("ValueError for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
            except Exception as e:
                logger.warning("Exception for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
            finally:
                self.notify_value_n("k.proc.pidfile", {"PROCNAME": checker}, pid_file_present)

            # psutil
            try:
                logger.info("Process call now for pid=%s", pid)
                psutil.Process(pid)
            except psutil.NoSuchProcess as e:
                logger.warning("NoSuchProcess (Process) for pid=%s, ex=%s", pid, SolBase.extostr(e))
                self.notify_value_n("k.proc.running", {"PROCNAME": checker}, "crash")
                continue
            except Exception as e:
                logger.warning("Exception (Process) for pid=%s, ex=%s", pid, SolBase.extostr(e))
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
                    logger.debug("as_dict=%s", d)

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
                        logger.warning(
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
                        logger.warning("num_fds None")

                    cpu_used += cpu_system + cpu_user

            self.notify_value_n("k.proc.io.num_fds", {"PROCNAME": checker}, num_fds)
            self.notify_value_n("k.proc.memory_used", {"PROCNAME": checker}, memory_used)
            self.notify_value_n("k.proc.cpu_used", {"PROCNAME": checker}, cpu_used)
            self.notify_value_n("k.proc.nbprocess", {"PROCNAME": checker}, nb_process)
