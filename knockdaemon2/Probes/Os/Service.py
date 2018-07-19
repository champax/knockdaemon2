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

from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe
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

    def __init__(self):
        """
        Init
        """
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.patern_list= list()
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

        self.notify_value_n("k.os.service.running_count", None, len(running_checked))

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
