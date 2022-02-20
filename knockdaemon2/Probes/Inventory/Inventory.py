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

# Thanks to Michael Brown
# https://www.openhub.net/p/python-dmidecode
"""
import logging
import os

import distro
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

    def _execute_linux(self):
        """
        Exec
        """

        # dmidecode
        dmi_buffer = self.get_dmi_buffer()

        # dmesg
        if len(dmi_buffer) == 0:
            dmesg_buffer = self.get_dmesg_buffer()
        else:
            dmesg_buffer = ""

        # Go
        self.process_from_data(dmi_buffer, dmesg_buffer)

    def process_from_data(self, dmi_buffer, dmesg_buffer):
        """
        Process from data
        :param dmi_buffer: str
        :type dmi_buffer: str
        :param dmesg_buffer: str
        :type dmesg_buffer: str
        """

        (sysname, nodename, kernel, version, machine) = os.uname()
        distribution = distro.id()
        dversion = distro.version()
        self.notify_value_n("k.inventory.os", None, "%s %s %s" % (sysname, distribution, dversion))
        self.notify_value_n("k.inventory.kernel", None, kernel)
        self.notify_value_n("k.inventory.name", None, nodename)

        # Parse dmi_buffer
        d_dmi = self.get_dmi_dict(dmi_buffer)
        if len(d_dmi) > 0:
            # From dmi
            for k, v in d_dmi.items():
                self.notify_value_n("k.inventory." + k, None, v)
        else:
            # From dmesg
            if dmesg_buffer.find('Booting paravirtualized kernel on Xen'):
                self.notify_value_n("k.inventory.chassis", None, "Virtual Server XEN")

    def dmi_parse(self, dmi_buffer):
        """
        Parse the whole dmidecode output.
        Returns a list of tuples of (type int, value dict).
        :param dmi_buffer: str
        :type dmi_buffer: str
        :return list
        :rtype list

        """
        ar_out = []
        idx = 0
        ar = dmi_buffer.strip().splitlines()
        for line in ar:
            if line.startswith('Handle 0x'):
                typ = int(line.split(',', 2)[1].strip()[len('DMI type'):])
                if typ in DMI_TYPE:
                    ar_out.append((typ, self.dmi_parse_handle_section(ar[idx:])))
            idx += 1
        return ar_out

    @classmethod
    def dmi_parse_handle_section(cls, lines):
        """
        Parse a section of dmidecode output

        * 1st line contains address, type and size
        * 2nd line is title
        * line started with one tab is one option and its value
        * line started with two tabs is a member of list

        :param lines: list
        :type lines: list
        :return : dict
        :rtype dict
        """
        data = {
            '_title': lines[1].rstrip(),
        }
        k = 0
        for line in lines[2:]:
            line = line.rstrip()
            # We replace tabs by spaces in the IDE
            if line.startswith('\t\t') or line.startswith("                "):
                if isinstance(data[k], list):
                    data[k].append(line.lstrip())
            elif line.startswith('\t') or line.startswith("        "):
                k, v = [i.strip() for i in line.lstrip().split(':', 1)]
                if v:
                    data[k] = v
                else:
                    data[k] = []
            else:
                break

        return data

    @classmethod
    def dmi_filter(cls, ar_dmi):
        """
        Filter dmi
        :param ar_dmi: list
        :type ar_dmi: list
        :return: dict
        :rtype: dict
        """

        def _get(ix):
            return [v for j, v in ar_dmi if j == ix]

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

    @classmethod
    def get_dmesg_buffer(cls):
        """
        Get dmsg buffer
        :return: str
        :rtype str
        """
        try:
            ec, so, se = ButcherTools.invoke("dmesg")
            if ec != 0:
                # Non-zero exit code
                logger.warning("dmesg invoke failed, ec=%s, so=%s, se=%s", ec, so, se)
                return ""
            else:
                return ec
        except Exception as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
            return ""

    @classmethod
    def get_dmi_buffer(cls):
        """
        Get dmi buffer
        :return: str (return "" if failed)
        :rtype str
        """

        ec, so, se = ButcherTools.invoke("dmidecode")
        if ec != 0:
            # Non-zero exit code, retry sudo
            logger.debug("dmidecode invoke failed, retry sudo, ec=%s, so=%s, se=%s", ec, so, se)
            ec, so, se = ButcherTools.invoke("sudo dmidecode")
            if ec != 0:
                logger.warning("dmidecode invoke failed, give up, ec=%s, so=%s, se=%s", ec, so, se)
                return ""
            else:
                return so
        else:
            return so

    def get_dmi_dict(self, dmi_buffer):
        """
        Get dmi dict from buffer
        :param dmi_buffer: str
        :type dmi_buffer: str
        :return dict
        :rtype dict
        """

        try:
            if dmi_buffer.find("sorry") >= 0:
                return dict()
            ar = self.dmi_parse(dmi_buffer)
            o2 = self.dmi_filter(ar)
            return o2
        except Exception as e:
            logger.warning("Ex=%s", SolBase.extostr(e))
            return dict()
