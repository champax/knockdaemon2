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

import gevent
from gevent.subprocess import Popen, PIPE
from pysolbase.SolBase import SolBase

logger = logging.getLogger(__name__)


class InvokeTimeout(Exception):
    """
    Invoke exception
    """

    pass


# noinspection PyClassHasNoInit
class ButcherTools:
    """
    Tools
    """

    HAS_BEEN_CALLED = False

    @classmethod
    def invoke(cls, cmd, timeout_ms=10000, shell=False):
        """
        Invoke a command line with timeout handling, sending back exit code, stdout & stderr buffers
        :param cmd: command line (will be splitted using ' ')
        :type cmd: str
        :param timeout_ms: timeout in millis (will return exit code -999 if it occurs)
        :type timeout_ms: int
        :param shell: bool
        :type shell: bool
        :return tuple (exit code, stdout, stderr)
        :rtype tuple
        """

        if shell:
            return cls._invoke_internal(cmd, timeout_ms, shell=shell)
        else:
            if cmd.find("|") >= 0:
                logger.error("Pipe not support in invoke, cmd=%s", cmd)
                raise Exception("Pipe not support in invoke")

            return cls._invoke_internal(cmd.split(' '), timeout_ms, shell=False)

    @classmethod
    def _invoke_internal(cls, ar_or_string, timeout_ms=10000, shell=False):
        """
        Invoke a command line with timeout handling, sending back exit code, stdout & stderr buffers
        :param ar_or_string: command line array, or str if shell=True
        :type ar_or_string: list, tuple, str
        :param timeout_ms: timeout in millis (will return exit code -999 if it occurs). Also return a -998 if an exception occurs.
        :type timeout_ms: int
        :param shell: bool
        :type shell: bool
        :return tuple (exit code, stdout, stderr)
        :rtype tuple
        """

        cls.HAS_BEEN_CALLED = True

        so = ""
        se = ""
        logger.info("invoke type=%s, ar_or_string=%s, timeout=%s", type(ar_or_string), ar_or_string, timeout_ms)

        ms = SolBase.mscurrent()
        p = None
        try:
            with gevent.Timeout(seconds=timeout_ms / 1000.0, exception=InvokeTimeout):
                if shell:
                    # Shell....
                    p = Popen(ar_or_string, stdout=PIPE, stderr=PIPE, shell=shell)
                else:
                    # No shell
                    p = Popen(ar_or_string, stdout=PIPE, stderr=PIPE, shell=shell)
                SolBase.sleep(0)

                so, se = p.communicate()
                SolBase.sleep(0)

                ret_code = p.returncode
                p = None
                return ret_code, so, se
        except InvokeTimeout:
            logger.warn("invoke timeout, ar_or_string=%s, ms=%s", ar_or_string, SolBase.msdiff(ms))
            return -999, so, se
        except Exception as e:
            logger.warn("Exception in invoke, ar_or_string=%s, ex=%s", ar_or_string, SolBase.extostr(e))
            return -998, so, se
        finally:
            # Kill if set
            if p:
                try:
                    p.kill()
                    del p
                except Exception as e:
                    logger.warn("Exception in kill, ar=%s, ex=%s", ar_or_string, SolBase.extostr(e))
