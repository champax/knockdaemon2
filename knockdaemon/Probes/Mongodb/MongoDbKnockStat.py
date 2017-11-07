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

from datetime import datetime
import logging
import pymongo
from knockdaemon.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class MongoDbKnockStat(KnockProbe):
    """
    Doc
    """

    __MONGO_SERVER = "mongoserver"
    __MONGO_PORT = "port"

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)

        self.server = None
        self.port = None
        self.database = None
        self.category = "/nosql/mongodb"

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
        self.server = config_parser[section_name][MongoDbKnockStat.__MONGO_SERVER]
        self.port = config_parser[section_name][MongoDbKnockStat.__MONGO_PORT]

    def _execute_windows(self):
        """
        Execute a probe (windows)
        """
        # Just call base, not supported
        KnockProbe._execute_windows(self)

    def _execute_linux(self):
        """
        Doc
        :return:
        """

        logger.info("Mongo server=%s, port=%s", self.server, self.port)

        self.getstat(self.server, self.port)

    def getstat(self, host, port):
        """
        Doc
        :param host: Doc
        :param port: Doc
        """

        try:
            # Connect
            mongo_client = pymongo.MongoClient(host, port)

            # Get DB list and cumulative DB info
            database_list = mongo_client.database_names()

            # For each db
            for db in database_list:
                # Current db
                self.database = db

                # Get connection
                currentdb = mongo_client[db]

                # Get stats (database)
                self.recurse(currentdb.command("dbstats", db), 'database.')

                # For each collection : get stats (collections)
                for coll in currentdb.collection_names():
                    collection_dict = dict()
                    collection_dict['{#COLL}'] = str("%s.%s" % (db, coll))

                    if coll == 'system.indexes':
                        continue

                    # Notify disco
                    self.notify_discovery_n("knock.mongodb_knockstat.collection.discovery", {"COLL": db + "." + coll})
                    self.notify_discovery_n("knock.mongodb_knockstat.database.discovery", {"DB": str(db)})

                    # Notify values
                    for key, value in currentdb.command("collstats", str(coll)).items():
                        if key in ('count', 'storageSize', 'sharded'):
                            self.notify_value_n("knock.mongodb_knockstat.collection." + key, {"COLL": db + "." + coll}, self.cleanvalue(value))
                        if key == 'count':
                            # Hack for count per sec
                            self.notify_value_n("knock.mongodb_knockstat.collection." + key + "_persec", {"COLL": db + "." + coll}, self.cleanvalue(value))

        except Exception as e:
            logger.exception(e)

    # noinspection PyMethodMayBeStatic
    def cleanvalue(self, v):
        """
        :param v: Doc
        """
        if isinstance(v, datetime):
            return int(v.strftime('%s'))

        return v

    def recurse(self, dictionary, subkey):
        """
        Doc
        :param dictionary: Doc
        :param subkey: Doc
        """
        for key, value in dictionary.items():
            if key not in ('count', 'storageSize', 'sharded'):
                continue
            if key == "raw":
                continue
            if isinstance(value, dict):
                self.recurse(value, subkey + key + "_")
            else:
                if self.database == 'all':
                    self.notify_value_n("knock.mongodb_knockstat." + subkey + key, None, self.cleanvalue(value))
                else:
                    self.notify_value_n("knock.mongodb_knockstat." + subkey + key, {"DB": self.database}, self.cleanvalue(value))
