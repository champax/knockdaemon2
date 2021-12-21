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
import logging
import re

import gevent

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    pass

logger = logging.getLogger(__name__)


class HddStatus(KnockProbe):
    """
    Hdd status
    """

    def __init__(self):
        """
        Init
        """
        # Base
        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        # override timeout since we are slow
        self.exec_timeout_override_ms = 30000

        self.helpers = KnockHelpers()
        self.all_hash = dict()
        self.category = "/os/disk"

    def add_to_all_hash(self, key, value):
        """
        Add to all hash
        :param key: Key
        :type key: str
        :param value: Value
        :type value: int, str
        """
        if key not in self.all_hash:
            self.all_hash[key] = value
        else:
            self.all_hash[key] = self.all_hash[key] + value

    def _execute_linux(self):
        """
        Update
        """

        # Requires SUDO :
        # user ALL=(ALL:ALL) NOPASSWD: /usr/sbin/smartctl

        # Init all hash
        self.init_all_hash()

        # Scan all in parallel
        ar_greenlet = list()
        for hd in self.scan_all_hdd():
            ar_greenlet.append(gevent.spawn(self.scan_one_hdd, hd))
        gevent.joinall(ar_greenlet, timeout=6)

        # Push all hash
        self.push_all_hash()

    def push_all_hash(self):
        """
        Push all hash
        """
        for key, value in self.all_hash.items():
            self.notify_value_n(key, {"HDD": "ALL"}, value)

    def init_all_hash(self):
        """
        Init all hash
        """
        # All hash
        self.all_hash = dict()

        # Default init
        self.add_to_all_hash("k.hard.hd.reallocated_sector_ct", 0)

    def scan_all_hdd(self):
        """
        Use smartctl to find all hardware disk
        :return: list of hdd
        :rtype: list
        """
        cmd = self.helpers.sudoize('smartctl --scan-open')
        _, so, _ = ButcherTools.invoke(cmd)
        return self.scan_all_hdd_buffer(so)

    @classmethod
    def scan_all_hdd_buffer(cls, buf):
        """
        Scan all hdd buffer
        :param buf: str
        :type buf: str
        :return: list of str (device names, ["/dev/sda"]
        :rtype list
        """
        for line in buf.split('\n'):
            # sample:
            # /dev/sda -d sat # /dev/sda [SAT], ATA device

            if line.startswith('#'):
                # scan_smart_devices: glob(3) aborted matching pattern /dev/discs/disc*
                continue
            if not ('failed:' in line or line == ''):
                name = line.split(' ')[0]
                yield name

    def process_smartctl_error_only_buffer(self, hdd, buf):
        """
        Process smartctl error only buffer
        :param hdd: str
        :type hdd: str
        :param buf: str
        :type buf: str
        """

        out_text = buf.strip()
        if len(out_text) == 0:
            out_text = "KNOCKOK"
        self.notify_value_n("k.hard.hd.health", {"HDD": hdd}, out_text)

    def process_smartctl_full_buffer(self, hdd, buf):
        """
        Process smartctl full buffer
        :param hdd: str
        :type hdd: str
        :param buf: str
        :type buf: str
        """

        self.notify_value_n("k.hard.hd.status", {"HDD": hdd}, buf)

        # Parse it
        for line in buf.split("\n"):
            if re.search(" 5 Reallocated_Sector_Ct", line):
                try:
                    int_value = int(line.split()[9])
                except ValueError:
                    int_value = 0
                self.notify_value_n("k.hard.hd.reallocated_sector_ct", {"HDD": hdd}, int_value)
                self.add_to_all_hash('k.hard.hd.reallocated_sector_ct', int_value)
            elif re.search("241 Total_LBAs_Written", line):
                try:
                    int_value = int(line.split()[9])
                except ValueError:
                    int_value = 0
                self.notify_value_n("k.hard.hd.total_lbas_written", {"HDD": hdd}, int_value)
            elif re.search("Device Model: ", line):
                value = line.split(None, 2)[2].strip()
                self.notify_value_n("k.hard.hd.device_model", {"HDD": hdd}, value)
            elif re.search("Serial Number: ", line):
                value = line.split(None, 2)[2].strip()
                self.notify_value_n("k.hard.hd.serial_number", {"HDD": hdd}, value)
            elif re.search("User Capacity: ", line):
                # User Capacity:    512,110,190,592 bytes [512 GB]
                # User Capacity:    500 107 862 016 bytes [500 GB]
                try:
                    i1 = line.find(":")
                    i2 = line.find(" bytes")
                    v = line[i1 + 1:i2]
                    v = v.replace(" ", "").replace(",", "")
                    v = float(v)
                except ValueError:
                    v = 0.0
                self.notify_value_n("k.hard.hd.user_capacity", {"HDD": hdd}, v)

    def scan_one_hdd(self, hd):
        """
        Gevent spammed
        :param hd: 
        :return: 
        """

        # Clean
        c_hd = hd.replace('/dev/', '')

        # We do not use "-l selftest"", this may exit with code 4 with "Device does not support Self Test logging"
        cmd = self.helpers.sudoize("smartctl -q errorsonly -H %s" % hd)
        logger.info("going invoke, cmd=%s", cmd)
        ec, so, se = ButcherTools.invoke(cmd)
        if ec != 0:
            logger.warning("invoke failed, give up,  ec=%s, so=%s, se=%s", ec, so, se)
            return
        logger.debug("invoke ok, ec=%s, so=%s, se=%s", ec, so, se)

        # Process it
        self.process_smartctl_error_only_buffer(c_hd, so)

        # Check again - this may output exit code 4, so we dont check it
        cmd = self.helpers.sudoize("smartctl -a %s" % hd)
        logger.info("going invoke, cmd=%s", cmd)
        ec, so, se = ButcherTools.invoke(cmd)
        logger.info("invoke ok, ec=%s, so=%s, se=%s", ec, so, se)

        # Process it
        self.process_smartctl_full_buffer(c_hd, so)
