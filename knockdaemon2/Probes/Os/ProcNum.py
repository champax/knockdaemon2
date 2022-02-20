"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2022 Laurent Labatut / Laurent Champagnac
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
from os import listdir
from os.path import isdir, join

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


def read_file_line(file_name):
    """
    Read file line
    :param file_name: str
    :type file_name: str
    :return: str
    :rtype str
    """
    with open(file_name) as f:
        return f.readline()


def is_dir(path):
    """
    Is dir
    :param path: str
    :rtype path: str
    :return: bool
    :rtype bool
    """
    return isdir(path)


def get_proc_list():
    """
    Get proc list
    :return: list of str
    :rtype list
    """

    return listdir("/proc")


class NumberOfProcesses(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self, linux_support=True, windows_support=False)

        self.category = "/os/misc"

    def _execute_linux(self):
        """
        Exec
        """

        # This is in fact the number of running processes
        self.notify_value_n("k.os.processes.total", None, self._get_process_count())

    @classmethod
    def _get_process_count(cls):
        """
        Get
        :return:
        """
        result = 0
        for name in get_proc_list():
            path = join("/proc", name)
            if is_dir(path) and name.isdigit():
                if len(read_file_line(path + "/cmdline")) > 0:
                    result += 1
        return result
