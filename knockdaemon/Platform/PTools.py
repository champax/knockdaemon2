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
import logging
import platform
import tempfile

from pythonsol.SolBase import SolBase

logger = logging.getLogger(__name__)


class PTools(object):
    """
    Platform tools
    """

    @classmethod
    def is_os_64(cls):
        """
        Return true is platform is 64 bits
        :return bool
        :rtype bool
        """

        try:
            return platform.machine().find('64') >= 0
        except Exception as e:
            # Not normal, but fallback 64 bits
            logger.warn("Ex=%s", SolBase.extostr(e))
            return True

    @classmethod
    def is_cpu_arm(cls):
        """
        Return true is cpu is an arm (32 or 64 bits)
        :return bool
        :rtype bool
        """

        try:
            if platform.machine().lower().startswith("arm") or platform.machine().lower().startswith("aarch"):
                return True
            else:
                return False
        except Exception as e:
            # Not normal, but fallback x86
            logger.warn("Ex=%s", SolBase.extostr(e))
            return False

    @classmethod
    def get_distribution_type(cls):
        """
        Debian      : return debian
        Ubuntu      : return debian
        Centos      : return redhat
        Redhat      : return redhat
        Raspbian    : return debian
        Windows     : return windows
        Unknown     : return debian + warn log

        *** Ubuntu 15
        platform.linux_distribution(full_distribution_name=False)
        ('Ubuntu', '15.10', 'wily')
        platform.dist()
        ('Ubuntu', '15.10', 'wily')

        *** Debian 8
        platform.linux_distribution(full_distribution_name=False)
        ('Debian', '8', '')
        platform.dist()
        ('Debian', '8', '')

        *** Centos 7
        platform.linux_distribution(full_distribution_name=False)
        ('centos', '7.3.1611', 'Core')
        platform.dist()
        ('centos', '7.3.1611', 'Core')

        *** Raspbian 8
        platform.linux_distribution(full_distribution_name=False)
        ('Debian', '8', '')
        platform.dist()
        ('Debian', '8', '')

        *** Usefull : https://github.com/hpcugent/easybuild/wiki/OS_flavor_name_version

        :return: str
        :rtype str
        """

        # Detected
        detected_dist = None

        # Get
        cur_dist = platform.dist()
        cur_linux_distribution = platform.linux_distribution(full_distribution_name=False)

        # Try dist
        if not detected_dist:
            try:
                detected_dist = cur_dist[0]
                detected_dist = detected_dist.strip()
                if len(detected_dist) == 0:
                    # Reset
                    detected_dist = None
            except Exception as e:
                logger.debug("Ex=%s", SolBase.extostr(e))

        # Try linux_distribution if required
        if not detected_dist:
            try:
                detected_dist = cur_linux_distribution[0]
                detected_dist = detected_dist.strip()
                if len(detected_dist) == 0:
                    # Reset
                    detected_dist = None
            except Exception as e:
                logger.debug("Ex=%s", SolBase.extostr(e))

        # This is a fallback windows
        if not detected_dist:
            # Windows HACK
            detected_dist = platform.system()

        # Ok
        return cls._get_distribution_type(detected_dist, cur_dist, cur_linux_distribution)

    @classmethod
    def _get_distribution_type(cls, detected_dist, cur_dist, cur_linux_distribution):
        """
        Internal method
        :param detected_dist: str,None
        :type detected_dist: str,None
        :param cur_dist: list,tuple, for log only
        :type cur_dist: list,tuple
        :param cur_linux_distribution: list,tuple, for log only
        :type cur_linux_distribution: list,tuple
        :return str
        :rtype str
        """

        # Check
        if not detected_dist:
            logger.warn("Unable to detect distribution, fallback debian, got detected_dist=%s, cur_dist=%s, cur_linux_distribution=%s", detected_dist, cur_dist, cur_linux_distribution)
            return "debian"

        # Lower
        detected_dist = detected_dist.lower()

        # Check
        if detected_dist == "debian":
            return "debian"
        elif detected_dist == "ubuntu":
            return "debian"
        elif detected_dist == "centos":
            return "redhat"
        elif detected_dist == "scientific linux":
            return "redhat"

        # Here some hacks (zzz)
        elif detected_dist.find("redhat") >= 0:
            return "redhat"
        elif detected_dist.find("red hat") >= 0:
            return "redhat"
        elif detected_dist.find("centos") >= 0:
            return "redhat"
        elif detected_dist.find("rehl") >= 0:
            return "redhat"

        # Windows
        elif detected_dist.find("windows") >= 0:
            return "windows"

        # Fallback
        logger.warn("Unknown distribution, fallback debian, got detected_dist=%s, cur_dist=%s, cur_linux_distribution=%s", detected_dist, cur_dist, cur_linux_distribution)
        return "debian"

    @classmethod
    def get_tmp_dir(cls):
        """
        Get tmp dir
        """
        if cls.get_distribution_type() == "windows":
            return tempfile.gettempdir()
        else:
            return "/tmp"
