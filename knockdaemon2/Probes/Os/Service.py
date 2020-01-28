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
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    pass

logger = logging.getLogger(__name__)

# SALT Steal
SYSTEM_CONFIG_PATHS = ('/lib/systemd/system', '/usr/lib/systemd/system')
LOCAL_CONFIG_PATH = '/etc/systemd/system'
INITSCRIPT_PATH = '/etc/init.d'
VALID_UNIT_TYPES = ('service', 'socket', 'device', 'mount', 'automount',
                    'swap', 'target', 'path', 'timer')


# noinspection PyMethodMayBeStatic
class Service(KnockProbe):
    """
    Doc
    """
    SERVICE_PATERNS = list()
    regex_find_pid = re.compile(r' Main PID: ([0-9]+)')

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=False)
        self.helpers = KnockHelpers()

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

        if len(Service.SERVICE_PATERNS) == 0:
            for p in self.patern_list:
                try:
                    Service.SERVICE_PATERNS.append(re.compile(p))
                except Exception as e:
                    logger.warning(SolBase.extostr(e))

        installed_service = set(self._get_local_services())

        ######################
        #  Build service to check
        ######################
        service_to_check = set()
        for p in self.SERVICE_PATERNS:
            for s in installed_service:
                if p.match(s):
                    service_to_check.update([s])

        running_service = set(self._get_running())
        not_running_service = installed_service - running_service
        running_checked = running_service.intersection(service_to_check)
        for s in not_running_service.intersection(service_to_check):
            self.notify_value_n("k.os.service.running", {"SERVICE": s}, 0)
        for s in running_checked:
            self.notify_value_n("k.os.service.running", {"SERVICE": s}, 1)
            try:
                self._service_meters(s)
            except Exception:
                # Low level log.
                pass

        self.notify_value_n("k.os.service.running_count", None, len(running_checked))

        # -----------------------------
        # Handle uwsgi
        # -----------------------------
        # TODO : handle not running uwsgi process based on app-enabled configurations files versus processes enumerated
        d_uwsgi = self.uwsgi_get_processes()
        for uwsgi_type, uwsgi_pid in d_uwsgi.items():
            # Notify running
            self.notify_value_n("k.os.service.running", {"SERVICE": uwsgi_type}, 1)
            # Notify processes
            self._notify_process(pid=uwsgi_pid, service=uwsgi_type)

    def _execute_windows(self):
        """
        Windows
        """

        return

    def _get_local_services(self):
        """

        :return:
        """
        ret = self._get_systemd_services()
        ret.update(set(self._get_sysv_services(systemd_services=ret)))

        # Filter .dpkg-new service
        ret = [service for service in ret if not service.find(".dpkg-new") > 0]

        return sorted(ret)

    def _get_running(self):
        """
        Return a list of all running services, so far as systemd is concerned

        :return:
        """
        ret = set()
        # Get running systemd units
        cmd = "systemctl --full --no-legend --no-pager"
        ec, out, se = ButcherTools.invoke(cmd, shell=False, timeout_ms=10 * 1000)
        if ec != 0:
            logger.warn("Invoke failed, ec=%s, so=%s, se=%s", ec, out, se)
            return list()
        else:
            logger.info("Invoke ok, ec=%s, so=%s, se=%s", ec, str(out.split('\n')[0:10]) + "...", se)

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
                logger.error(SolBase.extostr(exc))
                continue
            except IndexError as e:
                logger.warning(SolBase.extostr(e))
            else:
                if active_state != 'running':
                    continue
            try:
                unit_name, unit_type = fullname.rsplit('.', 1)
            except ValueError:
                continue
            if unit_type in VALID_UNIT_TYPES:
                ret.add(unit_name if unit_type == 'service' else fullname)

        return ret

    def _get_systemd_services(self):
        """
        Use os.listdir() to get all the unit files

        :return:
        """
        ret = set()
        for path in SYSTEM_CONFIG_PATHS + (LOCAL_CONFIG_PATH,):
            # Make sure user has access to the path, and if the path is a link
            # it's likely that another entry in SYSTEM_CONFIG_PATHS or LOCAL_CONFIG_PATH
            # points to it, so we can ignore it.
            if os.access(path, os.R_OK) and not os.path.islink(path):
                for fullname in os.listdir(path):
                    try:
                        unit_name, unit_type = fullname.rsplit('.', 1)
                    except ValueError:
                        continue
                    if unit_type in VALID_UNIT_TYPES:
                        ret.add(unit_name if unit_type == 'service' else fullname)
        return ret

    def _get_sysv_services(self, systemd_services=None):
        """
        Use os.listdir() and os.access() to get all the initscripts

        :param systemd_services:
        :return:
        """
        try:
            sysv_services = os.listdir(INITSCRIPT_PATH)
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                pass
            elif exc.errno == errno.EACCES:
                logger.error(
                    'Unable to check sysvinit scripts, permission denied to %s',
                    INITSCRIPT_PATH
                )
            else:
                logger.error(
                    'Error %d encountered trying to check sysvinit scripts: %s',
                    exc.errno,
                    exc.strerror
                )
            return []

        if systemd_services is None:
            systemd_services = self._get_systemd_services()

        ret = []
        for sysv_service in sysv_services:
            if os.access(os.path.join(INITSCRIPT_PATH, sysv_service), os.X_OK):
                if sysv_service in systemd_services:
                    logger.debug(
                        'sysvinit script \'%s\' found, but systemd unit '
                        '\'%s.service\' already exists',
                        sysv_service, sysv_service
                    )
                    continue
                ret.append(sysv_service)
        return ret

    def _service_meters(self, s):
        """
        notif file open, memory

        :param s: Service name
        :type s: str
        :return:
        """
        # get pid
        manager = SystemdManager()

        if not manager.is_active("%s.service" % s):
            logger.warn("service %s is not active", s)
            return

        pid = manager.get_pid("%s.service" % s)
        logger.debug("notify process %s pid %s", s, pid)
        self._notify_process(pid, s)

    @classmethod
    def uwsgi_get_processes(cls):
        """
        Process uwsgi processes (parent processes only as underlying process probe act recursively)
        :return dict, uwsgi_type => PID (parent pid ONLY)
        :rtype dict
        """

        # We are logging for uwsgi command line formatted as :
        # /usr/bin/uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/vulogboapi.ini --daemonize /var/log/uwsgi/app/vulogboapi.log

        # We store a dict : uwsgi_type => PARENT PID (only)
        d_uwsgi = dict()

        # Enumerate all processes
        for proc in psutil.process_iter():
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

            logger.info("Uwsgi detected, s_type=%s, pid=%s")

        # Ok
        logger.info("Got d_uwsgi.keys=%s", d_uwsgi.keys())
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

    def _notify_process(self, pid, service):
        """

        :param pid:
        :type pid: int
        :param service: service name
        :type service: str
        :return:
        """
        p = psutil.Process(pid)
        children = p.children(recursive=True)

        try:
            io_stat = p.io_counters()
            read_bytes = io_stat[2]
            write_bytes = io_stat[3]

            for c in children:
                c_io_stat = c.io_counters()
                read_bytes += c_io_stat[2]
                write_bytes += c_io_stat[3]

            self.notify_value_n("k.proc.io.read_bytes", {"PROCNAME": service}, read_bytes)
            self.notify_value_n("k.proc.io.write_bytes", {"PROCNAME": service}, write_bytes)
            logger.debug("notify read/write %s/%s service %s", read_bytes, write_bytes, service)

        except psutil.AccessDenied as e:
            logger.warn(
                "io_counters failed, pid=%s, e=%s",
                pid,
                SolBase.extostr(e))
        except NotImplementedError:
            # patch rapsberry NotImplementedError: couldn't find /proc/xxxx/io (kernel too old?)
            logger.info("Couldn't find /proc/xxxx/io (possible kernel too old), discarding k.proc.io.read_bytes / k.proc.io.write_bytes")

        d = p.as_dict()

        cpu_user = d["cpu_times"].user
        cpu_system = d["cpu_times"].system

        rss_memory = d["memory_info"].rss

        num_fds = d.get("num_fds")
        if num_fds is None:
            num_fds = 0
        for c in children:
            d = c.as_dict()
            cpu_user += d["cpu_times"].user
            cpu_system += d["cpu_times"].system

            rss_memory += d["memory_info"].rss

            c_num_fds = d.get("num_fds")
            if c_num_fds is not None:
                num_fds += c_num_fds

        cpu_used = cpu_system + cpu_user
        self.notify_value_n("k.proc.io.num_fds", {"PROCNAME": service}, num_fds)
        self.notify_value_n("k.proc.memory_used", {"PROCNAME": service}, rss_memory)
        self.notify_value_n("k.proc.cpu_used", {"PROCNAME": service}, cpu_used)
