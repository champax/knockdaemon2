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

import gevent
import re
from pysolbase.SolBase import SolBase

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Core.KnockProbe import KnockProbe
from knockdaemon2.Platform.PTools import PTools

if PTools.get_distribution_type() == "windows":
    from knockdaemon2.Windows.Wmi.Wmi import Wmi

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
        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        # override timeout since we are slow
        self.exec_timeout_override_ms = 30000

        self.helpers = KnockHelpers()
        self.helpers.sudoize('smartctl --version')
        self.liste = list()
        self.all_hash = dict()

        self.category = "/os/disk"

    @staticmethod
    def add_to_hash(h, key, value):
        """
        Add to hash
        :param h: Hash
        :type h: dict
        :param key: Key
        :type key: str
        :param value: Value
        :type value: int, str
        """
        if key not in h:
            h[key] = value
        else:
            h[key] = h[key] + value

    def _execute_linux(self):
        """
        Update
        """

        # Requires SUDO :
        # user ALL=(ALL:ALL) NOPASSWD: /usr/sbin/smartctl
        logger.info('Entering')
        hds = self.scan_hdd()

        logger.info("hds=%s", hds)

        self.liste = list()

        # Add ALL
        self.notify_discovery_n("k.hard.hd.discovery", {"HDD": "ALL"})

        # All hash
        self.all_hash = dict()

        # Default init
        self.add_to_hash(self.all_hash, "k.hard.hd.reallocated_sector_ct", 0)
        self.add_to_hash(self.all_hash, "k.hard.hd.total_lbas_written", 0)
        self.add_to_hash(self.all_hash, "k.hard.hd.model_family", "ALL")
        self.add_to_hash(self.all_hash, "k.hard.hd.device_model", "ALL")
        self.add_to_hash(self.all_hash, "k.hard.hd.serial_number", "ALL")
        self.add_to_hash(self.all_hash, "k.hard.hd.status", "OK")
        self.add_to_hash(self.all_hash, "k.hard.hd.health", "KNOCKOK")
        self.add_to_hash(self.all_hash, "k.hard.hd.user_capacity", "ALL")

        ar_greenlet = list()
        for hd in hds:
            ar_greenlet.append(gevent.spawn(self.one_hd, hd))
        gevent.joinall(ar_greenlet, timeout=6)

        # -----------------------------
        # Handle "ALL" keys
        # -----------------------------
        for key, value in self.all_hash.iteritems():
            self.notify_value_n(key, {"HDD": "ALL"}, value)

    def scan_hdd(self):
        """
        Use smartctl to find all hardware disk
        :return: list of hdd
         :rtype: list
        """
        cmd = self.helpers.sudoize('smartctl --scan-open')
        ec, so, se = ButcherTools.invoke(cmd)

        for line in so.split('\n'):
            # sample:
            # /dev/sda -d sat # /dev/sda [SAT], ATA device

            if line.startswith('#'):
                # scan_smart_devices: glob(3) aborted matching pattern /dev/discs/disc*
                continue
            if not ('failed:' in line or line == ''):
                name = line.split(' ')[0]
                yield name

    def one_hd(self, hd):
        """
        Gevent spammed
        :param hd: 
        :return: 
        """

        # Clean
        c_hd = hd.replace('/dev/', '')

        # Disco
        self.notify_discovery_n("k.hard.hd.discovery", {"HDD": c_hd})

        # out = os.popen("/usr/sbin/smartctl -q errorsonly -H -l selftest " + hd)
        cmd = self.helpers.sudoize("smartctl -q errorsonly -H -l selftest " + hd)
        logger.info("going invoke, cmd=%s", cmd)
        ec, so, se = ButcherTools.invoke(cmd)
        if ec != 0:
            logger.warn("invoke failed, give up,  ec=%s, so=%s, se=%s", ec, so, se)
            return

        logger.debug("invoke ok, ec=%s, so=%s, se=%s", ec, so, se)

        out_text = so.strip()
        if len(out_text) == 0:
            out_text = "KNOCKOK"

        self.notify_value_n("k.hard.hd.health", {"HDD": c_hd}, out_text)

        # out = os.popen("/usr/sbin/smartctl -a " + hd)
        cmd = self.helpers.sudoize("smartctl -a " + hd)
        logger.info("going invoke, cmd=%s", cmd)
        ec, so, se = ButcherTools.invoke(cmd)
        if ec != 0:
            logger.warn("invoke failed, give up, ec=%s, so=%s, se=%s", ec, so, se)
            return

        logger.info("invoke ok, ec=%s, so=%s, se=%s", ec, so, se)

        out_text = so

        self.notify_value_n("k.hard.hd.status", {"HDD": c_hd}, "".join(out_text))

        for line in out_text:
            # noinspection RepeatedSpace
            if re.search("  5 Reallocated_Sector_Ct", line):
                value = line.split()[9]

                self.notify_value_n("k.hard.hd.reallocated_sector_ct", {"HDD": c_hd}, value)

                # ----------------------
                # ALL : cast to int
                # ----------------------
                try:
                    int_value = int(value)
                    self.add_to_hash(self.all_hash, 'k.hard.hd.reallocated_sector_ct', int_value)
                except Exception as e:
                    logger.warn("Unable to process reallocated_sector_ct[ALL], value=%s, ex=%s", value, e)
            elif re.search("241 Total_LBAs_Written", line):
                value = line.split()[9]
                self.notify_value_n("k.hard.hd.total_lbas_written", {"HDD": c_hd}, value)
            elif re.search("Model Family: ", line):
                value = line.split(None, 2)[2].strip()
                self.notify_value_n("k.hard.hd.model_family", {"HDD": c_hd}, value)
            elif re.search("Device Model:     ", line):
                value = line.split(None, 2)[2].strip()
                self.notify_value_n("k.hard.hd.device_model", {"HDD": c_hd}, value)
            elif re.search("Serial Number:    ", line):
                value = line.split(None, 2)[2].strip()
                self.notify_value_n("k.hard.hd.serial_number", {"HDD": c_hd}, value)
            elif re.search("User Capacity:    ", line):
                value = line.split(None, 5)[2].strip().replace(',', '')
                self.notify_value_n("k.hard.hd.user_capacity", {"HDD": c_hd}, value)

    def _execute_windows(self):
        """
        Windows
        """

        try:
            # Wmi
            d, age_ms = Wmi.wmi_get_dict()
            logger.info("Using wmi with age_ms=%s", age_ms)

            # "k.hard.hd.status[ALL]" = "OK"
            # "k.hard.hd.user_capacity[ALL]" = "ALL"
            # "k.hard.hd.reallocated_sector_ct[ALL]" = 0
            # "k.hard.hd.serial_number[ALL]" = "ALL"
            # "k.hard.hd.model_family[ALL]" = "ALL"
            # "k.hard.hd.total_lbas_written[ALL] =  0
            # "k.hard.hd.health[ALL]" = "KNOCKOK"
            # "k.hard.hd.device_model[ALL]" = "ALL"

            # Smart : MSStorageDriver_Failure* WMI classes are all empty on all computers tested
            # We HACK the stuff based on Win32_DiskDrive status
            failed_count = 0
            for d_diskdrive in d["Win32_DiskDrive"]:
                # Device ID
                s_disk_deviceid = d_diskdrive["DeviceID"]
                s_status = d_diskdrive["Status"]
                logger.info("Processing disk=%s, status=%s", s_disk_deviceid, s_status)

                if s_status.lower() == "ok":
                    # OK
                    pass
                else:
                    # NOK
                    logger.info("Got a failure")
                    failed_count += 1

            # If we have one failure, signal it
            if failed_count > 0:
                logger.info("Notifying failure (failed_count=%s)", failed_count)
                self.notify_value_n("k.hard.hd.status", {"HDD": "ALL"}, "FAILED_WIN")
                self.notify_value_n("k.hard.hd.user_capacity", {"HDD": "ALL"}, "ALL")
                self.notify_value_n("k.hard.hd.reallocated_sector_ct", {"HDD": "ALL"}, failed_count)
                self.notify_value_n("k.hard.hd.serial_number", {"HDD": "ALL"}, "ALL")
                self.notify_value_n("k.hard.hd.model_family", {"HDD": "ALL"}, "ALL")
                self.notify_value_n("k.hard.hd.total_lbas_written", {"HDD": "ALL"}, failed_count)
                self.notify_value_n("k.hard.hd.health", {"HDD": "ALL"}, "KNOCK_FAILED_WIN")
                self.notify_value_n("k.hard.hd.device_model", {"HDD": "ALL"}, "ALL")
            else:
                logger.info("Notifying success")
                self.notify_value_n("k.hard.hd.status", {"HDD": "ALL"}, "OK")
                self.notify_value_n("k.hard.hd.user_capacity", {"HDD": "ALL"}, "ALL")
                self.notify_value_n("k.hard.hd.reallocated_sector_ct", {"HDD": "ALL"}, failed_count)
                self.notify_value_n("k.hard.hd.serial_number", {"HDD": "ALL"}, "ALL")
                self.notify_value_n("k.hard.hd.model_family", {"HDD": "ALL"}, "ALL")
                self.notify_value_n("k.hard.hd.total_lbas_written", {"HDD": "ALL"}, failed_count)
                self.notify_value_n("k.hard.hd.health", {"HDD": "ALL"}, "KNOCKOK")
                self.notify_value_n("k.hard.hd.device_model", {"HDD": "ALL"}, "ALL")

            # -----------------
            # DISCO
            # -----------------
            self.notify_discovery_n("k.hard.hd.discovery", {"HDD": "ALL"})

        except Exception as e:
            logger.info("Ex=%s", SolBase.extostr(e))
