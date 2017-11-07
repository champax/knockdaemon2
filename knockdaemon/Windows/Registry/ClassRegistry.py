"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2014/2015/2016 Laurent Champagnac / Laurent Labatut
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
from pythonsol.SolBase import SolBase
from threading import Lock

# ===============================================================================
# pyinstaller requires all dynamic loaded classes to be explicitly declared.
# ===============================================================================

# ===============================================================================
# PROBES
# ===============================================================================

from knockdaemon.Probes.Apache.ApacheStat import ApacheStat
from knockdaemon.Probes.Inventory.Inventory import Inventory
from knockdaemon.Probes.MemCached.MemCachedStat import MemCachedStat
from knockdaemon.Probes.Mongodb.MongoDbStat import MongoDbStat
from knockdaemon.Probes.Mysql.Mysql import Mysql
from knockdaemon.Probes.Nginx.NGinxStat import NginxStat
from knockdaemon.Probes.Os.CheckDns import CheckDns
from knockdaemon.Probes.Os.CheckProcess import CheckProcess
from knockdaemon.Probes.Os.DiskSpace import DiskSpace
from knockdaemon.Probes.Os.HddStatus import HddStatus
from knockdaemon.Probes.Os.IpmiLog import IpmiLog
from knockdaemon.Probes.Os.IpvsAdm import IpvsAdm
from knockdaemon.Probes.Os.Load import Load
from knockdaemon.Probes.Os.Memory import Memory
from knockdaemon.Probes.Os.NetStat import Netstat
from knockdaemon.Probes.Os.Network import Network
from knockdaemon.Probes.Os.ProcNum import NumberOfProcesses
from knockdaemon.Probes.Os.TimeDiff import TimeDiff
from knockdaemon.Probes.Os.UpTime import Uptime
from knockdaemon.Probes.PhpFpm.PhpFpmStat import PhpFpmStat
from knockdaemon.Probes.Redis.RedisStat import RedisStat
from knockdaemon.Probes.Uwsgi.UwsgiStat import UwsgiStat
from knockdaemon.Probes.Varnish.VarnishStat import VarnishStat

# ===============================================================================
# TRANSPORT
# ===============================================================================

from knockdaemon.Transport.HttpAsyncTransport import HttpAsyncTransport

# ===============================================================================
# SOME CODE USING THEM
# ===============================================================================
from knockdaemon.Transport.InfluxAsyncTransport import InfluxAsyncTransport

SolBase.voodoo_init()
logger = logging.getLogger(__name__)


class ClassRegistry(object):
    """
    Register all classes for pyinstaller
    """
    _reg_initialized = False
    _reg_lock = Lock()
    _reg_dict = dict()

    @classmethod
    def _register(cls, c):
        """
        Register
        :param c: object 
        :type c: object
        """
        cls._reg_dict[c] = True
        logger.info("Registered class=%s", c)

    @classmethod
    def register_all_classes(cls):
        """
        Register all
        """

        # Check
        if cls._reg_initialized:
            return

        # Lock
        with cls._reg_lock:
            # Re-check
            if cls._reg_initialized:
                return

            # Go
            logger.info("Initializing classes")

            # PROBES
            cls._register(ApacheStat)
            cls._register(Inventory)
            cls._register(MemCachedStat)
            cls._register(MongoDbStat)
            cls._register(Mysql)
            cls._register(NginxStat)
            cls._register(CheckDns)
            cls._register(CheckProcess)
            cls._register(DiskSpace)
            cls._register(HddStatus)
            cls._register(IpmiLog)
            cls._register(IpvsAdm)
            cls._register(Load)
            cls._register(Memory)
            cls._register(Netstat)
            cls._register(Network)
            cls._register(NumberOfProcesses)
            cls._register(TimeDiff)
            cls._register(Uptime)
            cls._register(PhpFpmStat)
            cls._register(RedisStat)
            cls._register(UwsgiStat)
            cls._register(VarnishStat)

            # TRANSPORT
            cls._register(HttpAsyncTransport)
            cls._register(InfluxAsyncTransport)

            # DONE
            cls._reg_initialized = True
