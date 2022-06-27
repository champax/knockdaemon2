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

import json
import logging
import ntpath
from os.path import dirname, abspath

import psutil
from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


def get_process_list():
    """
    Get process list
    :return: list of Process
    :rtype list,Generator
    """
    return psutil.process_iter()


def get_io_counters(pid):
    """
    Get io counters
    :param pid: int
    :type pid: int
    :return: psutil._pslinux.pio
    :rtype psutil._pslinux.pio
    """
    return psutil.Process(pid).io_counters()


def get_process_stat(pid):
    """
    Get process stats
    :param pid: int
    :type pid: int
    :return: dict
    :rtype dict
    """
    return psutil.Process(pid).as_dict()


def read_pid(pid_file):
    """
    Read pid file
    :param pid_file: str
    :type pid_file: str
    :return int
    :rtype int
    """
    with open(pid_file, "r") as f:
        return int(f.readline())


def call_psutil_process(pid):
    """
    Call
    :param pid: int
    :type pid: int
    """
    psutil.Process(pid)


# noinspection PyUnresolvedReferences
class CheckProcess(KnockProbe):
    """
    Check process

    Configuration expected is like
    "nginx": {
        "startup": "/etc/nginx/nginx.conf",
        "pid": "/var/run/nginx.pid"
    },
    "nginx_array": {
        "startup": [
            "/etc/nginx/nginx.conf.invalid",
            "/etc/nginx/nginx.conf"
        ],
        "pid": "/var/run/nginx.pid"
    }
    """

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

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

        # Load our config

        # --------------------
        # Patches (fucking paths)
        # We extract file name and rebase to config root dir
        # --------------------
        s = d["process_json_configfile"]
        s = ntpath.basename(s)

        # noinspection PyProtectedMember
        root_dir = dirname(abspath(self._knock_manager._config_file_name))

        s = SolBase.get_pathseparator().join([root_dir, s])
        logger.debug("Rebased json_config_file=%s", s)
        self.load_json_config(s)

    def load_json_config(self, json_config_file):
        """
        Load json config
        :param json_config_file: str
        :type json_config_file: str
        """

        self.json_config_file = json_config_file

        # Ok
        with open(self.json_config_file, 'r') as f:
            self.process_config = json.load(f)
        logger.debug("Loaded process_config=%s", self.process_config)

        # Log
        for k, d in self.process_config.items():
            logger.debug("Got process k=%s, d=%s", k, d)

    def _execute_linux(self):
        """
        Execute
        """

        for process_key, d_process in self.process_config.items():
            process_key = str(process_key)
            logger.debug("Processing process_key=%s, d_process=%s", process_key, d_process)
            pid_file = d_process['pid']
            startup = d_process['startup']

            # 2 cases : str (legacy) or list (new code & config)
            if isinstance(startup, list):
                logger.debug("Using startup as list, startup=%s", startup)
                ar_startup = startup
            else:
                logger.debug("Using startup as str (legacy), startup=%s", startup)
                ar_startup = [startup]

            # Browse
            logger.debug("Checking ar_startup=%s", ar_startup)
            found_startup = None
            for cur_startup in ar_startup:
                try:
                    logger.debug("Check cur_startup=%s", cur_startup)
                    with open(cur_startup):
                        found_startup = cur_startup
                except IOError as e:
                    logger.debug("IOError for cur_startup=%s, ex=%s", cur_startup, SolBase.extostr(e))
                    continue
                except Exception as e:
                    logger.debug("Exception for cur_startup=%s, ex=%s", cur_startup, SolBase.extostr(e))
                    continue

            # Check
            if not found_startup:
                logger.debug("No valid found_startup, giveup")
                continue

            # Ok
            logger.debug("Got found_startup=%s, processing process_key=%s against pid=%s", found_startup, process_key, pid_file)

            # read pid
            pid_file_present = "missing"
            pid = 0
            try:
                logger.debug("Reading pid_file=%s", pid_file)
                pid = read_pid(pid_file)
                pid_file_present = "ok"
            except IOError as e:
                logger.warning("IOError for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
                pid = 0
            except ValueError as e:
                logger.warning("ValueError for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
            except Exception as e:
                logger.warning("Exception for pid_file=%s, ex=%s", pid_file, SolBase.extostr(e))
            finally:
                self.notify_value_n("k.proc.pidfile", {"PROCNAME": process_key}, pid_file_present)

            # psutil
            try:
                logger.debug("Process call now for pid=%s", pid)
                call_psutil_process(pid)
            except psutil.NoSuchProcess as e:
                logger.warning("NoSuchProcess for pid=%s, ex=%s", pid, SolBase.extostr(e))
                self.notify_value_n("k.proc.running", {"PROCNAME": process_key}, "crash")
                continue
            except Exception as e:
                logger.warning("Exception (Process) for pid=%s, ex=%s", pid, SolBase.extostr(e))
                self.notify_value_n("k.proc.running", {"PROCNAME": process_key}, "crash")
                continue

            self.notify_value_n("k.proc.running", {"PROCNAME": process_key}, "ok")

            num_fds = 0
            memory_used = 0
            cpu_used = 0
            nb_process = 0
            for process in get_process_list():
                # Get stats for senior and junior
                if process.ppid == pid or process.pid == pid:
                    nb_process += 1

                    # noinspection PyProtectedMember
                    d = get_process_stat(process._pid)

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

                    read_bytes = 0
                    write_bytes = 0
                    try:
                        io_stat = get_io_counters(pid)
                        read_bytes += io_stat[2]
                        write_bytes += io_stat[3]
                        self.notify_value_n("k.proc.io.read_bytes", {"PROCNAME": process_key}, read_bytes)
                        self.notify_value_n("k.proc.io.write_bytes", {"PROCNAME": process_key}, write_bytes)

                    except psutil.AccessDenied as e:
                        logger.warning("io_counters failed, process_key=%s, pid_file=%s, e=%s", process_key, pid_file, SolBase.extostr(e))
                    except NotImplementedError:
                        # patch rapsberry NotImplementedError: couldn't find /proc/xxxx/io (kernel too old?)
                        logger.debug("Couldn't find /proc/xxxx/io (possible kernel too old), discarding k.proc.io.read_bytes / k.proc.io.write_bytes")

                    # Fetch
                    cpu_user = d["cpu_times"].user
                    cpu_system = d["cpu_times"].system
                    rss_memory = d["memory_info"].rss
                    memory_used += rss_memory
                    cpu_used += cpu_system + cpu_user

                    # This one can be None
                    v = d.get("num_fds")
                    if v:
                        num_fds += v

            # Over
            self.notify_value_n("k.proc.io.num_fds", {"PROCNAME": process_key}, num_fds)
            self.notify_value_n("k.proc.memory_used", {"PROCNAME": process_key}, memory_used)
            self.notify_value_n("k.proc.cpu_used", {"PROCNAME": process_key}, cpu_used)
            self.notify_value_n("k.proc.nbprocess", {"PROCNAME": process_key}, nb_process)
