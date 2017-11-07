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

try:

    import logging
    import os

    from os.path import dirname, abspath

    import sys
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import servicemanager
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import win32evtlogutil
    from pysolbase.FileUtility import FileUtility
    from pysolbase.SolBase import SolBase
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import win32service
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import win32serviceutil
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import win32event

    from knockdaemon2.Core.KnockManager import KnockManager
    from knockdaemon2.Windows.KnockDaemon.KnockDaemonEvent import KnockDaemonEvent
    from knockdaemon2.Windows.Registry.ClassRegistry import ClassRegistry
    from knockdaemon2.Windows.Wmi.Wmi import Wmi

    SolBase.voodoo_init()
    logger = logging.getLogger(__name__)

    # -------------------
    # ENV
    # EXPECTED PATTERN LIKE :
    # - Binary : C:\Program Files\knock\knockdaemon2\knockdaemon2.exe
    # - Config : C:\Program Files\knock\knockdaemon2\knockdaemon2.ini
    # - Config : C:\Program Files\knock\knockdaemon2\*.json
    # - Config : C:\Program Files\knock\knockdaemon2\conf.d\*.ini
    # - Logfile : C:\Users\champax\AppData\Local\knock\knockdaemon2\knockdaemon2.log
    # -------------------

    D_PATH = dict()

    # -------------------
    # Static
    # -------------------
    D_PATH["APP_NAME"] = "knockdaemon2"

    # -------------------
    # Get from system & current app
    # -------------------
    D_PATH["APPDATA_DIR"] = os.environ["LOCALAPPDATA"]
    D_PATH["CURRENT_DIR"] = dirname(abspath(__file__))

    # -------------------
    # Log files
    # -------------------
    D_PATH["LOG_DIR"] = SolBase.get_pathseparator().join([D_PATH["APPDATA_DIR"], "knock", "knockdaemon2"])
    D_PATH["LOG_FILE"] = SolBase.get_pathseparator().join([D_PATH["LOG_DIR"], "knockdaemon2.log"])

    # -------------------
    # Register event source context ASAP
    # -------------------
    KnockDaemonEvent.LOG_FILE = D_PATH["LOG_FILE"]
    KnockDaemonEvent.APP_NAME = D_PATH["APP_NAME"]

    # -------------------
    # DIRECT FILES
    # -------------------

    D_PATH["LOCATED_CONFIG_FILE"] = None
    D_PATH["LOCATED_MESSAGE_DLL"] = None

    pass

    # -------------------
    # INIT DAEMON CONTEXT
    # -------------------

    pass


    def set_default_paths():
        """
        Set default paths
        """

        D_PATH["AR_SEARCH_DIRS"] = list()

        # C:\Program Files\knock\knockdaemon2 (or equivalent)
        for cur_var in ["ProgramFiles", "ProgramFiles(x86)", "ProgramFiles(W6432)"]:
            if cur_var in os.environ:
                D_PATH["AR_SEARCH_DIRS"].append(SolBase.get_pathseparator().join([os.environ[cur_var], "knock", "knockdaemon2"]))

        D_PATH["AR_SEARCH_DIRS"].append(
            # For debug C:\champax\_devs\knockdaemon2\windows\pyinstaller
            SolBase.get_pathseparator().join(["C:", "champax", "_devs", "knockdaemon2", "windows", "pyinstaller", "dist"])
        )

        D_PATH["AR_SEARCH_DIRS"].append(
            # Current dir
            D_PATH["CURRENT_DIR"]
        )


    def initialize_daemon_context():
        """
        Initialize (or re-initialize) daemon context
        """

        # ---------------------
        # Reset
        # ---------------------
        D_PATH["LOCATED_CONFIG_FILE"] = None
        D_PATH["LOCATED_MESSAGE_DLL"] = None

        # ---------------------
        # Browse
        # ---------------------
        for cur_dir in D_PATH["AR_SEARCH_DIRS"]:
            # CONFIG
            if not D_PATH["LOCATED_CONFIG_FILE"]:
                f_config = SolBase.get_pathseparator().join([cur_dir, "knockdaemon2.ini"])
                logger.info("Config : trying %s", f_config)
                if FileUtility.is_file_exist(f_config):
                    D_PATH["LOCATED_CONFIG_FILE"] = f_config
                    logger.info("Found LOCATED_CONFIG_FILE=%s", D_PATH["LOCATED_CONFIG_FILE"])

            # DLL
            if not D_PATH["LOCATED_MESSAGE_DLL"]:
                f_dll = SolBase.get_pathseparator().join([cur_dir, "win32evtlog.pyd"])
                logger.info("Dll : trying %s", f_dll)
                if FileUtility.is_file_exist(f_dll):
                    D_PATH["LOCATED_MESSAGE_DLL"] = f_dll
                    logger.info("Found LOCATED_MESSAGE_DLL=%s", D_PATH["LOCATED_MESSAGE_DLL"])

        # ---------------------
        # Check
        # ---------------------
        if not D_PATH["LOCATED_CONFIG_FILE"]:
            logger.warn("Unable to locate LOCATED_CONFIG_FILE")
        if not D_PATH["LOCATED_MESSAGE_DLL"]:
            logger.warn("Unable to locate LOCATED_MESSAGE_DLL")

        # -------------------
        # Logs
        # -------------------
        for k, v in D_PATH.iteritems():
            logger.info("Having %s=%s", k, v)

        # -------------------
        # Register event source (windows)
        # -------------------

        try:
            # Check binary
            if not D_PATH["LOCATED_MESSAGE_DLL"]:
                logger.warn("Unable to AddSourceToRegistry")
            elif not FileUtility.is_file_exist(D_PATH["LOCATED_MESSAGE_DLL"]):
                raise Exception("APP_MESSAGE_DLL=%s not available" % D_PATH["LOCATED_MESSAGE_DLL"])
            else:
                # Register (this may fail if non root)
                logger.info("AddSourceToRegistry now")
                win32evtlogutil.AddSourceToRegistry(appName=D_PATH["APP_NAME"], msgDLL=D_PATH["LOCATED_MESSAGE_DLL"])
                logger.info("AddSourceToRegistry ok")
        except Exception as ex:
            # noinspection PyShadowingNames
            ex_str = SolBase.extostr(ex)
            logger.warn("AddSourceToRegistry failed, Ex=%s", ex_str)
            KnockDaemonEvent.report_warn("AddSourceToRegistry failed", ex_str)


    pass

    # =======================================================
    # =======================================================
    # BLOCK START, OUTSIDE FOR FUNCTIONS (DIRTY)
    # =======================================================
    # =======================================================

    # ==================================
    # SEARCH directories
    # ==================================
    set_default_paths()

    # ==================================
    # Report paths
    # ==================================
    KnockDaemonEvent.report_info("Using D_PATH=%s" % D_PATH)

    # ==================================
    # pyinstaller requires explicit import, do it now
    # ==================================

    ClassRegistry.register_all_classes()

    # =======================================================
    # =======================================================
    # BLOCK END, OUTSIDE FOR FUNCTIONS (DIRTY)
    # =======================================================
    # =======================================================

    pass

    # ==================================
    # WINDOWS SERVICE
    # ==================================

    pass


    class KnockDaemonService(win32serviceutil.ServiceFramework):
        """
        Windows service class
        """

        # NET START/STOP name
        _svc_name_ = D_PATH["APP_NAME"]

        # SERVICE name
        _svc_display_name_ = D_PATH["APP_NAME"]

        # SERVICE desc
        _svc_description_ = "knockdaemon2"

        def __init__(self, args):
            """
            Init
            :param args: args
            """

            # noinspection PyShadowingNames
            try:
                # ------------------
                # Log args and store them
                # ------------------

                # Event log
                logger.info("Init, args=%s", args)
                KnockDaemonEvent.report_info("knockdaemon2 __init__ called", "args=%s" % str(args))

                # Go
                self.args = args

                # Initialize
                initialize_daemon_context()

                # Check config (message dll is not fatal)
                if not D_PATH["LOCATED_CONFIG_FILE"]:
                    # Report a fatal warning
                    logger.error("Fatal : LOCATED_CONFIG_FILE not available, was using D_PATH=%s", D_PATH)
                    KnockDaemonEvent.report_error("Fatal : LOCATED_CONFIG_FILE not available, was using D_PATH=%s" % D_PATH)
                    sys.exit(-1)

                # ------------------
                # LOG : REDIRECT
                # ------------------
                if "debug" in args:
                    logger.info("Starting in debug mode, log to console")
                elif "KNOCK_UNITTEST" in os.environ:
                    logger.info("Starting in UNITTEST mode, log to console")
                else:
                    # SERVICE START
                    logger.info("Starting as normal service, going to redirect logs to file=%s", D_PATH["LOG_FILE"])
                    KnockDaemonEvent.report_info("Starting as normal service, going to redirect logs to file=%s" % D_PATH["LOG_FILE"])

                    # Create dirs
                    logger.info("Checking and creating dir=%s", D_PATH["LOG_DIR"])
                    # noinspection PyShadowingNames
                    try:
                        os.makedirs(D_PATH["LOG_DIR"])
                    except Exception as ex:
                        logger.debug("Ex=%s", SolBase.extostr(ex))

                    # Check them
                    if not FileUtility.is_dir_exist(D_PATH["LOG_DIR"]):
                        logger.error("Fatal : LOG_DIR not available, was using D_PATH=%s", D_PATH)
                        KnockDaemonEvent.report_error("Fatal : LOG_DIR not available, was using D_PATH=%s" % D_PATH)
                        sys.exit(-1)

                    # Reset loggers
                    logger.info("Redirect logs, (using 'time_file', rotating 7 days, one log per day), file=%s", D_PATH["LOG_FILE"])
                    KnockDaemonEvent.report_info("Redirect logs (using 'time_file', rotating 7 days, one log per day), file=%s" % D_PATH["LOG_FILE"])

                    SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file=D_PATH["LOG_FILE"], log_to_syslog=False, log_to_console=False, log_to_file_mode="time_file")

                    logger.info("Redirect logs, file=%s", D_PATH["LOG_FILE"])
                    KnockDaemonEvent.report_info("Redirected logs, file=%s" % D_PATH["LOG_FILE"])

                # ------------------
                # Logs all
                # ------------------
                for k1, v1 in D_PATH.iteritems():
                    logger.info("Starting with %s=%s", k1, v1)

                # ------------------
                # CALL BASE (if not unittest)
                # ------------------
                if "KNOCK_UNITTEST" not in os.environ:
                    logger.info("Call base class")
                    win32serviceutil.ServiceFramework.__init__(self, args)

                # ------------------
                # Stop event
                # ------------------
                self.stop_event = win32event.CreateEvent(None, 0, 0, None)

                # ------------------
                # Members
                # ------------------
                self.k = None
                self.is_running = False
                self.start_loop_exited = True
            except Exception as ex:
                # noinspection PyShadowingNames
                ex_str = SolBase.extostr(ex)
                logger.error("Ex=%s", ex_str)
                KnockDaemonEvent.report_error("Exception", ex_str)

        # noinspection PyPep8Naming
        def SvcDoRun(self):
            """
            Run method (BLOCKING)
            """

            # noinspection PyShadowingNames
            try:
                # ---------------------------
                # Starting
                # ---------------------------
                logger.info("knockdaemon2 starting")
                KnockDaemonEvent.report_info("knockdaemon2 starting")

                if "KNOCK_UNITTEST" not in os.environ:
                    self.ReportServiceStatus(win32service.SERVICE_START_PENDING)

                # Report paths
                KnockDaemonEvent.report_info("Starting using D_PATH=%s" % D_PATH)

                # ---------------------------
                # Fetch config
                # ---------------------------

                # Detected file (direct)
                config_file = D_PATH["LOCATED_CONFIG_FILE"]

                # Valid config
                logger.info("Checking config_file=%s", config_file)
                if not FileUtility.is_file_exist(config_file):
                    logger.error("Fatal : config_file not available, was using D_PATH=%s", D_PATH)
                    KnockDaemonEvent.report_error("Fatal : config_file not available, was using D_PATH=%s" % D_PATH)
                    sys.exit(-1)

                # Go
                KnockDaemonEvent.report_info("Found config_file", "Selected config_file=%s" % config_file)
                logger.info("Found config_file=%s", config_file)

                # Go
                self.is_running = True
                self.start_loop_exited = False

                # Init manager
                self.k = KnockManager(config_file)

                logger.info("Config loaded, signaling service up")
                KnockDaemonEvent.report_info("Config loaded, signaling service up")

                # We signal running ASAP to avoid 30 sec timeout while starting due to hardcoded service manager timeout...
                if "KNOCK_UNITTEST" not in os.environ:
                    self.ReportServiceStatus(win32service.SERVICE_RUNNING)

                # Windows wmi start (will perform initial full fetch in blocking mode)
                Wmi.wmi_start()
                logger.info("Wmi started")
                KnockDaemonEvent.report_info("Wmi started")

                # Fetch WMI to console
                # noinspection PyProtectedMember
                Wmi._flush_props(Wmi._WMI_DICT, Wmi._WMI_DICT_PROPS)

                # Start manager
                self.k.start()
                logger.info("Manager started")
                KnockDaemonEvent.report_info("Manager started")

                # Ok
                logger.info("knockdaemon2 started")
                KnockDaemonEvent.report_info("knockdaemon2 started")

                # ---------------------------
                # Engage run forever loop (and flush to event log from time to time the manager status)
                # ---------------------------

                start_ms = SolBase.mscurrent()
                last_log_ms = SolBase.mscurrent()
                logger.info("Writing initial manager status now")
                KnockDaemonEvent.write_manager_status(self.k)

                while self.is_running:
                    # Elapsed since start
                    ms_elapsed = SolBase.msdiff(start_ms)

                    # Log interval
                    if ms_elapsed < 10 * 60 * 1000:
                        # 1 min
                        log_interval_ms = 60000
                    else:
                        # 1 hour
                        log_interval_ms = 60 * 60 * 1000

                    # Check if we need to log
                    last_log_elapsed = SolBase.msdiff(last_log_ms)
                    if last_log_elapsed >= log_interval_ms:
                        # LOG
                        logger.info("Writing manager status now, ms_elapsed=%s, last_log_elapsed=%s, log_interval_ms=%s", ms_elapsed, last_log_elapsed, log_interval_ms)
                        KnockDaemonEvent.write_manager_status(self.k)
                        last_log_ms = SolBase.mscurrent()

                    # Sleep
                    SolBase.sleep(500)

                # ---------------------------
                # Stop
                # ---------------------------

                logger.info("knockdaemon2 stopping")
                KnockDaemonEvent.report_info("knockdaemon2 stopping")

                # Signal stop start
                if "KNOCK_UNITTEST" not in os.environ:
                    self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

                # Stop manager
                self.k.stop()
                logger.info("Manager stopped")
                KnockDaemonEvent.report_info("Manager stopped")

                # Stop wmi
                Wmi.wmi_stop()
                logger.info("Wmi stopped")
                KnockDaemonEvent.report_info("Wmi stopped")

                # Signal stop event
                self.start_loop_exited = True

                # Log
                logger.info("knockdaemon2 stopped")
                KnockDaemonEvent.report_info("knockdaemon2 stopped")
            except Exception as ex:
                # noinspection PyShadowingNames
                ex_str = SolBase.extostr(ex)
                logger.error("Ex=%s", ex_str)
                KnockDaemonEvent.report_error("Exception", ex_str)
                sys.exit(-1)
            finally:
                logger.info("Exiting method now")
                KnockDaemonEvent.report_info("Exiting method now")

        # noinspection PyPep8Naming
        def SvcStop(self):
            """
            Handle stop signal
            """

            # noinspection PyShadowingNames
            try:

                logger.info("Stop received")
                KnockDaemonEvent.report_info("Stop received")

                # Signal our event for shutdown
                logger.info("Signaling is_running")
                KnockDaemonEvent.report_info("Signaling is_running")
                self.is_running = False
                logger.info("Signaled is_running")
                KnockDaemonEvent.report_info("Signaled is_running")

                # Over
                logger.info("Stop signaled")
                KnockDaemonEvent.report_info("Stop signaled")
            except Exception as e:
                # noinspection PyShadowingNames
                ex_str = SolBase.extostr(e)
                logger.error("Ex=%s", ex_str)
                KnockDaemonEvent.report_error("Exception", ex_str)
                sys.exit(-1)
            finally:
                logger.info("Exiting method now")
                KnockDaemonEvent.report_info("Exiting method now")

        # noinspection PyPep8Naming
        def SvcInterrogate(self):
            """
            Interrogate (status)
            """
            try:
                logger.info("Interrogate received")
                # KnockDaemonEvent.report_info("Interrogate received")

                # Call base
                if "KNOCK_UNITTEST" not in os.environ:
                    self.ReportServiceStatus(win32service.SERVICE_RUNNING)

                logger.info("Interrogate processed")
                # KnockDaemonEvent.report_info("Interrogate processed")
            finally:
                logger.info("Exiting method now")
                # KnockDaemonEvent.report_info("Exiting method now")


    if __name__ == '__main__':
        try:
            if len(sys.argv) == 1:
                servicemanager.Initialize()
                servicemanager.PrepareToHostSingle(KnockDaemonService)
                servicemanager.StartServiceCtrlDispatcher()
            else:
                win32serviceutil.HandleCommandLine(KnockDaemonService)
        except Exception as e:
            ex_str = SolBase.extostr(e)
            logger.error("Main Ex=%s", ex_str)
            KnockDaemonEvent.report_error("Main Exception", ex_str)
        finally:
            logger.info("Exiting main now")
except Exception as e:
    # ===================
    # CRITICAL
    # ===================
    KnockDaemonEvent.report_error("CRITICAL Top Exception", e)
    print "CRITICAL Top Exception=" + str(e)
