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
# noinspection PyPackageRequirements
from _socket import gaierror
import time
# noinspection PyPackageRequirements
import dns
# noinspection PyPackageRequirements
import logging
from dns.resolver import NoAnswer, NXDOMAIN, Resolver
from gevent import Timeout
from knockdaemon.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


def get_resolv():
    """
    Get resolvers
    :return list
    :rtype list
    """
    ar = Resolver().nameservers

    # Skip some resolver
    ar_out = list()
    for r in ar:
        if ar in ["0.0.0.0"]:
            logger.info("Skipping resolver=%s", r)
            continue
        else:
            logger.info("Keeping resolver=%s", r)
            ar_out.append(r)
    return ar_out


class CheckDns(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self, linux_support=True, windows_support=True)

        self.record = None
        self.dnsserver = None
        self.discoverylist = None

        self.dns_check_config = None

        self.host_to_check = None

        self.category = "/os/dns"

    def init_from_config(self, config_parser, section_name):
        """
        Initialize from configuration
        :param config_parser: dict
        :type config_parser: dict
        :param section_name: Ini file section for our probe
        :type section_name: str
        """

        # Base
        KnockProbe.init_from_config(self, config_parser, section_name)

        # Go
        self.host_to_check = config_parser[section_name]["dns_host"].split(',')

    def resolv(self, record, dnsserver):
        """
        Resolv
        :param record:
        :param dnsserver:
        :return:
        """
        self.record = record
        self.dnsserver = dnsserver

        additional_rdclass = 65535
        timeout = 5
        star_time = time.time()
        string_result = None

        response = None
        success = False

        with Timeout(timeout + 2, False):
            try:
                domain = dns.name.from_text(record)

                request = dns.message.make_query(domain, dns.rdatatype.A)
                request.flags |= dns.flags.AD
                request.find_rrset(request.additional, dns.name.root, additional_rdclass,
                                   dns.rdatatype.OPT, create=True, force_unique=True)
                request.timeout = timeout
                response = dns.query.udp(request, dnsserver, timeout=5)
            except Timeout:
                string_result = "KO: TimeOut %s " % dnsserver
            except NoAnswer:
                string_result = "KO: TimeOut %s " % dnsserver
            except NXDOMAIN:
                string_result = "KO: Host unkown %s " % dnsserver
            except gaierror as e:
                string_result = "KO: Dns server: %s[%s] " % (e.strerror, e.errno)
            except BaseException as e:
                string_result = "KO: Exception %s" % e.message

            if not response:
                if not string_result:
                    string_result = "KO: No response, no result, possible bug %s" % dnsserver
            elif len(response.answer) == 0:
                string_result = "KO: Empty Response from %s" % dnsserver
            else:
                result = list()
                # noinspection PyUnresolvedReferences
                for rdata in response.answer:
                    for item in rdata.items:
                        result.append(item.address)
                string_result = ",".join(sorted(result))
                success = True
            timeout_reached = False

        time_to_check = int((time.time() - star_time) * 1000)

        if timeout_reached:
            string_result = 'KO: Global TimeOut'
            time_to_check = None

        if not string_result:
            string_result = 'KO: Unknown Error 1'
        if len(string_result) == 0:
            string_result = 'KO: Unknown Error 2'

        return string_result, time_to_check, success

    def _execute_linux(self):
        """
        Exec
        :return:
        """
        self.dns_check_config = get_resolv()

        for dns_servers in self.dns_check_config:
            self.dns_check_group(dns_servers)

    def _execute_windows(self):
        """
        Exec
        """

        return self._execute_linux()

    def dns_check_group(self, dns_server):
        """
        Doc
        :param dns_server:
        :return:
        """

        for host_to_resolv in self.host_to_check:
            time_to_check = None

            # List
            disco_list = list()

            # Dict
            disco_dict = dict()
            disco_dict['{#HOST}'] = host_to_resolv
            disco_dict['{#SERVER}'] = dns_server
            disco_list.append(disco_dict)

            # Data dict => list
            data_dict = dict()
            data_dict["data"] = disco_list

            self.notify_discovery_n("k.dns.discovery", {"HOST": host_to_resolv, "SERVER": dns_server})

            string_result = ""

            for retry_count in range(3):
                result, time_to_check, success = self.resolv(host_to_resolv, dns_server)
                if success or retry_count == 2:
                    string_result += result
                    break

            self.notify_value_n("k.dns.resolv", {"HOST": host_to_resolv, "SERVER": dns_server}, string_result)

            if time_to_check is not None:
                self.notify_value_n("k.dns.time", {"HOST": host_to_resolv, "SERVER": dns_server}, time_to_check)
