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
import re
from datetime import datetime

import pymongo

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class MongoStatDb(KnockProbe):
    """
    Probe
    """

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)

        self.strport = None
        self.database = None
        self.category = "/nosql/mongodb"

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Exec
        """

        for port, t in self.__getserverlist():
            if port == 27017:
                self.notify_discovery_n("knock.mongo.discovery", {"PORT": str(port)})
                self.getstat("127.0.0.1", port)

    def getstat(self, host, port):
        """
        Stat
        :param host:
        :param port:
        :return:
        """
        self.strport = str(port)

        try:
            mongo_connection = pymongo.MongoClient(host, port)
        except Exception as e:
            logger.exception(e)
            self.notify_value_n("knock.mongodb.server.ok", {"PORT": self.strport}, "0")
            return
        self.notify_value_n("knock.mongodb.server.ok", {"PORT": self.strport}, "0")
        mongo_db_handle = mongo_connection["admin"]

        # -----------------------------
        # Get DB list and cumulative DB info
        # -----------------------------
        db_list = mongo_connection.database_names()

        self.database = "all"
        self.recurse(mongo_db_handle.command("dbstats"), 'server.')

        for db in db_list:
            self.notify_discovery_n("knock.mongo.databases.db.discovery", {"DB": str(db)})

        for db in db_list:
            self.database = db
            currentdb = mongo_connection[db]
            self.recurse(mongo_db_handle.command("dbstats", db), 'db.')
            for coll in currentdb.collection_names():
                if coll == 'system.indexes':
                    continue

                self.notify_discovery_n("knock.mongo.databases.coll.discovery", {"COLL": db + "." + coll})

                for key, value in currentdb.command("collstats", str(coll)).items():
                    if key in ('count', 'storageSize', 'sharded'):
                        self.notify_value_n("knock.mongo.databases.coll." + key, {"COLL": db + "." + coll}, self.cleanvalue(value))

    # noinspection PyMethodMayBeStatic
    def __getserverlist(self):
        """
        LA DOC MARRAUD
        :return:
        """
        server_list = list()

        init_files = glob.glob('/etc/init.d/mongo*')
        logger.debug("initd files : %s", init_files)

        for initd in init_files:
            config_db = False
            port = 0
            shardsvr = False
            conf_file = None
            for conf_line in open(initd, 'r').readlines():
                if conf_line.startswith('CONF='):
                    conf_line = re.sub(' +', ' ', conf_line)
                    conf_file = conf_line[5:].strip()
                if conf_line.startswith('CONFIGDB='):
                    config_db = True
            logger.debug("file %s - conf_file %s - config_db %s" % (initd, conf_file, config_db))

            # Parse conf file
            if conf_file is not None:
                try:
                    for conf_line in open(conf_file).readlines():
                        if conf_line.startswith('port ='):
                            conf_line = re.sub(' +', ' ', conf_line)
                            port = int(conf_line[6:].strip())

                        if conf_line.startswith('shardsvr ='):
                            conf_line = re.sub(' +', ' ', conf_line)
                            shardsvr = conf_line[10:].strip()
                except IOError as e:
                    logger.info("Cannot read %s : %s " % (conf_file, e.message))
                except Exception as err:
                    logger.exception(err)
            if port == 0:
                port = 27017

            if not shardsvr and config_db:
                t = "config"
            elif shardsvr and not config_db:
                t = "data"
            elif shardsvr and config_db:
                t = "mongos"
            else:
                t = "unknown"

            server_list.append((port, t))
            logger.debug(" %s file - conf %s - port %s - shard %s - confiDb %s - type %s" % (
                initd, conf_file, port, shardsvr, config_db, t))
        return server_list

    # noinspection PyMethodMayBeStatic
    def cleanvalue(self, v):
        """
        :param v: str
        """

        if isinstance(v, datetime):
            return int(v.strftime('%s'))

        return v

    def recurse(self, dictionary, subkey):
        """
        Recurse
        :param dictionary:
        :param subkey:
        :return:
        """
        for key, value in dictionary.items():
            if key == "raw":
                continue
            if isinstance(value, dict):
                self.recurse(value, subkey + key + "_")
            else:
                if self.database == 'all':
                    self.notify_value_n("knock.mongo.databases." + subkey + key, None, self.cleanvalue(value))
                else:
                    self.notify_value_n("knock.mongo.databases." + subkey + key, {"DB": self.database}, self.cleanvalue(value))
