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
from pythonsol.SolBase import SolBase


class HttpResponse(object):
    """
    Http response
    """

    def __init__(self):
        """
        Const
        """

        # Related request
        self.http_request = None

        # Exception while processing
        self.exception = None

        # Time taken in ms
        self.elapsed_ms = None

        # Class used for internal http processing
        self.http_implementation = None

        # Response buffer
        self.buffer = None

        # Response headers
        self.headers = {
            'User-Agent': 'unittest',
        }

        # Status code (integer)
        self.status_code = 0

        # Content-length
        self.content_length = 0

    def __str__(self):
        """
        To string override
        :return: A string
        :rtype string
        """

        return "hresp:st={0}*cl={1}*impl={2}*ms={3}*h={4}*req.uri={5}*req.h={6}*ex={7}".format(
            self.status_code,
            self.content_length,
            self.http_implementation,
            self.elapsed_ms,
            self.headers,
            self.http_request.uri,
            self.http_request.headers,
            SolBase.extostr(self.exception) if self.exception else "None",
        )
