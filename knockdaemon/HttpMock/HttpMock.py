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

# noinspection PyProtectedMember
from collections import OrderedDict

# noinspection PyProtectedMember
from gevent.baseserver import _parse_address
from os.path import abspath

from os.path import dirname
from threading import Lock
import urlparse
import ujson

import gevent
from gevent.pywsgi import WSGIServer
from gevent.event import Event
from pythonsol.FileUtility import FileUtility
from pythonsol.meter.MeterManager import MeterManager
from pythonsol.SolBase import SolBase

from knockdaemon.Core.KnockConfigurationKeys import KnockConfigurationKeys
from knockdaemon.Core.KnockStat import KnockStat

SolBase.voodoo_init()

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


class NotSupportedVersion(Exception):
    pass


class HttpMock(object):
    """
    Http mock
    """

    def __init__(self):
        """
        Constructor
        """

        # Daemon control
        self._locker = Lock()
        self._is_running = False
        self._server_greenlet = None

        # Zip on
        self._zip_enabled = True

        # Start event
        self._start_event = Event()

        # Server
        self._wsgi_server = None

        # Lifecycle stuff (from daemon)
        self._lifecycle_locker = Lock()
        self._lifecycle_interval_ms = 30000
        self._lifecycle_last_log_ms = SolBase.mscurrent()

        # Register counters
        MeterManager.put(KnockStat())

    # ==============================
    # START / STOP
    # ==============================

    def start(self):
        """
        Start
        """

        with self._locker:
            try:
                lifecyclelogger.info("Start : starting")

                # Check
                if self._is_running:
                    logger.warn("Already running, doing nothing")

                # Start
                self._server_greenlet = gevent.spawn(self._server_forever)
                SolBase.sleep(0)

                # Wait
                lifecyclelogger.debug("Start : waiting")
                self._start_event.wait()
                SolBase.sleep(0)

                # Signal
                self._is_running = True
                lifecyclelogger.info("Start : started")
            except Exception as e:
                logger.error("Exception, e=%s", SolBase.extostr(e))

    def stop(self):
        """
        Stop
        """

        # Signal out of lock (may help greenlet to exit itself)
        self._is_running = False

        # Flush out logs
        for k, v in MeterManager.get(KnockStat).to_dict().iteritems():
            logger.debug("Stop kstat, %s = %s", k, v)

        with self._locker:
            try:
                lifecyclelogger.info("Stop : stopping")

                # Stop
                if self._wsgi_server:
                    self._wsgi_server.close()
                    self._wsgi_server = None

                # Kill the greenlet
                if self._server_greenlet:
                    logger.info("_server_greenlet.kill")
                    self._server_greenlet.kill()
                    logger.info("_server_greenlet.kill done")
                    # gevent.kill(self._server_greenlet)
                    self._server_greenlet.join()
                    self._server_greenlet = None

                lifecyclelogger.info("Stop : stopped")
            except Exception as e:
                logger.error("Exception, e=%s", SolBase.extostr(e))

    # =====================================
    # LIFECYCLE
    # =====================================

    def _lifecycle_log_status(self):
        """
        Run
        """

        try:
            with self._lifecycle_locker:
                # Check
                ms_diff = SolBase.msdiff(self._lifecycle_last_log_ms)
                if ms_diff < self._lifecycle_interval_ms:
                    return

                # Log now
                self._lifecycle_last_log_ms = SolBase.mscurrent()

            # noinspection PyProtectedMember
            lifecyclelogger.info(
                "self=%s",
                # Id
                id(self),
            )
        except Exception as e:
            logger.warning("Exception, ex=%s", SolBase.extostr(e))

    # ==============================
    # SERVER
    # ==============================

    def _server_forever(self):
        """
        Exec loop
        """

        try:
            # Alloc
            logger.info("Allocating WSGIServer")
            self._wsgi_server = WSGIServer(listener=('localhost', 7900), application=self.on_request)

            logger.info("DEBUG SOS, %s, %s", self._wsgi_server.address, _parse_address(self._wsgi_server.address))
            SolBase.sleep(0)

            # Signal
            logger.info("Signaling _start_event")
            self._start_event.set()
            SolBase.sleep(0)

            # This will block until signaled
            logger.info("Calling serve_forever")
            self._wsgi_server.serve_forever()
        except Exception as e:
            logger.error("Ex=%s", SolBase.extostr(e))
            # This is fatal, we exit, we cannot serve
            exit(-1)
        finally:
            logger.info("Clearing _start_event")
            self._start_event.clear()

    # ==========================
    # TOOLS
    # ==========================

    def _get_param_from_qs(self, environ):
        """
        Extract params from query string
        :param environ: dict
        :type environ: dict
        :return dict
        :rtype dict
        """

        return self._get_param_internal(environ["QUERY_STRING"])

    def _get_param_from_post_data(self, environ):
        """
        Extract params from post data (treat them as a normal query string)
        Assume post data is urlencoded.
        :param environ: dict
        :type environ: dict
        :return dict
        :rtype dict
        """

        return self._get_param_internal(self._get_post_data(environ))

    # noinspection PyMethodMayBeStatic
    def _get_param_internal(self, buf):
        """
        Get param from a buffer (query string or post data)
        Assume post data is urlencoded.
        :param buf: str
        :type buf: str
        :return dict
        :rtype dict
        """

        if not buf:
            return dict()
        elif len(buf) == 0:
            return dict

        # Decode, browse and hash (got a list of tuple (param, value))
        d = dict()
        for tu in urlparse.parse_qsl(buf, keep_blank_values=True, strict_parsing=True):
            d[tu[0]] = tu[1]
        return d

    # noinspection PyMethodMayBeStatic
    def _get_post_data_raw(self, environ):
        """
        Get post data, raw, not decoded. Return an empty string is no post data.
        :param environ: dict
        :type environ: dict
        :return str
        :rtype str
        """
        wi = environ["wsgi.input"]
        if not wi:
            return ""
        else:
            return wi.read()

    def _get_post_data(self, environ):
        """
        Get post data, raw, not decoded. Return an empty string is no post data.
        :param environ: dict
        :type environ: dict
        :return str
        :rtype str
        """
        wi = self._get_post_data_raw(environ)
        if wi:
            # Try gzip
            try:
                wi = wi.decode("zlib")
            except Exception as ex:
                logger.debug("Unable to decode zlib, should be a normal buffer, ex=%s",
                             SolBase.extostr(ex))

        return wi

    # ==============================
    # MAIN REQUEST CALLBACK
    # ==============================

    def on_request(self, environ, start_response):
        """
        On request callback
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        try:
            logger.info("Request start now")

            # Log
            for k, v in environ.iteritems():
                logger.debug("Env: %s=%s", k, v)

            # Switch
            pi = environ["PATH_INFO"]
            logger.debug("pi=%s", pi)

            # Sometimes PATH_INFO come with full uri (urllib3) (?!)
            # http://127.0.0.1:7900/unittest

            if pi.endswith("/mockdeb"):
                return self._on_mockdeb(environ, start_response)
            elif pi.endswith("/mockrpm"):
                return self._on_mockrpm(environ, start_response)
            elif pi.endswith("/pv2"):
                return self._on_probe_v2(environ, start_response)
            elif pi.endswith("/logv1"):
                return self._on_log_v1(environ, start_response)
            elif pi.endswith("/unittest"):
                return self._on_unit_test(environ, start_response)
            elif pi.endswith("/junittest"):
                return self._on_json_unit_test(environ, start_response)
            elif pi.endswith("/kdversion"):
                return self._on_kdversion(environ, start_response)
            else:
                return self._on_invalid(start_response)
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            status = "500 Internal Server Error"
            body = status
            headers = [('Content-Type', 'text/plain')]
            start_response(status, headers)
            return [body]
        finally:
            self._lifecycle_log_status()

    # ==============================
    # REQUEST : INVALID
    # ==============================

    # noinspection PyMethodMayBeStatic
    def _on_invalid(self, start_response):
        """
        On request callback
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        # Debug
        status = "400 Bad Request"
        body = status
        headers = [('Content-Type', 'text/txt')]
        start_response(status, headers)
        return [body]

    # ==============================
    # REQUEST : UNITTEST
    # ==============================

    def _on_unit_test(self, environ, start_response):
        """
        On request callback
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        # Param
        from_qs = self._get_param_from_qs(environ)
        from_post = self._get_param_from_post_data(environ)

        # Debug
        status = "200 OK"
        body = "OK" + "\n"
        body += "from_qs=" + str(from_qs) + " -EOL\n"
        body += "from_post=" + str(from_post) + " -EOL\n"
        headers = [('Content-Type', 'text/txt')]
        start_response(status, headers)
        return [body]

    # ==============================
    # REQUEST : UNITTEST
    # ==============================

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def _on_mockdeb(self, environ, start_response):
        """
        On request callback
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        # Get the .deb full path
        s = SolBase.get_pathseparator()
        current_dir = dirname(abspath(__file__)) + s
        deb_file = current_dir + "../../knockdaemon_test/ForTest/knockdaemon_mock.deb"

        # Load it (binary)
        buf = FileUtility.file_to_byte_buffer(deb_file)

        # Send it

        # Debug
        status = "200 OK"
        headers = [('Content-Type', 'application/octet-stream')]
        body = buf
        start_response(status, headers)
        return [body]

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def _on_mockrpm(self, environ, start_response):
        """
        On request callback
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        # Get the .deb full path
        s = SolBase.get_pathseparator()
        current_dir = dirname(abspath(__file__)) + s
        rpm_file = current_dir + "../../knockdaemon_test/ForTest/knockdaemon_mock.rpm"

        # Load it (binary)
        buf = FileUtility.file_to_byte_buffer(rpm_file)

        # Send it

        # Debug
        status = "200 OK"
        headers = [('Content-Type', 'application/octet-stream')]
        body = buf
        start_response(status, headers)
        return [body]

    # ==============================
    # REQUEST : PROBES
    # ==============================

    def _on_json_unit_test(self, environ, start_response):
        """
        Json unit pythonsol
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        # We expect POST DATA, not url encoded
        post_data = self._get_post_data(environ)

        # We fallback to QS for debug only
        if len(post_data) == 0:
            # Process and decode QS
            dqs = self._get_param_from_qs(environ)
            # Assume we got post data into "pd" param
            post_data = dqs["pd"]

        # Ok, post_data are json buffer, process it
        d = ujson.loads(post_data)
        logger.debug("d=%s", d)

        # Reply
        rd = dict()
        rd["st"] = 200
        status = "200 OK"
        body = ujson.dumps(rd)
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)
        return [body]

    # ==============================
    # REQUEST : PROBES
    # ==============================

    def _on_probe_v2(self, environ, start_response):
        """
        Probe v2 (array)
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        try:
            # We expect POST DATA, not url encoded
            post_data = self._get_post_data(environ)

            # Ok, post_data are json buffer, process it
            d = ujson.loads(post_data)
            logger.debug("d=%s", d)

            # Options
            protocol_array = d["par"]
            options = d["o"]

            # Allocate
            account_hash = dict()
            node_hash = dict()
            notify_hash = dict()
            notify_values = list()

            # Browse chunks
            for cur_buf in protocol_array:
                cur_d = ujson.loads(cur_buf)
                account_hash.update(cur_d["a"])
                node_hash.update(cur_d["n"])
                notify_hash.update(cur_d["h"])
                notify_values.extend(cur_d["v"])

            # Process options
            zip_support = options["zip"]

            # Go to supervision
            ms_start = SolBase.mscurrent()
            b, ok_count, ko_count = self._go_to_supervision(
                account_hash, node_hash, notify_hash, notify_values)

            # Reply
            rd = dict()
            rd["st"] = 200
            rd["ac"] = len(account_hash)
            rd["nc"] = len(node_hash)
            rd["hc"] = len(notify_hash)
            rd["vc"] = len(notify_values)
            rd["sp"] = {"ok": ok_count, "ko": ko_count, "ms": int(SolBase.msdiff(ms_start))}
            status = "200 OK"
            body = ujson.dumps(rd)
            if self._zip_enabled and zip_support:
                body = body.encode("zlib")
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)
            return [body]
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            # Reply success to avoid client enqueing stuff if we are buggy
            rd = dict()
            rd["st"] = 200
            status = "200"
            body = ujson.dumps(rd)
            if self._zip_enabled:
                body = body.encode("zlib")
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)
            return [body]

    # ==============================
    # REQUEST : VERSION
    # ==============================

    def _on_kdversion(self, environ, start_response):
        """
         Knock daemon get last version
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """
        # We expect POST DATA, not url encoded
        post_data = self._get_post_data(environ)
        return_status_code = 200
        return_status_message = "OK"
        version = 'UNK'
        from_cache = False
        package_url = None
        client_os_name = None

        try:
            # We fallback to QS for debug only
            if len(post_data) == 0:
                # Process and decode QS
                p = self._get_param_from_qs(environ)

            else:
                p = ujson.loads(post_data)

            # Just log
            client_os_name = p['os_name']
            client_os_version = p['os_version']
            client_os_arch = p['os_arch']
            logger.info("GOT OS name=%s, version=%s, arch=%s", client_os_name, client_os_version, client_os_arch)

        except KeyError:
            logger.warning("Missing parameters")
            return_status_code = 418
            return_status_message = "I'm a teapot"

        except Exception as e:
            logger.warning(SolBase.extostr(e))
            return_status_code = 500
            return_status_message = 'Internal error'

        if return_status_code == 200:
            try:
                # Mock, we hard code and target our local mock handler
                if client_os_name == "debian":
                    version = "0.1.1-406"
                    package_url = "http://127.0.0.1:7900/mockdeb"
                    from_cache = False
                elif client_os_name == "redhat" or client_os_name == "centos":
                    version = "0.1.1-452"
                    package_url = "http://127.0.0.1:7900/mockrpm"
                    from_cache = False

            except NotSupportedVersion as e:
                logger.warning(SolBase.extostr(e))
                return_status_message = 'Version not supported'
                return_status_code = 404
            except Exception as e:
                package_url = None
                logger.warning(SolBase.extostr(e))

        # Reply
        rd = dict()
        rd["st"] = return_status_code
        rd["message"] = return_status_message
        if return_status_code == 200:
            rd["version"] = version
            rd["url"] = package_url
            rd['fc'] = from_cache
        status = "200 OK"
        body = ujson.dumps(rd)
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)
        return [body]

    # ==============================
    # REQUEST : LOGS
    # ==============================

    def _on_log_v1(self, environ, start_response):
        """
        Logs v1
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        try:
            # We expect POST DATA, not url encoded
            post_data = self._get_post_data(environ)

            # Ok, post_data are json buffer, process it
            d = ujson.loads(post_data)
            logger.debug("d=%s", d)

            # We expect "logs" as a list of dict["type", "data"] and "nm" as str
            if "main_type" not in d:
                raise Exception("main_type required")
            main_type = d["main_type"]
            namespace = d.get("namespace", "")
            host = d.get("host", "")
            for d_log in d["logs"]:
                t = d_log["type"]
                data = d_log["data"]
                logger.info("Got main_type=%s, namespace=%s, host=%s, t=%s, data=%s", main_type, namespace, host, t, repr(data))

            # Reply
            rd = dict()
            rd["st"] = 200
            rd["log_count"] = len(d["logs"])
            status = "200 OK"
            body = ujson.dumps(rd)
            if self._zip_enabled:
                body = body.encode("zlib")
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)
            return [body]
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            rd = dict()
            rd["st"] = 500
            status = "500"
            body = ujson.dumps(rd)
            if self._zip_enabled:
                body = body.encode("zlib")
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)
            return [body]

    def _go_to_supervision(self, account_hash, node_hash, notify_hash, notify_values):
        """
        Go to supervision
        :param account_hash: dict
        :type account_hash: dict
        :param node_hash: dict
        :type node_hash: dict
        :param notify_hash: Hash str to (disco_key, disco_id, tag)
        :type notify_hash; dict
        :param notify_values: List of (superv_key, tag, value)
        :type notify_values; list
        :return tuple (True if all success, processed, failed)
        :rtype tuple
        """

        # ----------------------------
        # NODES
        # ----------------------------
        for k, v in node_hash.iteritems():
            logger.debug("Node %s: %s", k, v)

        # Get host
        host = node_hash["host"]

        # Get namespace
        account_ns = account_hash[KnockConfigurationKeys.INI_KNOCKD_ACC_NAMESPACE]

        # Ok, push all
        return self._go_to_supervision_internal(account_ns, host, notify_hash,
                                                notify_values)

    # noinspection PyMethodMayBeStatic
    def _go_to_supervision_internal(self, account_ns, host, notify_hash, notify_values):
        """
        Go to supervision
        :param account_ns: str
        :type account_ns: str
        :param notify_hash: Hash str to (disco_key, disco_id, tag)
        :type notify_hash; dict
        :param notify_values: List of (superv_key, tag, value)
        :type notify_values; list
        :return tuple (success, processed, failed)
        :rtype tuple
        """

        # ----------------------------
        # A) DISCOVERY (aka notify_hash)
        # ----------------------------

        # Prefix with namespace (dirty, to clean)
        # noinspection PyAugmentAssignment
        host = account_ns + "." + host

        # {
        # "host": "LLABATUT",
        # "value": "{"data": [{"{#RDPORT}": "6380"}, {"{#RDPORT}": "ALL"}]}",
        # "key": "test.dummy.discovery",
        # "clock": 1369399569.651645
        # }

        # Merge disco key to list
        hash_disco_key_to_list = dict()
        for k, tu in notify_hash.iteritems():

            # OLD FORMAT :
            # Key => tuple (disco_key, disco_id, tag)
            #
            # NEW FORMAT :
            # Key => tuple (disco_key, OrderedDict)

            if len(tu) == 3:
                # -----------------------
                # OLD FORMAT
                # -----------------------
                disco_key = tu[0]
                disco_id = tu[1]
                tag = tu[2]
                logger.debug("Got %s : %s, %s, %s", k, disco_key, disco_id, tag)

                # Hash
                superv_disco_key = disco_key + ".discovery"
                if superv_disco_key not in hash_disco_key_to_list:
                    hash_disco_key_to_list[superv_disco_key] = list()

                # Local dict
                local_dict = dict()
                d_key = "{#" + disco_id + "}"
                d_value = tag
                local_dict[d_key] = d_value

                # Add to list of dict
                hash_disco_key_to_list[superv_disco_key].append(local_dict)
            elif len(tu) == 2:
                # -----------------------
                # NEW FORMAT
                # -----------------------
                disco_key = tu[0]
                dd = tu[1]
                assert isinstance(dd, dict), "dd must be a dict, got={0}, value={1}".format(SolBase.get_classname(dd), dd)
                assert disco_key.endswith(".discovery"), "disco_key must end with .discovery, got={0}".format(disco_key)

                # Switch to ordered dict
                od = OrderedDict(sorted(dd.items(), key=lambda z: z[0]))

                # Hash
                if disco_key not in hash_disco_key_to_list:
                    hash_disco_key_to_list[disco_key] = list()

                # Browse
                local_dict = dict()
                for disco_id, disco_tag in od.iteritems():
                    # Create dict
                    local_dict["{#" + disco_id + "}"] = disco_tag

                # Add it
                hash_disco_key_to_list[disco_key].append(local_dict)

            else:
                raise Exception("Unknown format, tu={0}".format(tu))

        # ----------------------------
        # B) BUILD data_list using DISCO, browse hash_disco_key_to_list
        # ----------------------------
        disco_list = list()
        for superv_disco_key, localList in hash_disco_key_to_list.iteritems():
            # Value is a JSON { "data" : [ list of dict ]
            json_dict = dict()
            json_dict["data"] = localList
            json_local_buf = ujson.dumps(json_dict)
            # Set
            local_dict = dict()
            local_dict["host"] = host  # unittest.LLABATUT
            local_dict["key"] = superv_disco_key  # test.dummy.discovery
            local_dict["value"] = json_local_buf
            local_dict["clock"] = 1

            # Add
            disco_list.append(local_dict)

        # ----------------------------------
        # C) PROCESS VALUES (aka notify_values)
        # 4 possibilities :
        #
        # A - simple value
        #   => key=k.apache.dummy[default], tag=None, value=value, t=ms)
        #
        # B - discovery simple value
        #   => (key=k.apache.discovery, tag=None, value={"data":[{"{#ID}":"www"}]}, t=ms)
        #
        # C - tag value
        #   => (key=k.apache.dummy, tag=ID, value=www, t=ms)
        #
        # D - tag value as OrderedDict
        #   => (key=k.apache.dummy, tag={ID:www, SERVER:s1}, value=value, t=ms)
        # ----------------------------------

        # Data : probes values
        local_list_disco = list()
        local_list_data = list()
        for tu in notify_values:
            superv_key = tu[0]
            tag = tu[1]
            value = tu[2]
            t = tu[3]
            d_opts_tags = tu[4]

            # Debug
            logger.debug("Got %s, %s, %s, %s, %s", superv_key, tag, value, t, d_opts_tags)

            # Set
            local_dict = dict()
            local_dict["host"] = host
            local_dict["value"] = value
            local_dict["clock"] = t

            if tag:
                if isinstance(tag, dict):
                    # --------------------
                    # D) NEW FORMAT
                    # --------------------
                    # We DONT need DISCOVERY HERE, it has already been push by previous notify hash
                    # Bu we need to append disco tags to probes name
                    new_superv_key = superv_key
                    # Switch to ordered dict
                    od = OrderedDict(sorted(tag.items(), key=lambda z: z[0]))
                    if len(od) > 1:
                        pass
                    sa = "["
                    for k, v in od.iteritems():
                        # sa += "'" + v + "',"
                        sa += "" + v + ","
                    sa = sa[:-1]
                    sa += "]"
                    new_superv_key += sa
                    # Override
                    logger.debug("DISCO_V4 : Replacing superv_key=%s, new_superv_key=%s, od=%s", superv_key, new_superv_key, od)
                    superv_key = new_superv_key
                    # Add it
                    local_dict["key"] = superv_key
                    local_list_data.append(local_dict)
                elif len(tag) > 0:
                    # --------------------
                    # C) OLD FORMAT : DATA ONLY
                    # --------------------
                    # We do NOT allow discovery here
                    if superv_key.endswith(".discovery"):
                        logger.warn(".discovery not allowed in tag value, got %s, %s, %s, %s", superv_key, tag, value, t)
                        raise Exception(".discovery not allowed in tag value")

                    # Tag value
                    local_dict["key"] = "{0}[{1}]".format(superv_key, tag)
                    local_list_data.append(local_dict)
                else:
                    raise Exception("Unknown tag={0}".format(tag))
            elif superv_key.endswith(".discovery"):
                # --------------------
                # B) Simple : discovery
                # --------------------
                local_dict["key"] = superv_key
                local_list_disco.append(local_dict)

                # If we have "k.business", we must sent to host aggreg also
                if superv_key.startswith("k.business"):
                    aggreg_dict = dict()
                    aggreg_dict["host"] = "K.Host.Aggreg"
                    aggreg_dict["namespace"] = account_ns
                    aggreg_dict["value"] = value
                    aggreg_dict["clock"] = t
                    aggreg_dict["key"] = superv_key
                    local_list_disco.append(aggreg_dict)
                    logger.info("K.Host.Aggreg : pushing aggreg_dict=%s", aggreg_dict)

            else:
                # --------------------
                # A) Simple
                # --------------------
                local_dict["key"] = superv_key
                local_list_data.append(local_dict)

        # ---------------------------
        # D) NEW CODE PATH
        # ---------------------------
        r_is_ok = True
        r_ok = 0
        r_ko = 0
        try:
            # ---------------------------
            # DISPATCH IN TWO LIST
            # ---------------------------

            # Realloc pure data list
            data_list = list()

            # Priority to discovery
            for it in local_list_disco:
                disco_list.append(it)

            # Then disco
            for it in local_list_data:
                data_list.append(it)

            # ---------------------------
            # A : Fire discovery one by one
            # ---------------------------

            logger.info("DISCO Processing (sequential) disco_list.len=%s", len(disco_list))

            for cur_disco_dict in disco_list:
                # Fire it
                logger.info("DISCO Processing (single disco), cur_disco_dict.len=%s", len(cur_disco_dict))

                # ---------------------------
                # DISCO : Fire zab
                # ---------------------------

                # Alloc a local list
                single_disco_list = list()
                single_disco_list.append(cur_disco_dict)

                # Fire it
                logger.info("DISCO Firing (single disco), single_disco_list.len=%s", len(single_disco_list))

                # Fire simulated
                ok_count = len(single_disco_list)
                ko_count = 0

                # Total processed
                r_ok += ok_count
                r_ko += ko_count

            # ---------------------------
            # B : Fire all datas
            # ---------------------------
            logger.info("DATA Firing (bulk), data_list.len=%s", len(data_list))
            is_ok = True
            ok_count = len(data_list)
            ko_count = 0
            if not is_ok:
                r_is_ok = False

            r_ok += ok_count
            r_ko += ko_count
        except Exception as e:
            logger.warn("Exception (new code path), ex=%s", SolBase.extostr(e))
            raise
        finally:
            # required for unittest
            MeterManager.get(KnockStat).transport_spv_processed.increment(r_ok)
            MeterManager.get(KnockStat).transport_spv_failed.increment(r_ko)
            MeterManager.get(KnockStat).transport_spv_total.increment(r_ok + r_ko)
            return r_is_ok, r_ok, r_ko

    # noinspection PyMethodMayBeStatic
    def _go_to_supervision_internal_old(self, account_ns, host, notify_hash, notify_values):
        """
        Go to supervision
        :param account_ns: str
        :type account_ns: str
        :param notify_hash: Hash str to (disco_key, disco_id, tag)
        :type notify_hash; dict
        :param notify_values: List of (superv_key, tag, value)
        :type notify_values; list
        :return tuple (success, processed, failed)
        :rtype tuple
        """

        # ----------------------------
        # DISCOVERY (aka notify_hash)
        # ----------------------------

        # Prefix with namespace (dirty, to clean)
        # noinspection PyAugmentAssignment
        host = account_ns + "." + host

        # Merge disco key to list
        hash_disco_key_to_list = dict()
        for k, tu in notify_hash.iteritems():
            disco_key = tu[0]
            disco_id = tu[1]
            tag = tu[2]
            logger.debug("Got %s : %s, %s, %s", k, disco_key, disco_id, tag)

            # Hash
            superv_disco_key = disco_key + ".discovery"
            if superv_disco_key not in hash_disco_key_to_list:
                hash_disco_key_to_list[superv_disco_key] = list()

            # Local dict
            local_dict = dict()
            d_key = "{#" + disco_id + "}"
            d_value = tag
            local_dict[d_key] = d_value

            # Add to list of dict
            hash_disco_key_to_list[superv_disco_key].append(local_dict)
        logger.debug("hash_disco_key_to_list=%s", hash_disco_key_to_list)

        # Browse it
        data_list = list()
        for superv_disco_key, localList in hash_disco_key_to_list.iteritems():
            # Value is a JSON { "data" : [ list of dict ]
            json_dict = dict()
            json_dict["data"] = localList
            json_local_buf = ujson.dumps(json_dict)
            # Set
            local_dict = dict()
            local_dict["host"] = host  # unittest.LLABATUT
            local_dict["key"] = superv_disco_key  # test.dummy.discovery
            local_dict["value"] = json_local_buf
            local_dict["clock"] = 1

            # Add
            data_list.append(local_dict)

        # ----------------------------------
        # VALUES (aka notify_values)
        # 3 possibilities :
        # - simple value
        #   => key=k.apache.dummy[default], tag=None, value=value, t=ms)
        # - discovery simple value
        #   => (key=k.apache.discovery, tag=None, value={"data":[{"{#ID}":"www"}]}, t=ms)
        # - tag value
        #   => (key=k.apache.dummy, tag=ID, value=www, t=ms)
        # ----------------------------------

        # Data : probes values
        local_list_disco = list()
        local_list_data = list()
        for tu in notify_values:
            superv_key = tu[0]
            tag = tu[1]
            value = tu[2]
            t = tu[3]

            # Debug
            logger.debug("Got %s, %s, %s, %s", superv_key, tag, value, t)

            # Set
            local_dict = dict()
            local_dict["host"] = host
            local_dict["value"] = value
            local_dict["clock"] = t

            if tag and len(tag) > 0:
                # We do NOT allow discovery here
                if superv_key.endswith(".discovery"):
                    logger.warn(".discovery not allowed in tag value, got %s, %s, %s, %s", superv_key, tag, value, t)
                    raise Exception(".discovery not allowed in tag value")

                # Tag value
                local_dict["key"] = "{0}[{1}]".format(superv_key, tag)
                local_list_data.append(local_dict)
            elif superv_key.endswith(".discovery"):
                # Simple : discovery
                local_dict["key"] = superv_key
                local_list_disco.append(local_dict)
            else:
                # Simple
                local_dict["key"] = superv_key
                local_list_data.append(local_dict)

        # ---------------------------
        # GO
        # ---------------------------
        r_is_ok = True
        r_ok = 0
        r_ko = 0
        try:
            # ---------------------------
            # DISPATCH IN TWO LIST
            # ---------------------------

            # Already set : disco only
            disco_list = data_list

            # Realloc pure data list
            data_list = list()

            # Priority to discovery
            for it in local_list_disco:
                disco_list.append(it)

            # Then disco
            for it in local_list_data:
                data_list.append(it)

            # ---------------------------
            # A : Fire discovery one by one
            # ---------------------------

            logger.info("DISCO Processing (sequential) disco_list.len=%s", len(disco_list))

            for cur_disco_dict in disco_list:
                # Fire it
                logger.info("DISCO Processing (single disco), cur_disco_dict.len=%s", len(cur_disco_dict))

                # ---------------------------
                # DISCO : Fire zab
                # ---------------------------

                # Alloc a local list
                single_disco_list = list()
                single_disco_list.append(cur_disco_dict)

                # Fire it
                logger.info("DISCO Firing (single disco), single_disco_list.len=%s", len(single_disco_list))

                # Fire simulated
                ok_count = len(single_disco_list)
                ko_count = 0

                # Total processed
                r_ok += ok_count
                r_ko += ko_count

            # ---------------------------
            # B : Fire all datas
            # ---------------------------
            logger.info("DATA Firing (bulk), data_list.len=%s", len(data_list))
            is_ok = True
            ok_count = len(data_list)
            ko_count = 0
            if not is_ok:
                r_is_ok = False

            r_ok += ok_count
            r_ko += ko_count
        except Exception as e:
            logger.warn("Exception (new code path), ex=%s", SolBase.extostr(e))
            raise
        finally:
            # required for unittest
            MeterManager.get(KnockStat).transport_spv_processed.increment(r_ok)
            MeterManager.get(KnockStat).transport_spv_failed.increment(r_ko)
            MeterManager.get(KnockStat).transport_spv_total.increment(r_ok + r_ko)
            return r_is_ok, r_ok, r_ko
