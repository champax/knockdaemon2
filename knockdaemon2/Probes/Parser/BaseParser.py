"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2021 Laurent Labatut / Laurent Champagnac
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

import glob
import logging
import os

from pysolbase.SolBase import SolBase

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class BaseParser(KnockProbe):
    """
    Base parser
    """

    def __init__(self, file_mask=None, pos_file=None, kvc=None):
        """
        Init
        :param file_mask: str
        :type file_mask: str
        :param pos_file: str
        :type pos_file! str
        :param kvc: callback
        """

        KnockProbe.__init__(self)

        # Stats : line
        self.line_parsed = 0
        self.line_parsed_ok = 0
        self.line_parsed_failed = 0
        self.line_parsed_skipped = 0

        # Last parse time
        self.last_parse_time_ms = 0

        # Current position, current file
        self.file_cur_pos = 0
        self.file_cur_name = ""

        # Members
        self.file_mask = file_mask
        self.pos_file = pos_file
        self.kvc = kvc
        self.notify_kvc = None

        logger.info("Starting, file_mask=%s, pos_file=%s", self.file_mask, self.pos_file)
        self.load_position()

    def init_from_config(self, k, d_yaml_config, d):
        """
        Initialize from configuration
        :param k: str
        :type k: str
        :param d_yaml_config: full conf
        :type d_yaml_config: d
        :param d: local conf
        :type d: dict
        """

        # Base
        KnockProbe.init_from_config(self, k, d_yaml_config, d)

        # Go
        self.file_mask = d["file_mask"]
        self.pos_file = d["pos_file"]

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Execute a probe.
        """

        file_found = False
        try:
            file_found = self.parse_file()
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            raise
        finally:
            if file_found:
                self.write_position()

    def load_position(self):
        """
        Load position from file
        """

        try:
            if os.path.exists(self.pos_file):
                for line in open(self.pos_file):
                    # Format : key=value\n

                    ar = line.replace("\n", "").split("=")
                    if ar[0] == "file":
                        self.file_cur_name = ar[1]
                    elif ar[0] == "pos":
                        self.file_cur_pos = int(ar[1])
                    else:
                        raise Exception("Invalid buffer={0}".format(line))

                logger.info("Position loaded from file, file_cur_name=%s, file_cur_pos=%s",
                            self.file_cur_name,
                            self.file_cur_pos)
            else:
                logger.info("Position file not exists, reverting to default")
                self.file_cur_name = None
                self.file_cur_pos = 0
        except Exception as e:
            logger.warn("Exception while loading position file, reverting to default, ex=%s",
                        SolBase.extostr(e))
            self.file_cur_name = None
            self.file_cur_pos = 0

    def write_position(self):
        """
        Write
        """

        f = None
        try:
            buf = "file={0}\npos={1}\n".format(self.file_cur_name, self.file_cur_pos)
            f = open(self.pos_file, "w")
            f.write(buf)
        finally:
            if f is not None:
                f.close()

    def parse_file(self):
        """
        Parse file
        """

        ms_start = SolBase.mscurrent()
        try:
            # Before parsing
            self.on_file_pre_parsing()

            # Get the newest file using the mask
            file_time = None
            file_to_parse = None
            for fileName in glob.glob(self.file_mask):
                if file_time is None:
                    file_time = os.path.getctime(fileName)
                    file_to_parse = fileName
                else:
                    cur_time = os.path.getctime(fileName)
                    if file_time < cur_time:
                        file_time = cur_time
                        file_to_parse = fileName

            # No file ?
            if file_to_parse is None:
                # No file => exit
                return False

            # Check
            if self.file_cur_name != file_to_parse:
                # File change => Reset
                self.file_cur_name = file_to_parse
                self.file_cur_pos = 0

            # Parse
            self.file_cur_pos = BaseParser.parse_file_static(
                self.file_cur_name, self.parse_line, self.file_cur_pos)

            # Ms
            self.last_parse_time_ms = SolBase.msdiff(ms_start)

            # Post
            self.on_file_post_parsing()

            return True

        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            raise

    def parse_line(self, line_buffer):
        """
        Parse a file line by line.
        :param line_buffer: Line buffer
        :type line_buffer: str
        """

        try:
            # Stat
            self.line_parsed += 1

            if len(line_buffer) == 0:
                self.line_parsed_skipped += 1
                return

            # Try parse
            if self.on_file_parse_line(line_buffer):
                # Success
                self.line_parsed_ok += 1
        except Exception as e:
            # Failed
            logger.warn("Ex=%s, buffer=%s", SolBase.extostr(e), line_buffer)
            self.line_parsed_failed += 1
        finally:
            pass

    # =======================
    # TOOLS
    # =======================

    # noinspection PyMethodMayBeStatic
    def fix_dict(self, d, key):
        """
        Fix hash
        :param d: Hash
        :type d: dict
        :param key: Key
        :type key: str
        """

        if key not in d:
            d[key] = 0

    # noinspection PyMethodMayBeStatic
    def fill_dict(self, d, key, value, operator):
        """
        Fill hash
        :param d: Hash
        :type d: dict
        :param key: Key
        :type key: str
        :param value: Value
        :type value: int
        :param operator: Operator
        :type operator: str
        :return:
        :rtype:
        """

        # Not hashed : hash and exit
        if key not in d:
            d[key] = value
            return

        # Apply operator
        cur_val = d[key]
        if operator == "sum":
            new_val = cur_val + value
        elif operator == "min":
            new_val = min(cur_val, value)
        elif operator == "max":
            new_val = max(cur_val, value)
        else:
            raise Exception("Invalid operator={0}".format(operator))

        # Update
        d[key] = new_val

    # =======================
    # HIGHER LEVEL
    # =======================

    def on_file_pre_parsing(self):
        """
        Called BEFORE the file is parsed.
        """
        raise Exception("Must be overriden")

    def on_file_post_parsing(self):
        """
        Called after a file has been parsed
        """
        raise Exception("Must be overriden")

    def on_file_parse_line(self, buf):
        """
        Called when a line buffer has to be parsed
        :param buf: Buffer
        :type buf: str
        :return Bool (True : Success, False : Failed)
        :rtype bool
        """
        raise Exception("Must be overriden")

    # =======================
    # PARSING
    # =======================

    @classmethod
    def parse_file_static(cls, file_full_path, line_processing_callback, seek_to_position=0):
        """
        Parse a file line by line.
        :param file_full_path: File full path.
        :type file_full_path: str
        :param line_processing_callback: Processing line callback (will receive lineBuffer)
        :param seek_to_position: Seek to specified position (if not possible, will revert to zero)
        :type seek_to_position: int
        :return File position after parsing
        :rtype int
        """

        f = None
        try:
            # Try to open
            f = open(file_full_path, 'r')

            # Seek ?
            if seek_to_position > 0:
                logger.debug("Seek to position=%s", seek_to_position)
                # Seek !
                f.seek(seek_to_position, os.SEEK_SET)
                # Check
                pos = f.tell()
                if pos != seek_to_position:
                    # Revert to head
                    logger.debug(
                        "Seek to position=%s : FAILED (mismatch), revert to header, pos=%s",
                        seek_to_position,
                        pos)
                    f.seek(0, os.SEEK_SET)
                elif pos > os.path.getsize(file_full_path):
                    # Revert to head
                    logger.debug(
                        "Seek to position=%s : FAILED (filelen reached), revert to header, pos=%s",
                        seek_to_position, pos)
                    f.seek(0, os.SEEK_SET)
                else:
                    logger.debug("Seek to position=%s : OK", seek_to_position)

            # Browse line
            for line in f:
                # Remove last \n if required
                try:
                    if line[len(line) - 1] == "\n":
                        line_processing_callback(line[:-1])
                    else:
                        # Callback
                        line_processing_callback(line)
                except Exception as e:
                    logger.warn("line_processing_callback exception, ex=%s, line=%s", e, line)
                    raise

            # Return position
            pos = f.tell()
            return pos
        except Exception as e:
            # Failed
            logger.warn("Ex=%s", e)
            raise
        finally:
            # Close
            if f:
                f.close()
