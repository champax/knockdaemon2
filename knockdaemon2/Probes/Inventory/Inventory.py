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

# Thanks to Michael Brown
# https://www.openhub.net/p/python-dmidecode
"""
import logging
import platform

import os
from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)

# """
# Add subprocess.check_output for python 2.6
# """
#
# if "check_output" not in dir(subprocess):
#     def f(*popenargs, **kwargs):
#         """
#         Doc
#         :param popenargs: args
#         :param kwargs: args
#         """
#         if 'stdout' in kwargs:
#             raise ValueError('stdout argument not allowed, it will be overridden.')
#         process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
#         output, unused_err = process.communicate()
#         retcode = process.poll()
#         if retcode:
#             cmd = kwargs.get("args")
#             if cmd is None:
#                 cmd = popenargs[0]
#             raise subprocess.CalledProcessError(retcode, cmd)
#         return output
#
#
#     subprocess.check_output = f

DMI_TYPE = {
    0: 'bios',
    1: 'system',
    2: 'base board',
    3: 'chassis',
    4: 'processor',
    7: 'cache',
    8: 'port connector',
    9: 'system slot',
    10: 'on board device',
    11: 'OEM strings',
    # 13: 'bios language',
    15: 'system event log',
    16: 'physical memory array',
    17: 'memory_device',
    19: 'memory array mapped address',
    24: 'hardware security',
    25: 'system power controls',
    27: 'cooling device',
    32: 'system boot',
    41: 'onboard device',
}


class Inventory(KnockProbe):
    """
    Probe
    """

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Exec
        """

        (sysname, nodename, kernel, version, machine) = os.uname()
        (distribution, dversion, _) = platform.linux_distribution()
        self.notify_value_n("k.inventory.os", None, "%s %s %s" % (sysname, distribution, dversion))
        self.notify_value_n("k.inventory.kernel", None, kernel)
        self.notify_value_n("k.inventory.name", None, nodename)

        # dmidecode
        return_empty = True
        for k, v in self._get_dmi().iteritems():
            return_empty = False
            self.notify_value_n("k.inventory." + k, None, v)

        # fallback dmesg
        if return_empty:
            try:
                # TODO : Why PATH before??
                ec, so, se = ButcherTools.invoke("dmesg")
                if ec != 0:
                    # Non-zero exit code
                    logger.warn("dmesg invoke failed, ec=%s, so=%s, se=%s", ec, so, se)
                else:
                    # Ok, parse
                    if so.find('Booting paravirtualized kernel on Xen'):
                        self.notify_value_n("k.inventory.chassis", None, "Virtual Server XEN")
            except Exception as e:
                logger.warn("Ex=%s", SolBase.extostr(e))

    def _parse_dmi(self, content):
        """
        :param content: str
        :return info: list
        Parse the whole dmidecode output.
        Returns a list of tuples of (type int, value dict).
        """
        info = []
        lines = iter(content.strip().splitlines())
        while True:
            try:
                line = lines.next()
            except StopIteration:
                break

            if line.startswith('Handle 0x'):
                typ = int(line.split(',', 2)[1].strip()[len('DMI type'):])
                if typ in DMI_TYPE:
                    info.append((typ, self._dmi_parse_handle_section(lines)))
        return info

    # noinspection PyMethodMayBeStatic
    def _dmi_parse_handle_section(self, lines):
        """
        :param lines:
        :return : dict: data
        Parse a section of dmidecode output

        * 1st line contains address, type and size
        * 2nd line is title
        * line started with one tab is one option and its value
        * line started with two tabs is a member of list
        """
        data = {
            '_title': lines.next().rstrip(),
        }
        k = 0
        for line in lines:
            line = line.rstrip()
            if line.startswith('\t\t'):
                if isinstance(data[k], list):
                    data[k].append(line.lstrip())
            elif line.startswith('\t'):
                k, v = [i.strip() for i in line.lstrip().split(':', 1)]
                if v:
                    data[k] = v
                else:
                    data[k] = []
            else:
                break

        return data

    # noinspection PyMethodMayBeStatic
    def _filter_dmi(self, info):
        """
        LA DOC MARRAUD
        Doc not found
        :param info:
        :return:
        """

        def _get(ix):
            return [v for j, v in info if j == ix]

        # Output
        dmi = dict()

        # system
        system = _get(1)[0]
        dmi['system'] = '%s %s (SN: %s, UUID: %s)' % (
            system['Manufacturer'],
            system['Product Name'],
            system['Serial Number'],
            system['UUID']
        )

        # vendor
        dmi['vendor'] = system['Manufacturer']

        # serial
        dmi['serial'] = system['Serial Number']

        # cpu
        thread_count = 1
        core_count = 1
        for cpu in _get(4):
            if 'Thread Count' in cpu:
                thread_count = cpu['Thread Count']
            if 'Core Count' in cpu:
                core_count = cpu['Core Count']
            dmi['cpu'] = '%s %s %s (Core: %s, Thead: %s)' % (
                cpu['Manufacturer'],
                cpu['Family'],
                cpu['Max Speed'],
                core_count,
                thread_count
            )

        # mem
        cnt, total, unit = 0, 0, None
        max_mem = 'Unknow'
        for physicalMem in _get(16):
            max_mem = physicalMem['Maximum Capacity']

        for mem in _get(17):
            if mem['Size'] == 'No Module Installed':
                continue
            i, unit = mem['Size'].split()
            cnt += 1
            total += int(i)
        dmi['mem'] = '%d memory stick(s), %d %s in total, Max %s' % (
            cnt,
            total,
            unit,
            max_mem
        )

        # chassis
        for chassis in _get(3):
            dmi['chassis'] = chassis['Type']

        return dmi

    def _get_dmi(self):
        """
        Get DMI information
        :return dict
        :rtype dict
        """

        # Requires SUDO :
        # user ALL=(ALL:ALL) NOPASSWD: /usr/sbin/dmidecode

        try:
            # TODO : Why PATH before??
            ec, so, se = ButcherTools.invoke("dmidecode")
            if ec != 0:
                # Non-zero exit code, retry sudo
                logger.info("dmidecode invoke failed, retry sudo, ec=%s, so=%s, se=%s", ec, so, se)
                ec, so, se = ButcherTools.invoke("sudo dmidecode")
                if ec != 0:
                    logger.warn("dmidecode invoke failed, give up, ec=%s, so=%s, se=%s", ec, so, se)
                    return dict()

            if so.find("sorry") >= 0:
                return dict()

            # Ok, parse
            logger.debug("so=%s", so)

            o = self._parse_dmi(so)
            logger.info("o=%s", o)

            o2 = self._filter_dmi(o)
            logger.info("o2=%s", o2)
            return o2

        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            return dict()

            # output = ''
            # try:
            #     output = subprocess.check_output(
            #         'PATH=$PATH:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin '
            #         'sudo dmidecode', shell=True)
            # except subprocess.CalledProcessError as e:
            #     logger.debug(SolBase.extostr(e))
            #
            # if len(output) < 100:
            #     return dict()
            # output = self._parse_dmi(output)
            #
            # return self._filter_dmi(output)
