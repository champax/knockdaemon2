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
import logging
import ujson

logger = logging.getLogger(__name__)


def expect_disco(self, k, key, d_disco):
    """
    Expect discovery present
    :param self: self (must be a unittest.case.TestCase)
    :param k: knockdaemon2.Core.KnockManager.KnockManager
    :type k: knockdaemon2.Core.KnockManager.KnockManager
    :param key str
    :type key str
    :param d_disco: dict {"ID": "toto}
    :type d_disco: dict
    """

    count = 0
    # noinspection PyProtectedMember
    for cur_key, tu in k._superv_notify_disco_hash.iteritems():
        disco_key, ddict = tu
        if disco_key != key:
            continue

        # Check we have all
        if len(d_disco) != len(ddict):
            continue

        # Check key / values
        for k2, v2 in d_disco.iteritems():
            if k2 in ddict and ddict[k2] == v2:
                count += 1

    # Check
    # noinspection PyProtectedMember
    self.assertGreater(count, 0, msg="Disco not found, lookfor={0}, having={1}".format(d_disco, k._superv_notify_disco_hash))


def expect_value(self, k, key, value, operator, d_disco=None, cast_to_float=False, target_count=None):
    """
    Expect key to have value
    :param self: self (must be a unittest.case.TestCase)
    :param k: knockdaemon2.Core.KnockManager.KnockManager
    :type k: knockdaemon2.Core.KnockManager.KnockManager
    :param key str
    :type key str
    :param value str, int, float, None
    :type value str, int, float, None
    :param operator: str (eq, gte, lte, exists)
    :type operator str
    :param d_disco: disco dict {"FSNAME": "/"}
    :type d_disco: dict, None
    :param cast_to_float: bool
    :type cast_to_float bool
    :param target_count: None, int
    :param target_count: None, int
    """

    # LLA fix
    if isinstance(value, dict):
        value = ujson.dumps(value)

    hit = 0
    count = 0
    vlist = list()
    # noinspection PyProtectedMember
    for tu in k._superv_notify_value_list:
        cur_key = tu[0]
        k_d_disco = tu[1]
        v = tu[2]
        if cast_to_float:
            try:
                v = float(v)
            except ValueError:
                v = None

        if cur_key == key:
            hit += 1
            vlist.append(tu)

            # Look for d_disco
            disco_ok = False
            if d_disco:
                d_ok = 0

                for k2, v2 in d_disco.iteritems():
                    if k2 not in k_d_disco:
                        continue
                    elif k_d_disco[k2] != v2:
                        continue
                    else:
                        d_ok += 1

                if d_ok != len(d_disco):
                    logger.debug("Unable to match (d_ok), d_disco=%s, having tu=%s", d_disco, tu)
                elif len(d_disco) != len(k_d_disco):
                    logger.debug("Unable to match (len),  d_disco=%s, having tu=%s", d_disco, tu)
                else:
                    disco_ok = True
            else:
                disco_ok = True

            # Check
            if disco_ok:
                if operator == "eq":
                    if v == value:
                        count += 1
                elif operator == "gte":
                    v = float(v)
                    value = float(value)
                    if v >= value:
                        count += 1
                elif operator == "lte":
                    v = float(v)
                    value = float(value)
                    if v <= value:
                        count += 1
                elif operator == "exists":
                    count += 1

    if count == 0:
        self.assertEqual(True, False, msg="Key/Value not found, hit={0}, count={1}, ope={2}, {3}={4}, d_disco={5} vlist={6}".format(hit, count, operator, key, value, d_disco, vlist))

    # Go some, if target count is provided, check it
    if target_count:
        if count != target_count:
            self.assertEqual(True, False, msg="Key/Value target count not ok, hit={0}, count={1}, target={2} ope={3}, {4}={5}, d_disco={6} vlist={7}".format(hit, count, target_count, operator, key, value, d_disco, vlist))

    # Ok
    self.assertEqual(True, True, msg='%s %s %s' % (key, value, operator))


# noinspection PyProtectedMember
def _exec_helper(self, exec_class):
    """
    Exec helper
    """

    # Reset
    self.k._superv_notify_value_list = list()

    count = 0
    for p in self.k._probe_list:
        if isinstance(p, exec_class) or exec_class.__name__ == p.__class__.__name__:
            for k, v in self.conf_probe_override.iteritems():
                setattr(p, k, v)
            # Category must be set and no "undef"
            self.assertIsNotNone(p.category)
            self.assertGreater(len(p.category), 0)
            self.assertNotEqual(p.category, "undef")
            p.execute()
            count += 1
    self.assertGreater(count, 0)
    logger.info("Exec ok")

    for tu in self.k._superv_notify_value_list:
        logger.info("Having tu=%s", tu)

    for k, tu in self.k._superv_notify_disco_hash.iteritems():
        logger.info("Having disco, k=%s, tu=%s", k, tu)
