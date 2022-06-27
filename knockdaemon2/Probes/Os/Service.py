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
import errno
import logging
import os
import re

import psutil
from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Core.systemd import SystemdManager

logger = logging.getLogger(__name__)

# SALT Steal
SYSTEM_CONFIG_PATHS = ('/lib/systemd/system', '/usr/lib/systemd/system')
LOCAL_CONFIG_PATH = '/etc/systemd/system'
INITSCRIPT_PATH = '/etc/init.d'
VALID_UNIT_TYPES = ('service', 'socket', 'device', 'mount', 'automount', 'swap', 'target', 'path', 'timer')


def systemd_get_pid(unit_name):
    """
    Get pid
    :param unit_name: str
    :type unit_name: str
    :return: int
    :rtype int
    """
    # Manager
    manager = SystemdManager()

    return manager.get_pid(unit_name)


def systemd_is_active(unit_name):
    """
    Check if it is systemd active
    :param unit_name: str
    :type unit_name: str
    :return: bool
    :rtype bool
    """
    # Manager
    manager = SystemdManager()

    # Check active
    if not manager.is_active("%s.service" % unit_name):
        logger.warning("unit %s is not active", unit_name)
        return False
    else:
        return True


def get_process_list():
    """
    Get process iter
    :return: generator / list of object (must have cmdline / ppid / pid)
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


def get_process_child(pid):
    """
    Get process child
    :param pid: int
    :type pid: int
    :return: list of Process
    :rtype list
    """

    return psutil.Process(pid).children(recursive=True)


def get_process_stat(pid):
    """
    Get process stats
    :param pid: int
    :type pid: int
    :return: dict
    :rtype dict
    """
    return psutil.Process(pid).as_dict()


def get_local_services():
    """
    Get local services list (systemd and sysv, dpkg-new filtered)
    :return set of str
    :rtype set
    """
    ret = get_systemd_services()
    ret.update(get_sysv_services(systemd_services=ret))

    # Filter .dpkg-new service
    ret = [service for service in ret if not service.find(".dpkg-new") > 0]

    return set(ret)


def get_running_services():
    """
    Return a list of all running services, so far as systemd is concerned

    :return: set of str
    :rtype set
    """
    ret = set()
    # Get running systemd units
    cmd = "systemctl --full --no-legend --no-pager"
    ec, out, se = ButcherTools.invoke(cmd, shell=False, timeout_ms=10 * 1000)
    if ec != 0:
        logger.warning("Invoke failed, ec=%s, so=%s, se=%s", ec, out, se)
        return list()
    else:
        logger.debug("Invoke ok, ec=%s, so=%s, se=%s", ec, str(out.split('\n')[0:10]) + "...", se)

    for line in ButcherTools.split(out, '\n'):
        active_state = ''
        fullname = ''
        if line == "":
            continue
        try:
            comps = line.strip().split()
            fullname = comps[0]
            if len(comps) > 3:
                active_state = comps[3]
        except ValueError as exc:
            logger.error("Ex=%s", SolBase.extostr(exc))
            continue
        except IndexError as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
        else:
            if active_state != 'running':
                continue
        try:
            unit_name, unit_type = fullname.rsplit('.', 1)
        except ValueError:
            continue
        if unit_type in VALID_UNIT_TYPES:
            ret.add(unit_name if unit_type == 'service' else fullname)

    return set(ret)


def get_systemd_services():
    """
    Use os.listdir() to get all the unit files

    :return: set of str
    :rtype set
    """
    ret = set()
    for path in SYSTEM_CONFIG_PATHS + (LOCAL_CONFIG_PATH,):
        # Make sure user has access to the path, and if the path is a link
        # it's likely that another entry in SYSTEM_CONFIG_PATHS or LOCAL_CONFIG_PATH
        # points to it, so we can ignore it.
        if not os.access(path, os.R_OK):
            continue
        elif os.path.islink(path):
            continue
        for fullname in os.listdir(path):
            try:
                unit_name, unit_type = fullname.rsplit('.', 1)
            except ValueError:
                continue
            if unit_type in VALID_UNIT_TYPES:
                ret.add(unit_name if unit_type == 'service' else fullname)
    return ret


def get_sysv_services(systemd_services=None):
    """
    Use os.listdir() and os.access() to get all the initscripts

    :param systemd_services: set,None
    :type systemd_services: set,None
    :return: set of str
    :rtype set
    """
    try:
        sysv_services = os.listdir(INITSCRIPT_PATH)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            pass
        elif exc.errno == errno.EACCES:
            logger.error('Unable to check sysvinit scripts, permission denied to %s, ex=%s', INITSCRIPT_PATH, SolBase.extostr(exc))
        else:
            logger.error('Error %d encountered trying to check sysvinit scripts: %s, ex=%s', exc.errno, exc.strerror, SolBase.extostr(exc))
        return []

    if systemd_services is None:
        systemd_services = get_systemd_services()

    ret = []
    for sysv_service in sysv_services:
        if os.access(os.path.join(INITSCRIPT_PATH, sysv_service), os.X_OK):
            if sysv_service in systemd_services:
                logger.debug('sysvinit script \'%s\' found, but systemd unit \'%s.service\' already exists', sysv_service, sysv_service)
                continue
            ret.append(sysv_service)
    return set(ret)


class Service(KnockProbe):
    """
    Doc
    """
    REGEX_FIND_PID = re.compile(r' Main PID: ([0-9]+)')

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=False)
        self.helpers = KnockHelpers()

        self.ar_service = list()
        self.patern_list = list()
        self.category = "/os/services"

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
        self.patern_list = d["patern"]
        pass

    def _execute_linux(self):
        """
        Exec
        """

        # Init if required
        if len(self.ar_service) == 0:
            for p in self.patern_list:
                try:
                    self.ar_service.append(re.compile(p))
                except Exception as e:
                    logger.warning("Ex=%s", SolBase.extostr(e))

        # Get local services
        d_services_local = get_local_services()

        # Get running services
        d_services_running = get_running_services()

        # Services to check
        d_services_to_check = set()
        for p in self.ar_service:
            for s in d_services_local:
                if p.match(s):
                    d_services_to_check.add(s)

        # Not running services
        d_services_not_running = d_services_local - d_services_running

        # Not running, to check => signal DOWN
        d_services_not_running_to_check = d_services_not_running.intersection(d_services_to_check)
        for s in d_services_not_running_to_check:
            self.notify_value_n("k.os.service.running", {"SERVICE": s}, 0)

        # Running, to check => signal UP
        d_services_running_to_check = d_services_running.intersection(d_services_to_check)
        for s in d_services_running_to_check:
            self.notify_value_n("k.os.service.running", {"SERVICE": s}, 1)
            try:
                self.notify_service(s)
            except Exception as e:
                logger.debug("Exception, s=%s, ex=%s", s, SolBase.extostr(e))

        # -----------------------------
        # Handle uwsgi
        # -----------------------------
        d_uwsgi = self.uwsgi_get_processes()
        for uwsgi_type, uwsgi_pid in d_uwsgi.items():
            # Notify running
            self.notify_value_n("k.os.service.running", {"SERVICE": uwsgi_type}, 1)
            # Notify processes
            self.notify_service_pid(pid=uwsgi_pid, service=uwsgi_type)

        # Running count
        self.notify_value_n("k.os.service.running_count", None, len(d_services_running_to_check) + len(d_uwsgi))

    def notify_service(self, service_name):
        """
        Notify
        :param service_name: Service name
        :type service_name: str
        """

        # Check
        if not systemd_is_active(service_name):
            return

        # Get running pid
        pid = systemd_get_pid("%s.service" % service_name)

        # Notify
        self.notify_service_pid(pid, service_name)

    @classmethod
    def uwsgi_get_processes(cls):
        """
        Process uwsgi processes (parent processes only as underlying process probe act recursively)
        :return dict, uwsgi_type => PID (parent pid ONLY)
        :rtype dict
        """

        # We are logging for uwsgi command line formatted as :
        # /usr/bin/uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/zzz.ini --daemonize /var/log/uwsgi/app/zz.log

        # We store a dict : uwsgi_type => PARENT PID (only)
        d_uwsgi = dict()

        # Enumerate all processes
        for proc in get_process_list():
            # Command line
            cmd_line = proc.cmdline()

            # Process uwsgi ONLY
            if len(cmd_line) == 0:
                continue
            elif not cmd_line[0].endswith("/uwsgi"):
                continue

            # Parent only
            c_ppid = proc.ppid()
            if not c_ppid == 1:
                # Not a parent
                continue

            # From command line, get uwsgi init block as string
            s_type = cls.uwsgi_get_type(cmd_line)

            # Add process id
            c_pid = proc.pid
            d_uwsgi[s_type] = c_pid

            logger.debug("Uwsgi detected, type=%s, pid=%s", s_type, c_pid)

        # Ok
        logger.debug("Got d_uwsgi.keys=%s", d_uwsgi.keys())
        return d_uwsgi

    @classmethod
    def uwsgi_get_type(cls, ar_uwsgi_cmd):
        """
        From a uwsgi cmd_line list, extract "--ini" .ini items and return them as string
        return "na" if nothing matches
        :param ar_uwsgi_cmd: list
        :type ar_uwsgi_cmd: list
        :return str
        :rtype str
        """

        ar_out = list()
        is_ini = False
        for s in ar_uwsgi_cmd:
            if s == "--ini":
                is_ini = True
                continue
            if is_ini:
                is_ini = False
                # Got /usr/share/uwsgi/conf/default.ini
                s_ini = s.split("/")[-1].replace(".ini", "")
                ar_out.append(s_ini)

        if len(ar_out) > 0:
            return "uwsgi_" + "_".join(ar_out)
        else:
            return "uwsgi_na"

    def notify_service_pid(self, pid, service):
        """
        Notify service with pid
        :param pid: int
        :type pid: int
        :param service: service name
        :type service: str
        """

        try:
            # Main process
            io_stat = get_io_counters(pid)
            d_stat = get_process_stat(pid)

            read_bytes = io_stat[2]
            write_bytes = io_stat[3]
            cpu_user = d_stat["cpu_times"].user
            cpu_system = d_stat["cpu_times"].system
            rss_memory = d_stat["memory_info"].rss
            num_fds = d_stat.get("num_fds")
            if num_fds is None:
                num_fds = 0

            # Child processes
            ar_child = get_process_child(pid)
            for p_child in ar_child:
                # noinspection PyProtectedMember
                io_stat_child = get_io_counters(p_child._pid)
                # noinspection PyProtectedMember
                d_stat_child = get_process_stat(p_child._pid)

                read_bytes += io_stat_child[2]
                write_bytes += io_stat_child[3]
                cpu_user += d_stat_child["cpu_times"].user
                cpu_system += d_stat_child["cpu_times"].system
                rss_memory += d_stat_child["memory_info"].rss
                c_num_fds = d_stat_child.get("num_fds")
                if c_num_fds is not None:
                    num_fds += c_num_fds

            # Notify
            cpu_used = cpu_system + cpu_user
            self.notify_value_n("k.proc.io.read_bytes", {"PROCNAME": service}, read_bytes)
            self.notify_value_n("k.proc.io.write_bytes", {"PROCNAME": service}, write_bytes)
            self.notify_value_n("k.proc.io.num_fds", {"PROCNAME": service}, num_fds)
            self.notify_value_n("k.proc.memory_used", {"PROCNAME": service}, rss_memory)
            self.notify_value_n("k.proc.cpu_used", {"PROCNAME": service}, cpu_used)

        except psutil.AccessDenied as e:
            logger.warning("io_counters failed, pid=%s, e=%s", pid, SolBase.extostr(e))
        except NotImplementedError:
            # patch rapsberry NotImplementedError: couldn't find /proc/xxxx/io (kernel too old?)
            logger.debug("Couldn't find /proc/xxxx/io (possible kernel too old), discarding k.proc.io.read_bytes / k.proc.io.write_bytes")
