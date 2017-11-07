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

import struct
from ctypes import *
from ctypes.wintypes import *
from socket import AF_INET
from socket import inet_ntoa, htons

TCP_TABLE_BASIC_LISTENER = 0
TCP_TABLE_BASIC_CONNECTIONS = 1
TCP_TABLE_BASIC_ALL = 2
TCP_TABLE_OWNER_PID_LISTENER = 3
TCP_TABLE_OWNER_PID_CONNECTIONS = 4
TCP_TABLE_OWNER_PID_ALL = 5
TCP_TABLE_OWNER_MODULE_LISTENER = 6
TCP_TABLE_OWNER_MODULE_CONNECTIONS = 7
TCP_TABLE_OWNER_MODULE_ALL = 8

NO_ERROR = 0
ERROR_INVALID_PARAMETER = 87
ERROR_INSUFFICIENT_BUFFER = 122

STATES = {
    1: "CLOSED",
    2: "LISTENING",
    3: "SYN_SENT",
    4: "SYN_RCVD",
    5: "ESTABLISHED",
    6: "FIN_WAIT",
    7: "FIN_WAIT_2",
    8: "CLOSE_WAIT",
    9: "CLOSING",
    10: "LAST_ACK",
    11: "TIME_WAIT",
    12: "DELETE_TCB",
}


# noinspection PyPep8Naming
class MIB_TCPROW_OWNER_PID(Structure):
    _fields_ = [
        ("dwState", DWORD),
        ("dwLocalAddr", DWORD),
        ("dwLocalPort", DWORD),
        ("dwRemoteAddr", DWORD),
        ("dwRemotePort", DWORD),
        ("dwOwningPid", DWORD)
    ]


# noinspection PyPep8Naming
class MIB_TCPTABLE_OWNER_PID(Structure):
    """
    MIB
    """
    # noinspection PyTypeChecker
    _fields_ = [
        ("dwNumEntries", DWORD),
        ("MIB_TCPROW_OWNER_PID", MIB_TCPROW_OWNER_PID * 0)
    ]


def format_ip(row):
    """
    Format an ip
    :param row: row
    :return object
    """
    return inet_ntoa(struct.pack("L", row.dwLocalAddr)), inet_ntoa(struct.pack("L", row.dwRemoteAddr))


# Get
_GetExtendedTcpTable = windll.iphlpapi.GetExtendedTcpTable


def get_netstat():
    """
    Get net stats as list of dict
    :return list of dict
    :rtype list
    """
    table_class = TCP_TABLE_OWNER_PID_ALL
    table_type = MIB_TCPTABLE_OWNER_PID
    row_type = MIB_TCPROW_OWNER_PID

    table = table_type()
    size = DWORD()
    order = True

    failure = _GetExtendedTcpTable(None, byref(size), order, AF_INET, table_class, 0)

    if failure == ERROR_INSUFFICIENT_BUFFER:
        resize(table, size.value)
        memset(byref(table), 0, sizeof(table))
        failure = _GetExtendedTcpTable(byref(table), byref(size), order, AF_INET, table_class, 0)

    if failure != NO_ERROR:
        raise Exception("_GetExtendedTcpTable failure, failure=%s" % failure)

    ptr_type = POINTER(row_type * table.dwNumEntries)
    tables = cast(getattr(table, row_type.__name__), ptr_type)[0]

    # Build
    ar_out = []
    for row in tables:
        local_addr, remote_addr = format_ip(row)
        ar_out.append(
            {
                "state": STATES.get(row.dwState, "UNKNOWN_STATE_%s" % (str(row.dwState))),
                "local_addr": local_addr,
                "local_port": htons(row.dwLocalPort),
                "remote_addr": remote_addr,
                "remote_port": htons(row.dwRemotePort),
                "pid": int(row.dwOwningPid)
            }
        )
    return ar_out
