"""
-*- coding: utf-8 -*-
===============================================================================

Copyright (C) 2013/2021 Laurent Labatut / Laurent Champagnac



 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2
 of the License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
 ===============================================================================
"""
import errno
import logging
import platform
import time
import ujson

import os
import psutil
from gevent import Timeout
from pysolbase.SolBase import SolBase
from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockHelpers import KnockHelpers
from knockdaemon2.Core.KnockManager import KnockManager
from knockdaemon2.Platform.PTools import PTools

SolBase.voodoo_init()

logger = logging.getLogger(__name__)


class ExitOnError(Exception):
    """
    exit_code list:
        2: no conf file
        3: cant install knockdaemon2
        5: Update already running
        127: unknow exception
    """

    def __init__(self, exit_code, message=''):
        """

        :param message: message
        :type message: str
        :param exit_code: int
        :type exit_code: int
        """
        super(ExitOnError, self).__init__(message)
        self.exit_code = exit_code


class AutoUpdateBase(object):
    """
    Auto update base class
    """

    _init_config_yaml = KnockManager.__dict__['_init_config_yaml']

    def __init__(self, config_file_name='/etc/knock/knockdaemon2/knockdaemon2.yaml', unittest=False, auto_start=True, lock_file='/var/run/knockdaemon2_autoupdate.pid'):
        """

        :param config_file_name: name of configuration file
        :type config_file_name: str
        :param unittest: run under unittest
        :type unittest: bool
        """
        if unittest:
            SolBase.logging_init(log_level="INFO", force_reset=True, log_to_file=False, log_to_syslog=False, log_to_console=True)

        # Config
        self._config_file_name = config_file_name

        # Unittest flag
        self._unittest = unittest

        # Parser instance
        self._d_yaml_config = None

        # Lock file
        self._file_lock = lock_file

        # Invoke timeout : 20 min
        self.invoke_timeout = 20 * 60 * 1000

        # Log
        logger.info("_config_file_name=%s", self._config_file_name)
        logger.info("_unittest=%s", self._unittest)
        logger.info("lock_file=%s", self._file_lock)
        logger.info("invoke_timeout=%s", self.invoke_timeout)

        # Http service url
        self._httpservice_kdversion_url = None

        # Config
        self._set_httpservice_kdversion_url()

        logger.info("_httpservice_kdversion_url=%s", self._httpservice_kdversion_url)

        # Run if autostart
        if auto_start:
            logger.info('Starting knockdaemon2 auto update now')
            self.run()

    def run(self, force_update=False):
        """
        main Run
        :return:
        :rtype:
        """

        # Lock
        self._acquire_lock()

        try:
            # Get prod version
            prod_version, url = self._get_prod_version()

            # Get local version (system dependent)
            local_version = self._z_platform_get_local_version()

            # Check
            if local_version is None:
                logger.warn('Cant get local version, please run apt-get update && apt-get install knockdaemon2 or equivalent')
                raise ExitOnError(2, 'No local version')

            # Check version
            if force_update or prod_version != local_version:
                # GO
                logger.info("Firing update now (local=%s, prod=%s, url=%s)", local_version, prod_version, url)
                self._z_platform_upgrade_knockdaemon2(url)
            else:
                # BYPASS
                logger.info('knockdaemon2 already up to date (local=%s, prod=%s)', local_version, prod_version)
        finally:
            # Release
            self._release_lock()

    def _get_prod_version(self):
        """
        Get version via httpservice
        :return: tuple (prod_version, download url)
        :rtype: tuple
        """
        os_name, os_version, os_arch = self._get_os()
        staging = self._get_config_staging()

        d_json = dict(
            os_version=os_version,
            os_name=os_name,
            os_arch=os_arch,
            staging=staging,
        )

        # Http request
        url = self._httpservice_kdversion_url
        hreq = HttpRequest()
        hc = HttpClient()
        hreq.uri = url
        hreq.post_data = ujson.dumps(d_json)
        logger.info("Firing uri=%s, d_json=%s", hreq.uri, d_json)
        hresp = hc.go_http(hreq)

        # load json
        try:
            resp_json = ujson.loads(hresp.buffer)
            logger.info("Got=%s", hresp)
        except Exception as err:
            logger.warn(SolBase.extostr(err))
            raise ExitOnError(2, err.message)

        # parse response
        try:
            if resp_json['st'] == 200:
                prod_version = resp_json['version']
                url = resp_json['url']
            else:
                msg = "reply from httpservice %s" % resp_json['message']
                logger.warn(msg)
                raise ExitOnError(2, msg)
        except Exception as err:
            logger.warn(SolBase.extostr(err))
            raise ExitOnError(2, err.message)

        return prod_version, url

    @classmethod
    def _get_os(cls):
        """

        :return: os_name, os_version, os_arch
        :rtype: tuple
        """
        if platform.system() == 'Linux':
            os_name, os_version, _ = platform.linux_distribution()
            os_arch = platform.machine()
            if os_arch == 'x86_64':
                os_arch = 'amd64'
        else:
            raise ExitOnError(2, "Not supported")

        # Override os_name
        logger.info("Overriding os_name=%s", os_name)
        os_name = PTools.get_distribution_type()
        logger.info("Returning os_name=%s, os_version=%s, os_arch=%s", os_name, os_version, os_arch)

        return os_name, os_version, os_arch

    # ==============================================
    # RESTART
    # ==============================================

    def _restart_daemon(self):
        """
        Restart daemon
        """

        kh = KnockHelpers()
        cmd = kh.sudoize("service knockdaemon2 restart")
        logger.info("Invoking, cmd=%s", cmd)
        ec, so, se = ButcherTools.invoke(cmd, shell=False, timeout_ms=self.invoke_timeout)
        if so:
            so = so.replace("\n", " | ")
        if se:
            se = se.replace("\n", " | ")
        if ec != 0:
            logger.warn("Invoke failed, ec=%s, so=%s, se=%s", ec, so, se)
        else:
            logger.info("Invoke ok, ec=%s, so=%s, se=%s", ec, so, se)

    # ==============================================
    # LOCK / PID
    # ==============================================

    def _acquire_lock(self):
        """
        Get lock
        """
        previous_pid = None
        if os.path.isfile(self._file_lock):
            # if file exist try to locate process
            file_mtime = os.path.getmtime(self._file_lock)
            with open(self._file_lock, 'r') as fd:
                # noinspection PyBroadException
                try:
                    previous_pid = int(fd.read().strip())
                except Exception:
                    if file_mtime + 5 * 60 < time.time():
                        self._create_lock()
                        return
                    else:
                        logger.warn('lock file too late')
                        raise ExitOnError(5, message='lock file too late %s sec' % int(time.time() - file_mtime))

            if AutoUpdateBase.pid_exists(previous_pid):
                if os.path.getmtime(self._file_lock) + 5 * 60 < time.time():
                    # kill process if stated since 5 min
                    psutil.Process(previous_pid).kill()
                    # wait for killed
                    try:
                        with Timeout(10):
                            while AutoUpdateBase.pid_exists(previous_pid):
                                SolBase.sleep(10)
                    except Timeout:
                        raise ExitOnError(5, 'Already running')

                    self._create_lock()
                    return
                else:
                    raise ExitOnError(5, 'Already running')

        self._create_lock()

    @classmethod
    def pid_exists(cls, pid):
        """
        Check whether pid exists in the current process table.
        UNIX only.
        :param pid: pid
        :type pid: int
        :return: bool
        :rtype: bool
        """
        if pid < 0:
            return False
        if pid == 0:
            # According to "man 2 kill" PID 0 refers to every process
            # in the process group of the calling process.
            # On certain systems 0 is a valid PID but we have no way
            # to know that in a portable fashion.
            raise ValueError('invalid PID 0')
        try:
            os.kill(pid, 0)
        except OSError as err:
            if err.errno == errno.ESRCH:
                # ESRCH == No such process
                return False
            elif err.errno == errno.EPERM:
                # EPERM clearly means there's a process to deny access to
                return True
            else:
                # According to "man 2 kill" possible error values are
                # (EINVAL, EPERM, ESRCH)
                raise ExitOnError(127, message='error %s' % err.message)
        else:
            return True

    def _create_lock(self):
        """
        Create lock
        """
        with open(self._file_lock, 'w') as fd:
            fd.write("%s" % os.getpid())

    def _release_lock(self):
        """
        Release lock

        """
        os.unlink(self._file_lock)

    # ==============================================
    # CONFIG
    # ==============================================

    def _set_httpservice_kdversion_url(self):
        """
        Set _httpservice_kdversion_url
        :return:
        :rtype: None
        """
        # load configuration
        try:
            self._d_yaml_config = self._init_config_yaml()
        except IOError as err:
            logger.warn(SolBase.extostr(err))
            raise ExitOnError(2, err.message)
        try:
            uri = None
            for k, d in self._d_yaml_config['transports'].iteritems():
                # Take the first one
                if d["class_name"].find("HttpAsyncTransport") >= 0:
                    uri = d["http_uri"]
                    break
            assert uri, "Need http_uri"
        except KeyError:
            logger.warn('Missing transport.http_uri parameter in conf file')
            raise ExitOnError(2, 'Missing transport.http_uri parameter in conf file')

        # Remove last word
        base_uri = '/'.join(uri.split('/')[:-1])

        # Store
        self._httpservice_kdversion_url = base_uri + '/kdversion'

    def _get_config_staging(self):
        """
        Get config
        :return: str
        :rtype: str
        """

        try:
            staging = self._d_yaml_config['knockd']['staging']
        except KeyError:
            staging = 'prod'
        return staging

    # ==============================================
    # ==============================================
    # SYSTEM DEPENDENT
    # ==============================================
    # ==============================================

    def _z_platform_get_local_version(self):
        """
        Get local version
        :return: Local version
        :rtype: str
        """

        raise NotImplementedError()

    def _z_platform_upgrade_knockdaemon2(self, binary_url):
        """
        Local update knock daemon
        :param binary_url: binary package url (deb, rpm, whatever)
        :type binary_url: str
        """
        raise NotImplementedError()
