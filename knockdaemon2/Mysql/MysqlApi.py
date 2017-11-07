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
from contextlib import closing
import logging

import pymysql

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


class MysqlApi(object):
    """
    Mysql Api
    """

    # UNIX or HOST (not both), HOST has precedence
    
    SAMPLE_CONFIG_DICT = {
        "host": "127.0.0.1",
        "unix": "/var/run/mysqld/mysqld.sock",
        "port": 3306,
        "database": "mysql",
        "user": "your_account",
        "password": "your_password",
        "autocommit": True,
        "pool_name": "p1",  # not used
        "pool_size": 5  # not used
    }

    @classmethod
    def get_connection(cls, conf_dict):
        """
        Get a connection
        :param conf_dict: dict
        :type conf_dict: dict
        :return: pymysql.connections.Connection
        :rtype: pymysql.connections.Connection
        """

        # DOC :
        #     def __init__(self, host=None, user=None, password="",
        #          database=None, port=3306, unix_socket=None,
        #          charset='', sql_mode=None,
        #          read_default_file=None, conv=decoders, use_unicode=None,
        #          client_flag=0, cursorclass=Cursor, init_command=None,
        #          connect_timeout=None, ssl=None, read_default_group=None,
        #          compress=None, named_pipe=None, no_delay=None,
        #          autocommit=False, db=None, passwd=None, local_infile=False,
        #          max_allowed_packet=16*1024*1024, defer_connect=False,
        #          auth_plugin_map={}):

        logger.debug("mysql connect, server=%s:%s, unix=%s, user=%s, pwd=%s, db=%s",
                     conf_dict.get("host"), conf_dict.get("port"), conf_dict.get("unix"),
                     conf_dict.get("user"), conf_dict.get("password"),
                     conf_dict.get("database")
                     )

        # Host
        h = conf_dict.get("host")
        if h:
            c = pymysql.connect(
                host=conf_dict["host"],
                port=int(conf_dict["port"]),

                db=conf_dict["database"],

                user=conf_dict["user"],
                password=conf_dict["password"],

                autocommit=conf_dict["autocommit"],

                cursorclass=pymysql.cursors.DictCursor
            )
            return c

        # Unix
        h = conf_dict.get("unix")
        if h:
            c = pymysql.connect(
                unix_socket=conf_dict["unix"],

                db=conf_dict["database"],

                user=conf_dict["user"],
                password=conf_dict["password"],

                autocommit=conf_dict["autocommit"],

                cursorclass=pymysql.cursors.DictCursor
            )
            return c

    @classmethod
    def get_pool_name(cls, mysql_conf):
        """
        Get pool name
        :param mysql_conf: dict
        :type mysql_conf: d
        :return: str
        :rtype str
        """

        return "{0}_{1}_{2}_{3}".format(
            mysql_conf.get("host"),
            mysql_conf.get("port"),
            mysql_conf.get("user"),
            mysql_conf.get("database")
        )

    @classmethod
    def fix_type(cls, data):
        """
        Fix type
        :param data: data
        """
        if isinstance(data, bytearray):
            return data.decode("utf-8")
        else:
            return data

    @classmethod
    def exec_0(cls, conf_dict, statement):
        """
        Execute a sql statement, returning nothing.
        :param conf_dict: configuration dict
        :type conf_dict: dict
        :param statement: statement to execute
        :type statement: str
        """

        with closing(MysqlApi.get_connection(conf_dict)) as cnx:
            with closing(cnx.cursor()) as cur:
                cur.execute(statement)

    @classmethod
    def exec_n(cls, conf_dict, statement, fix_types=True):
        """
        Execute a sql statement, returning 0..N rows
        :param conf_dict: configuration dict
        :type conf_dict: dict
        :param statement: statement to execute
        :type statement: str
        :param fix_types: If true, fix data type
        :type fix_types: bool
        :return list of dict.
        :rtype list
        """

        with closing(MysqlApi.get_connection(conf_dict)) as cnx:
            with closing(cnx.cursor()) as cur:
                cur.execute(statement)
                rows = cur.fetchall()
                for row in rows:
                    logger.debug("row=%s", row)
                    for k, v in row.iteritems():
                        logger.debug("k=%s, %s, %s", k, type(v), v)
                        if fix_types:
                            row[k] = MysqlApi.fix_type(v)
                return rows

    @classmethod
    def exec_1(cls, conf_dict, statement, fix_types=True):
        """
        Execute a sql statement, returning 1 row.
        Method will fail if 1 row in not returned.
        :param conf_dict: configuration dict
        :type conf_dict: dict
        :param statement: statement to execute
        :type statement: str
        :param fix_types: If true, fix data type
        :type fix_types: bool
        :return dict
        :rtype dict
        """

        with closing(MysqlApi.get_connection(conf_dict)) as cnx:
            with closing(cnx.cursor()) as cur:
                cur.execute(statement)
                rows = cur.fetchall()
                for row in rows:
                    logger.debug("row=%s", row)
                    for k, v in row.iteritems():
                        logger.debug("k=%s, %s, %s", k, type(v), v)
                        if fix_types:
                            row[k] = MysqlApi.fix_type(v)
                if len(rows) != 1:
                    raise Exception("Invalid row len, expecting 1, having={0}".format(len(rows)))
                return rows[0]

    @classmethod
    def exec_01(cls, conf_dict, statement, fix_types=True):
        """
        Execute a sql statement, returning 0 or 1 row.
        Method will fail if 0 or 1 row in not returned.
        :param conf_dict: configuration dict
        :type conf_dict: dict
        :param statement: statement to execute
        :type statement: str
        :param fix_types: If true, fix data type
        :type fix_types: bool
        :return dict, None
        :rtype dict, None
        """

        with closing(MysqlApi.get_connection(conf_dict)) as cnx:
            with closing(cnx.cursor()) as cur:
                cur.execute(statement)
                rows = cur.fetchall()
                for row in rows:
                    logger.debug("row=%s", row)
                    for k, v in row.iteritems():
                        logger.debug("k=%s, %s, %s", k, type(v), v)
                        if fix_types:
                            row[k] = MysqlApi.fix_type(v)
                if len(rows) == 0:
                    return None
                elif len(rows) != 1:
                    raise Exception("Invalid row len, expecting 1, having={0}".format(len(rows)))
                else:
                    return rows[0]

    @classmethod
    def multi_n(cls, conf_dict, statement, ):
        """
        Execute multiple sql statement
        Method will fail if 0 or 1 row in not returned.
        :type conf_dict: dict
        :param statement: statement to execute
        :type statement: str
        :return None
        :rtype None
        """

        with closing(MysqlApi.get_connection(conf_dict)) as cnx:
            with closing(cnx.cursor()) as cur:
                cur.execute(statement)
                rows = cur.fetchall()
                for row in rows:
                    logger.debug("row=%s", row)
