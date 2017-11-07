"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2014 Laurent Champagnac
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
from greenlet import GreenletExit
from threading import Lock, RLock

import gevent
# noinspection PyUnresolvedReferences,PyPackageRequirements
import pythoncom
# noinspection PyUnresolvedReferences,PyPackageRequirements
import wmi
from pythonsol.SolBase import SolBase

logger = logging.getLogger(__name__)


# noinspection SqlDialectInspection
class Wmi(object):
    """
    WMI Access helpers
    List of WMI Classes : http://www.activexperts.com/admin/scripts/wmi/powershell/
    MS : https://msdn.microsoft.com/en-us/library/aa394388(v=vs.85).aspx
    """

    # ============================================
    # Dict Instance_Name => list of counters to fetch (all if empty)
    # Can be populated on demand
    # ============================================
    # noinspection SqlNoDataSourceInspection
    _WMI_INSTANCES = {
        # ---------------------
        # CLASSES
        # ---------------------
        # https://msdn.microsoft.com/en-us/library/aa394134(v=vs.85).aspx
        "Win32_DiskDriveToDiskPartition": {
            "type": "list",
            "fields": ["Antecedent", "Dependent", "DeviceID", "BlockSize"],
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394175(v=vs.85).aspx
        "Win32_LogicalDiskToPartition": {
            "type": "list",
            "fields": ["Antecedent", "Dependent", "DeviceID"],
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },

        # ---------------------
        # WQL
        # ---------------------
        # https://msdn.microsoft.com/en-us/library/aa394173(v=vs.85).aspx
        "Win32_LogicalDisk": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["DeviceID", "Size", "FileSystem"]) +
                         " FROM Win32_LogicalDisk",
            "read": "list",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },

        # https://msdn.microsoft.com/en-us/library/aa394132(v=vs.85).aspx
        "Win32_DiskDrive": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["DeviceID", "Status"]) +
                         " FROM Win32_DiskDrive",
            "read": "list",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394246(v=vs.85).aspx
        "Win32_PageFileUsage": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["AllocatedBaseSize", "CurrentUsage"]) +
                         " FROM Win32_PageFileUsage",
            "read": "list",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # No doc on windows.com
        # http://wutils.com/wmi/root/cimv2/win32_perfrawdata_tcpip_networkadapter/
        "Win32_PerfRawData_Tcpip_NetworkInterface": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["BytesReceivedPersec", "BytesSentPersec", "PacketsReceivedPersec", "PacketsSentPersec", "PacketsReceivedErrors", "PacketsReceivedUnknown", "PacketsOutboundErrors", "Timestamp_Sys100NS"]) +
                         " FROM Win32_PerfRawData_Tcpip_NetworkInterface",
            "read": "list",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394272(v=vs.85).aspx
        "Win32_PerfFormattedData_PerfOS_System": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["ProcessorQueueLength", "SystemUpTime"]) +
                         " FROM Win32_PerfFormattedData_PerfOS_System",
            "read": "direct",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394246(v=vs.85).aspx
        "Win32_PerfFormattedData_PerfOS_Memory": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["AvailableBytes", "FreeAndZeroPageListBytes", "ModifiedPageListBytes"]) +
                         " FROM Win32_PerfFormattedData_PerfOS_Memory",
            "read": "direct",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394308%28v=vs.85%29.aspx
        "Win32_PerfRawData_PerfDisk_LogicalDisk": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["DiskReadBytesPersec", "DiskReadsPersec", "DiskWriteBytesPersec", "DiskWritesPersec", "Timestamp_Sys100NS"]) +
                         " FROM Win32_PerfRawData_PerfDisk_LogicalDisk" +
                         " WHERE Name != '_Total'",
            "read": "list",
            "min_client": "Windows XP",
            "min_server": "Windows Server 2003",
        },
        # https://msdn.microsoft.com/en-us/microsoft-r/aa394261
        "Win32_PerfFormattedData_PerfDisk_LogicalDisk": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["CurrentDiskQueueLength", "PercentDiskTime", "FreeMegabytes"]) +
                         " FROM Win32_PerfFormattedData_PerfDisk_LogicalDisk" +
                         " WHERE Name != '_Total'",
            "read": "list",
            "min_client": "Windows XP",
            "min_server": "Windows Server 2003",
        },
        # https://msdn.microsoft.com/en-us/library/windows/desktop/aa394239(v=vs.85).aspx
        "Win32_OperatingSystem": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["LastBootUpTime", "TotalVisibleMemorySize"]) +
                         " FROM Win32_OperatingSystem",
            "read": "direct",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394216(v=vs.85).aspx
        "Win32_NetworkAdapter": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["NetConnectionID", "Name", "NetConnectionStatus", "NetEnabled", "PhysicalAdapter", "Speed", "Installed", "Availability", "DeviceID", "Description", "MACAddress", "AdapterType", ]) +
                         " FROM Win32_NetworkAdapter" +
                         " WHERE NetEnabled=1",
            "read": "list",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394318(v=vs.90).aspx
        "Win32_PerfRawData_PerfOS_System": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["ContextSwitchesPersec", "Timestamp_Sys100NS"]) +
                         " FROM Win32_PerfRawData_PerfOS_System",
            "read": "direct",
            "min_client": "Windows XP",
            "min_server": "Windows Server 2003",
        },
        # # https://technet.microsoft.com/en-us/sysinternals/aa394317(v=vs.60)
        "Win32_PerfRawData_PerfOS_Processor": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["PercentDPCTime", "PercentPrivilegedTime", "PercentIdleTime", "PercentUserTime", "PercentInterruptTime", "InterruptsPersec", "PercentProcessorTime", "Timestamp_Sys100NS"]) +
                         " FROM Win32_PerfRawData_PerfOS_Processor WHERE Name='_Total'",
            "read": "list",
            "min_client": "Windows XP",
            "min_server": "Windows Server 2003",
        },
        # https://msdn.microsoft.com/en-us/library/aa394104(v=vs.85).aspx
        "Win32_Processor": {
            "type": "wql",
            "statement": "SELECT " +
                         ", ".join(["NumberOfCores", "Name"]) +
                         " FROM Win32_Processor",
            "read": "list",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394494(v=vs.85).aspx
        "WQL_RunningThreadCount": {
            "type": "wql",
            "statement": "SELECT ThreadState FROM Win32_Thread WHERE ThreadState=2",
            "read": "count",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # https://msdn.microsoft.com/en-us/library/aa394494(v=vs.85).aspx
        # This is MASSIVELY SLOW, disabled for now :(
        # "WQL_RunningThreadTotalCount": {
        #     "type": "wql",
        #     "statement": "SELECT Name FROM Win32_Thread",
        #     "read": "count",
        #     "min_client": "Windows Vista",
        #     "min_server": "Windows Server 2008",
        # },
        # https://msdn.microsoft.com/en-us/library/aa394189(v=vs.85).aspx
        "WQL_ConnectedUsers": {
            "type": "wql",
            "statement": "SELECT LogonType FROM Win32_LogonSession WHERE LogonType=10",
            "read": "count",
            "min_client": "Windows Vista",
            "min_server": "Windows Server 2008",
        },
        # Will have dynamic process based on JSON config (Win32_Process)
        # https://msdn.microsoft.com/en-us/library/aa394372(v=vs.85).aspx

    }

    # Wmi current dict and last refresh ms, props and lock
    _WMI_DICT = None
    _WMI_DICT_LAST_REFRESH_MS = None
    _WMI_DICT_PROPS = dict()
    _WMI_DICT_LOCK = RLock()

    # Wmi started flag
    _WMI_IS_STARTED = False

    # Wmi lock
    _WMI_LOCK = Lock()

    # Wmi refresh greenlet
    _WMI_GREENLET = None

    # Wmi refresh interval (assuming probes run every 60 sec, put a refresh at 20 sec
    _WMI_GREENLET_INTERVAL_MS = 20000

    # UNITTEST CALLBACK
    _WMI_UNITTEST_CB = None

    # =====================================
    # START / STOP / REFRESH
    # =====================================

    @classmethod
    def wmi_start(cls):
        """
        Start the cache
        """

        logger.info("Entering")

        with cls._WMI_LOCK:
            try:
                # Check
                if cls._WMI_IS_STARTED:
                    logger.warning("_WMI_IS_STARTED=True, doing nothing")
                    return

                # Log
                logger.info("Starting now")
                logger.info("_WMI_GREENLET_INTERVAL_MS=%s", cls._WMI_GREENLET_INTERVAL_MS)

                # Started
                cls._WMI_IS_STARTED = True

                # Initial fetch
                logger.info("Performing initial full fetch")
                cls._wmi_fetch_all()
                logger.info("Performed initial full fetch")

                # Start greenlet
                logger.info("scheduling initial greenlet")
                cls._WMI_GREENLET = gevent.spawn_later(cls._WMI_GREENLET_INTERVAL_MS * 0.001, cls._wmi_refresh_run)

                # Done
                logger.info("started")
            except Exception as e:
                logger.error("Exception, stopping, e=%s", SolBase.extostr(e))
                cls.wmi_stop()

        # Wait
        SolBase.sleep(0)

    @classmethod
    def wmi_stop(cls):
        """
        Stop the cache
        :return
        """

        with cls._WMI_LOCK:
            try:
                # Check
                if not cls._WMI_IS_STARTED:
                    logger.warn("Not started, giveup")
                    return

                # Signal
                logger.info("Stopping")
                cls._WMI_IS_STARTED = False

                # Kill greenlet
                if cls._WMI_GREENLET:
                    logger.info("Killing greenlet")
                    cls._WMI_GREENLET.kill(block=True)
                    cls._WMI_GREENLET = None
                    logger.info("Killed greenlet")
                else:
                    logger.info("No greenlet")

                # Over
                logger.info("Stopped")

            except Exception as e:
                logger.error("Exception, ex=%s", SolBase.extostr(e))
            finally:
                # Reset
                cls._WMI_IS_STARTED = False
                cls._WMI_GREENLET = None

    @classmethod
    def _reset(cls):
        """
        For unittest
        """

        with cls._WMI_DICT_LOCK:
            cls._WMI_DICT = None
            cls._WMI_DICT_LAST_REFRESH_MS = None
            cls._WMI_UNITTEST_CB = None
            cls._WMI_DICT_PROPS = dict()

    @classmethod
    def _wmi_refresh_schedule_next(cls):
        """
        Schedule next run.
        """

        try:
            # Started ?
            if not cls._WMI_IS_STARTED:
                return

            with cls._WMI_LOCK:
                # Re-check
                if not cls._WMI_IS_STARTED:
                    return

                # Yes, schedule
                cls._WMI_GREENLET = gevent.spawn_later(cls._WMI_GREENLET_INTERVAL_MS * 0.001, cls._wmi_refresh_run)

            # Wait
            SolBase.sleep(0)

        except Exception as e:
            logger.error("_schedule_next_watchdog : Exception, e=%s", SolBase.extostr(e))
        finally:
            pass

    @classmethod
    def _wmi_refresh_run(cls):
        """
        Watch dog
        :return Nothing
        """

        if not cls._WMI_IS_STARTED:
            return

        reschedule = True
        try:
            # Check
            if not cls._WMI_IS_STARTED:
                return

            # Full refresh
            cls._wmi_fetch_all()

            # Callback (unittest)
            if cls._WMI_UNITTEST_CB:
                cls._WMI_UNITTEST_CB()

        except GreenletExit:
            logger.info("GreenletExit, no reschedule")
            reschedule = False
        except Exception as e:
            logger.error("Exception, e=%s", SolBase.extostr(e))
        finally:
            if reschedule and cls._WMI_IS_STARTED:
                cls._wmi_refresh_schedule_next()

    # ================================
    # INTERNAL FUL REFRESH METHOD
    # ================================

    @classmethod
    def _wmi_fetch_one(cls, wmi_instance, wmi_class, w_dict, f_hash):
        """
        Fetch one
        :param wmi_instance: a wmi instance
        :type wmi_instance: WMI
        :param wmi_class: class name to fetch
        :type wmi_class: str
        :param w_dict: dict of what to fetch
        :type w_dict: dict
        :param f_hash: dict of fields to fetch
        :type f_hash
        :return tuple
        :rtype tuple
        """

        msq = SolBase.mscurrent()
        local_counter_dict = dict()
        local_refresh_dict = dict()

        # Get
        w_type = w_dict["type"]
        w_min_c = w_dict["min_client"]
        w_min_s = w_dict["min_server"]
        logger.info("Processing class=%s, min_client=%s, min_server=%s", wmi_class, w_min_c, w_min_s)

        if w_type in ["wql"]:
            # ------------------------
            # WQL FETCH
            # ------------------------
            statement = w_dict["statement"]
            read_mode = w_dict["read"]

            # Fire
            ms = SolBase.mscurrent()
            try:
                logger.info("WQL, statement=%s", statement)
                q = wmi_instance.query(statement)
            finally:
                logger.info("WQL, wmi_class=%s, ms=%s", wmi_class, SolBase.msdiff(ms))

            # Read
            ms = SolBase.mscurrent()
            try:
                if read_mode == "count":
                    # -------------------
                    # count : get len
                    # -------------------
                    q_count = len(q)
                    local_counter_dict[wmi_class] = q_count
                    local_refresh_dict[wmi_class] = {"refresh_at": SolBase.mscurrent(), "last_elapsed": SolBase.msdiff(msq)}
                elif read_mode == "list":
                    # -------------------
                    # list : Read all records
                    # -------------------
                    ar_local = list()
                    for cur_r in q:
                        local_dict = dict()
                        for k2 in cur_r.properties.keys():
                            SolBase.sleep(0)

                            # CHECK FIELD
                            if len(f_hash) > 0 and k2 not in f_hash:
                                # Bypass this field, not registered
                                continue

                            v2 = getattr(cur_r, k2)
                            if k2 == "GroupComponent":
                                # Group component refer to upper level in the tree, degage
                                pass
                            elif k2 in ["PartComponent", "Antecedent", "Dependent"]:
                                # Get
                                partco_key, partco_props = cls._get_part_component_to_dict(v2, f_hash)
                                # Store
                                if k2 in ["PartComponent"]:
                                    local_dict[str(partco_key)] = partco_props
                                else:
                                    # Antecedent / Dependent
                                    if k2 not in local_dict:
                                        local_dict[str(k2)] = dict()
                                    local_dict[str(k2)] = partco_props
                            else:
                                # Basic
                                local_dict[str(k2)] = v2
                        # Add
                        ar_local.append(local_dict)

                    # Push
                    local_counter_dict[wmi_class] = ar_local
                    local_refresh_dict[wmi_class] = {"refresh_at": SolBase.mscurrent(), "last_elapsed": SolBase.msdiff(msq)}
                elif read_mode == "direct":
                    # -------------------
                    # list : Read all records
                    # -------------------
                    assert len(q) == 1, "len(q)!=1, got q={0}".format(q)
                    local_dict = dict()
                    for cur_r in q:
                        for k2 in cur_r.properties.keys():
                            SolBase.sleep(0)

                            # CHECK FIELD
                            if len(f_hash) > 0 and k2 not in f_hash:
                                # Bypass this field, not registered
                                continue

                            v2 = getattr(cur_r, k2)
                            if k2 == "GroupComponent":
                                # Group component refer to upper level in the tree, degage
                                pass
                            elif k2 in ["PartComponent", "Antecedent", "Dependent"]:
                                # Get
                                partco_key, partco_props = cls._get_part_component_to_dict(v2, f_hash)
                                # Store
                                if k2 in ["PartComponent"]:
                                    local_dict[str(partco_key)] = partco_props
                                else:
                                    # Antecedent / Dependent
                                    if k2 not in local_dict:
                                        local_dict[str(k2)] = dict()
                                    local_dict[str(k2)] = partco_props
                            else:
                                # Basic
                                local_dict[str(k2)] = v2

                    # Push
                    local_counter_dict[wmi_class] = local_dict
                    local_refresh_dict[wmi_class] = {"refresh_at": SolBase.mscurrent(), "last_elapsed": SolBase.msdiff(msq)}
                else:
                    raise Exception("Invalid read=%s" % read_mode)
            finally:
                logger.info("WQL, read, ms=%s", SolBase.msdiff(ms))
        else:
            # ------------------------
            # FULL CLASS FETCH
            # ------------------------

            # Get
            w_counters = cls._get_inst_internal(wmi_instance, wmi_class)

            # Fetch all props
            cls._get_props(w_counters, w_type, msq, f_hash, local_counter_dict, local_refresh_dict)

        # OVER
        return local_counter_dict, local_refresh_dict

    @classmethod
    def _wmi_fetch_all(cls):
        """
        Wmi full refresh
        """
        ms_a = SolBase.mscurrent()
        try:
            # Dict
            counter_dict = dict()
            refresh_dict = dict()

            # Get instance
            wmi_instance = cls._get_inst()

            # ----------------
            # Browse instances
            # ----------------
            for wmi_class, w_dict in cls._WMI_INSTANCES.iteritems():
                # Sleep
                SolBase.sleep(0)

                # Hash the fields
                f_hash = dict()
                if "fields" in w_dict:
                    for field in w_dict["fields"]:
                        f_hash[field] = None

                # Fetch one instance
                local_counter_dict, local_refresh_dict = cls._wmi_fetch_one(wmi_instance, wmi_class, w_dict, f_hash)

                # Update dicts
                counter_dict.update(local_counter_dict)
                refresh_dict.update(local_refresh_dict)

            # ----------------
            # Full refreshed, store
            # But we need to handle possible more recent datas than us, so....
            # ----------------
            with cls._WMI_DICT_LOCK:
                for wmi_class in cls._WMI_INSTANCES.keys():
                    # Alloc
                    if not cls._WMI_DICT:
                        assert not cls._WMI_DICT_PROPS, "_WMI_DICT None, _WMI_DICT_PROPS"
                        cls._WMI_DICT = dict()
                        cls._WMI_DICT_PROPS = dict()

                    # ------------------
                    # If not present, just push
                    # ------------------
                    if wmi_class not in cls._WMI_DICT:
                        logger.info("FULL : Pushing initial, class=%s", wmi_class)
                        assert wmi_class not in cls._WMI_DICT_PROPS, "wmi_class not in cls._WMI_DICT but in _WMI_DICT_PROPS, wmi_class={0}".format(wmi_class)
                        cls._WMI_DICT[wmi_class] = counter_dict[wmi_class]
                        cls._WMI_DICT_PROPS[wmi_class] = refresh_dict[wmi_class]
                        continue

                    # ------------------
                    # Got some
                    # ------------------
                    age_in_dict = SolBase.msdiff(cls._WMI_DICT_PROPS[wmi_class]["refresh_at"])
                    age_us = SolBase.msdiff(refresh_dict[wmi_class]["refresh_at"])
                    if age_us < age_in_dict:
                        # ------------------
                        # Replace
                        # ------------------
                        logger.info("FULL : Pushing update, class=%s, age_us=%s, age_in_dict=%s", wmi_class, age_us, age_in_dict)
                        cls._WMI_DICT[wmi_class] = counter_dict[wmi_class]
                        cls._WMI_DICT_PROPS[wmi_class] = refresh_dict[wmi_class]
                    else:
                        # BYPASS
                        logger.info("FULL : Bypassing update, class=%s, age_us=%s, age_in_dict=%s", wmi_class, age_us, age_in_dict)

                # OK
                cls._WMI_DICT_LAST_REFRESH_MS = SolBase.mscurrent()
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
        finally:
            SolBase.sleep(0)
            logger.info("WMI, Fetched all classes, ms=%s, dict age ms=%s", SolBase.msdiff(ms_a), SolBase.msdiff(cls._WMI_DICT_LAST_REFRESH_MS))

    # ================================
    # ROOT
    # ================================

    @classmethod
    def _get_inst(cls):
        """
        Get wmi instance
        :return  WMI
        :rtype WMI
        """
        ms = SolBase.mscurrent()

        # Avoid CoInitialize exception
        try:
            logger.info("CoInitialize IN")
            pythoncom.CoInitialize()
            logger.info("CoInitialize OUT")
        except Exception as e:
            logger.warn("CoInitialize Ex=%s", SolBase.extostr(e))

        # Go
        try:
            return wmi.WMI(find_classes=False)
        finally:
            logger.debug("ms=%s", SolBase.msdiff(ms))

    @classmethod
    def _get_inst_internal(cls, wmi_instance, wmi_class):
        """
        Get wmi instance
        :param wmi_instance: WMI
        :type wmi_instance: WMI
        :param wmi_class: object
        :param wmi_class: object
        :return  Iterable
        :rtype Iterable
        """
        ms = SolBase.mscurrent()
        try:
            return getattr(wmi_instance, wmi_class)()
        finally:
            logger.info("WMI, Fetched wmi_class=%s, ms=%s", wmi_class, SolBase.msdiff(ms))

    # ================================
    # TOOLS
    # ================================

    @classmethod
    def _get_class_name(cls, k):
        """
        Get class name
        :param k: object
        :return: str,unicode
        :rtype str,unicode
        """
        # noinspection PyProtectedMember
        return str(k._instance_of._class_name)

    @classmethod
    def _get_part_component_to_dict(cls, pc, f_hash):
        """
        Part component to dict
        :param pc: part component
        :param f_hash: dict for fields to fetch
        :param f_hash: dict
        :return tuple key, dict of props
        :rtype tuple
        """

        # Get key
        ar_key = list()
        for k_key in pc.keys:
            SolBase.sleep(0)
            v_key = getattr(pc, k_key)
            ar_key.append(str(v_key))
        partco_key = ".".join(ar_key)

        # Get props
        partco_prop = dict()
        for k_prop in pc.properties.keys():
            SolBase.sleep(0)

            # CHECK FIELD
            if len(f_hash) > 0 and k_prop not in f_hash:
                # Bypass this field, not registered
                continue

            v_prop = getattr(pc, k_prop)
            partco_prop[str(k_prop)] = v_prop

        return partco_key, partco_prop

    @classmethod
    def _get_props(cls, o, w_type, msq, f_hash, d_dict, r_dict):
        """
        Get properties as dict, merging toward d
        :param o: Iterable
        :type o: Iterable
        :param w_type: type of data (may force list)
        :param w_type: str
        :param msq: Time at which operation at started
        :type msq: int
        :param f_hash: fields to fetch
        :type f_hash: dict
        :param d_dict: Dict to merge to
        :type d_dict: dict
        :param r_dict: Refresh dict to merge to
        :type r_dict: dict
        """

        # List or dict
        if w_type == "list":
            pass
        elif w_type == "direct":
            pass
        else:
            raise Exception("invalid w_type=" + str(w_type))

        ms = SolBase.mscurrent()
        try:
            if w_type == "direct":
                # ===================
                # Direct
                # ===================

                k1 = o[0]
                # Register
                k1_class_name = cls._get_class_name(k1)
                d_dict[str(k1_class_name)] = dict()

                # Browse props
                for k2 in k1.properties.keys():
                    SolBase.sleep(0)

                    # CHECK FIELD
                    if len(f_hash) > 0 and k2 not in f_hash:
                        # Bypass this field, not registered
                        continue

                    v2 = getattr(k1, k2)
                    if k2 == "GroupComponent":
                        # Group component refer to upper level in the tree, degage
                        pass
                    elif k2 in ["PartComponent", "Antecedent", "Dependent"]:
                        # Get
                        partco_key, partco_props = cls._get_part_component_to_dict(v2, f_hash)
                        # Store
                        if k2 in ["PartComponent"]:
                            d_dict[str(k1_class_name)][str(partco_key)] = partco_props
                        else:
                            # Antecedent / Dependent
                            d_dict[str(k1_class_name)][str(k2)] = partco_props
                    else:
                        # Basic
                        d_dict[str(k1_class_name)][str(k2)] = v2

                # Refresh
                r_dict[str(k1_class_name)] = {"refresh_at": SolBase.mscurrent(), "last_elapsed": SolBase.msdiff(msq)}
            else:
                # ===================
                # LIST
                # ===================
                for k1 in o:
                    k1_class_name = cls._get_class_name(k1)
                    if str(k1_class_name) not in d_dict:
                        d_dict[str(k1_class_name)] = list()

                    local_dict = dict()
                    for k2 in k1.properties.keys():
                        SolBase.sleep(0)

                        # CHECK FIELD
                        if len(f_hash) > 0 and k2 not in f_hash:
                            # Bypass this field, not registered
                            continue

                        v2 = getattr(k1, k2)
                        if k2 == "GroupComponent":
                            # Group component refer to upper level in the tree, degage
                            pass
                        elif k2 in ["PartComponent", "Antecedent", "Dependent"]:
                            # Get
                            partco_key, partco_props = cls._get_part_component_to_dict(v2, f_hash)
                            # Store
                            if k2 in ["PartComponent"]:
                                local_dict[str(partco_key)] = partco_props
                            else:
                                # Antecedent / Dependent
                                if k2 not in local_dict:
                                    local_dict[str(k2)] = dict()
                                local_dict[str(k2)] = partco_props
                        else:
                            # Basic
                            local_dict[str(k2)] = v2
                    # Store
                    d_dict[str(k1_class_name)].append(local_dict)
                    # Refresh
                    r_dict[str(k1_class_name)] = {"refresh_at": SolBase.mscurrent(), "last_elapsed": SolBase.msdiff(msq)}
        finally:
            logger.info("WMI, Get props, ms=%s", SolBase.msdiff(ms))

    # ================================
    # PUBLIC
    # ================================

    @classmethod
    def wmi_get_dict(cls):
        """
        Get wmi dict
        :return: tuple dict, age in ms (int)
        :rtype tuple
        """

        if not cls._WMI_DICT:
            logger.warn("WMI dict is None, cannot process, last_refresh=%s, interval_ms=%s",
                        cls._WMI_DICT_LAST_REFRESH_MS, cls._WMI_GREENLET_INTERVAL_MS)
            raise Exception("WMI dict is None, cannot process")

        # Check age
        age_ms = SolBase.msdiff(cls._WMI_DICT_LAST_REFRESH_MS)
        if age_ms > cls._WMI_GREENLET_INTERVAL_MS * 2:
            # Too old
            logger.warn("WMI internal dict age is too old, last_refresh=%s, interval_ms=%s, age_ms=%s",
                        cls._WMI_DICT_LAST_REFRESH_MS, cls._WMI_GREENLET_INTERVAL_MS,
                        age_ms)

        # Ok
        return cls._WMI_DICT, int(SolBase.msdiff(cls._WMI_DICT_LAST_REFRESH_MS))

    @classmethod
    def _flush_props(cls, d_dict, r_dict):
        """
        Flush
        :param d_dict: dict
        :type d_dict: dict
        :param r_dict: dict
        :type r_dict: dict
        """

        for k1, v1 in d_dict.iteritems():
            assert isinstance(k1, str), "k1 not an str, class={0}, k1={1}".format(SolBase.get_classname(k1), k1)

            if isinstance(v1, dict):
                for k2, v2 in v1.iteritems():
                    assert isinstance(k2, str), "k2 not an str, class={0}, k2={1}".format(SolBase.get_classname(k2), k2)

                    if isinstance(v2, dict):
                        for k3, v3 in v2.iteritems():
                            assert isinstance(k3, str), "k3 not an str, class={0}, k3={1}".format(SolBase.get_classname(k3), k3)

                            logger.info("(vdict) %s :: %s => %s => %s", k1, k2, k3, v3)
                    else:
                        logger.info("(vdict) %s :: %s => %s", k1, k2, v2)
            elif isinstance(v1, list):
                idx = 0
                for cur_d in v1:
                    for k2, v2 in cur_d.iteritems():
                        assert isinstance(k2, str), "k1 not an str, class={0}, k1={1}".format(SolBase.get_classname(k1), k1)

                        if isinstance(v2, dict):
                            for k3, v3 in v2.iteritems():
                                assert isinstance(k3, str), "k1 not an str, class={0}, k1={1}".format(SolBase.get_classname(k1), k1)
                                logger.info("(vlist) %s :: [id %s] %s => %s => %s", k1, idx, k2, k3, v3)
                        else:
                            logger.info("(vlist) %s :: [id %s] %s => %s", k1, idx, k2, v2)
                    idx += 1
            else:
                # Direct
                logger.info("(nativ) %s :: %s", k1, v1)

        for k1, v1 in d_dict.iteritems():
            assert isinstance(k1, str), "k1 not an str, class={0}, k1={1}".format(SolBase.get_classname(k1), k1)
            age_ms = SolBase.msdiff(r_dict[k1]["refresh_at"])
            last_elapsed = r_dict[k1]["last_elapsed"]
            t = cls._WMI_INSTANCES[k1]["type"]
            logger.info("WMI state, t=%s, class=%s, last_elapsed=%.0f, age_ms=%.0f, ", t.ljust(6), k1.ljust(48), last_elapsed, age_ms)

    @classmethod
    def ensure_recent(cls, wmi_class, max_ms=1000):
        """
        Ensure specified class is more recent than max ms.
        This call will blocker the caller for WMI refresh if applicable.
        :param wmi_class: str,unicode
        :type wmi_class: str,unicode
        :param max_ms: float,int
        :type max_ms: float,int
        """

        ms = SolBase.mscurrent()
        try:
            assert wmi_class in cls._WMI_INSTANCES, "wmi_class not in cls._WMI_INSTANCES, wmi_class={0}".format(wmi_class)

            # Get the age
            age_ms = SolBase.msdiff(cls._WMI_DICT_PROPS[wmi_class]["refresh_at"])
            if age_ms > max_ms:
                logger.info("Performing blocking refresh, class=%s, age_ms=%s, max_ms=%s", wmi_class, age_ms, max_ms)

                # ------------------------
                # Refresh it
                # ------------------------

                # Get instance
                wmi_instance = cls._get_inst()

                # Get dict
                w_dict = cls._WMI_INSTANCES[wmi_class]

                # Hash the fields
                f_hash = dict()
                if "fields" in w_dict:
                    for field in w_dict["fields"]:
                        f_hash[field] = None

                # Fetch it
                local_counter_dict, local_refresh_dict = cls._wmi_fetch_one(wmi_instance, wmi_class, w_dict, f_hash)

                # Replace in lock (if we are more recent)
                with cls._WMI_DICT_LOCK:
                    age_in_dict = SolBase.msdiff(cls._WMI_DICT_PROPS[wmi_class]["refresh_at"])
                    age_us = SolBase.msdiff(local_refresh_dict[wmi_class]["refresh_at"])
                    if age_us < age_in_dict:
                        # ------------------
                        # Replace
                        # ------------------
                        logger.info("Pushing refresh, class=%s, age_us=%s, age_in_dict=%s", wmi_class, age_us, age_in_dict)
                        cls._WMI_DICT[wmi_class] = local_counter_dict[wmi_class]
                        cls._WMI_DICT_PROPS[wmi_class] = local_refresh_dict[wmi_class]
                    else:
                        # BYPASS
                        logger.info("Bypassing refresh, class=%s, age_us=%s, age_in_dict=%s", wmi_class, age_us, age_in_dict)
        finally:
            logger.info("Elapsed=%s", SolBase.msdiff(ms))

    # ================================
    # HELPER
    # ================================

    @classmethod
    def get_sec_epoch_from_ns(cls, ns):
        """
        Get ns (as TimestampSys100Ns) as second since epoch
        :param ns: float
        :type ns: float
        :return float
        :rtype float
        """

        ns -= 116444736000000000.0
        seconds = ns / 10000000.0
        return float(seconds)

    @classmethod
    def fix_uint32_max(cls, v):
        """
        Fix uint32 stuff
        :param v: v
        :param v: float
        :return: v
        :rtype float
        """

        if v < 0.0:
            v += 4294967295.0
        return v
