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

import glob
import json
import logging
import re
from collections import defaultdict
from datetime import datetime

import dateutil
import pymongo
import yaml
from dateutil.parser import parser
from pymongo.errors import OperationFailure
from pysolbase.SolBase import SolBase
from yaml import SafeLoader

from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class MongoDbStat(KnockProbe):
    """
    Probe
    """
    __MONGO_SERVER = "127.0.0.1"
    __MONGOD_PORT = 2001
    __MONGOS_PORT = 2707
    __MONGOC_PORT = 2100

    # key to None OR callable (used by clean_value)
    KEYS = {
        "metrics_commands_updateUser_failed": None,
        "metrics_commands_updateUser_total": None,
        "metrics_commands_dropRole_failed": None,
        "metrics_commands_dropRole_total": None,
        "metrics_commands_renameCollection_failed": None,
        "metrics_commands_renameCollection_total": None,
        "metrics_commands_planCacheSetFilter_failed": None,
        "metrics_commands_planCacheSetFilter_total": None,
        "metrics_commands_top_failed": None,
        "metrics_commands_top_total": None,
        "metrics_commands_usersInfo_failed": None,
        "metrics_commands_usersInfo_total": None,
        "metrics_commands_applyOps_failed": None,
        "metrics_commands_applyOps_total": None,
        "metrics_commands_setParameter_failed": None,
        "metrics_commands_setParameter_total": None,
        "metrics_commands_find_failed": None,
        "metrics_commands_find_total": None,
        "metrics_commands_compact_failed": None,
        "metrics_commands_compact_total": None,
        "metrics_commands_createIndexes_failed": None,
        "metrics_commands_createIndexes_total": None,
        "metrics_commands_handshake_failed": None,
        "metrics_commands_handshake_total": None,
        "metrics_commands_group_failed": None,
        "metrics_commands_group_total": None,
        "metrics_commands_moveChunk_failed": None,
        "metrics_commands_moveChunk_total": None,
        "metrics_commands__mergeAuthzCollections_failed": None,
        "metrics_commands__mergeAuthzCollections_total": None,
        "metrics_commands_explain_failed": None,
        "metrics_commands_explain_total": None,
        "metrics_commands__migrateClone_failed": None,
        "metrics_commands__migrateClone_total": None,
        "metrics_commands_checkShardingIndex_failed": None,
        "metrics_commands_checkShardingIndex_total": None,
        "metrics_commands_logRotate_failed": None,
        "metrics_commands_logRotate_total": None,
        "metrics_commands_getPrevError_failed": None,
        "metrics_commands_getPrevError_total": None,
        "metrics_commands_replSetGetStatus_failed": None,
        "metrics_commands_replSetGetStatus_total": None,
        "metrics_commands_grantRolesToUser_failed": None,
        "metrics_commands_grantRolesToUser_total": None,
        "metrics_commands_shardConnPoolStats_failed": None,
        "metrics_commands_shardConnPoolStats_total": None,
        "metrics_commands_diagLogging_failed": None,
        "metrics_commands_diagLogging_total": None,
        "metrics_commands_splitChunk_failed": None,
        "metrics_commands_splitChunk_total": None,
        "metrics_commands_planCacheClear_failed": None,
        "metrics_commands_planCacheClear_total": None,
        "metrics_commands_getCmdLineOpts_failed": None,
        "metrics_commands_getCmdLineOpts_total": None,
        "metrics_commands_insert_failed": None,
        "metrics_commands_insert_total": None,
        "metrics_commands_replSetInitiate_failed": None,
        "metrics_commands_replSetInitiate_total": None,
        "metrics_commands_replSetGetConfig_failed": None,
        "metrics_commands_replSetGetConfig_total": None,
        "metrics_commands_fsync_failed": None,
        "metrics_commands_fsync_total": None,
        "metrics_commands_appendOplogNote_failed": None,
        "metrics_commands_appendOplogNote_total": None,
        "metrics_commands_drop_failed": None,
        "metrics_commands_drop_total": None,
        "metrics_commands_mapreduce_shardedfinish_failed": None,
        "metrics_commands_mapreduce_shardedfinish_total": None,
        "metrics_commands__recvChunkAbort_failed": None,
        "metrics_commands__recvChunkAbort_total": None,
        "metrics_commands_replSetSyncFrom_failed": None,
        "metrics_commands_replSetSyncFrom_total": None,
        "metrics_commands_connectionStatus_failed": None,
        "metrics_commands_connectionStatus_total": None,
        "metrics_commands_touch_failed": None,
        "metrics_commands_touch_total": None,
        "metrics_commands__recvChunkStatus_failed": None,
        "metrics_commands__recvChunkStatus_total": None,
        "metrics_commands_copydbgetnonce_failed": None,
        "metrics_commands_copydbgetnonce_total": None,
        "metrics_commands_planCacheListPlans_failed": None,
        "metrics_commands_planCacheListPlans_total": None,
        "metrics_commands_dataSize_failed": None,
        "metrics_commands_dataSize_total": None,
        "metrics_commands_dbHash_failed": None,
        "metrics_commands_dbHash_total": None,
        "metrics_commands_medianKey_failed": None,
        "metrics_commands_medianKey_total": None,
        "metrics_commands__recvChunkStart_failed": None,
        "metrics_commands__recvChunkStart_total": None,
        "metrics_commands_authenticate_failed": None,
        "metrics_commands_authenticate_total": None,
        "metrics_commands_cursorInfo_failed": None,
        "metrics_commands_cursorInfo_total": None,
        "metrics_commands_revokeRolesFromRole_failed": None,
        "metrics_commands_revokeRolesFromRole_total": None,
        "metrics_commands_grantPrivilegesToRole_failed": None,
        "metrics_commands_grantPrivilegesToRole_total": None,
        "metrics_commands_geoNear_failed": None,
        "metrics_commands_geoNear_total": None,
        "metrics_commands_replSetFresh_failed": None,
        "metrics_commands_replSetFresh_total": None,
        "metrics_commands_planCacheClearFilters_failed": None,
        "metrics_commands_planCacheClearFilters_total": None,
        "metrics_commands_getParameter_failed": None,
        "metrics_commands_getParameter_total": None,
        "metrics_commands_dropIndexes_failed": None,
        "metrics_commands_dropIndexes_total": None,
        "metrics_commands_listDatabases_failed": None,
        "metrics_commands_listDatabases_total": None,
        "metrics_commands_collStats_failed": None,
        "metrics_commands_collStats_total": None,
        "metrics_commands_hostInfo_failed": None,
        "metrics_commands_hostInfo_total": None,
        "metrics_commands_getShardVersion_failed": None,
        "metrics_commands_getShardVersion_total": None,
        "metrics_commands_cloneCollection_failed": None,
        "metrics_commands_cloneCollection_total": None,
        "metrics_commands_dropDatabase_failed": None,
        "metrics_commands_dropDatabase_total": None,
        "metrics_commands_update_failed": None,
        "metrics_commands_update_total": None,
        "metrics_commands_logout_failed": None,
        "metrics_commands_logout_total": None,
        "metrics_commands__transferMods_failed": None,
        "metrics_commands__transferMods_total": None,
        "metrics_commands_isMaster_failed": None,
        "metrics_commands_isMaster_total": None,
        "metrics_commands_getShardMap_failed": None,
        "metrics_commands_getShardMap_total": None,
        "metrics_commands_shardingState_failed": None,
        "metrics_commands_shardingState_total": None,
        "metrics_commands_replSetReconfig_failed": None,
        "metrics_commands_replSetReconfig_total": None,
        "metrics_commands_getLog_failed": None,
        "metrics_commands_getLog_total": None,
        "metrics_commands_connPoolSync_failed": None,
        "metrics_commands_connPoolSync_total": None,
        "metrics_commands_revokePrivilegesFromRole_failed": None,
        "metrics_commands_revokePrivilegesFromRole_total": None,
        "metrics_commands_replSetMaintenance_failed": None,
        "metrics_commands_replSetMaintenance_total": None,
        "metrics_commands_serverStatus_failed": None,
        "metrics_commands_serverStatus_total": None,
        "metrics_commands_replSetStepDown_failed": None,
        "metrics_commands_replSetStepDown_total": None,
        "metrics_commands_features_failed": None,
        "metrics_commands_features_total": None,
        "metrics_commands_connPoolStats_failed": None,
        "metrics_commands_connPoolStats_total": None,
        "metrics_commands_planCacheListQueryShapes_failed": None,
        "metrics_commands_planCacheListQueryShapes_total": None,
        "metrics_commands_copydb_failed": None,
        "metrics_commands_copydb_total": None,
        "metrics_commands_forceerror_failed": None,
        "metrics_commands_forceerror_total": None,
        "metrics_commands_planCacheListFilters_failed": None,
        "metrics_commands_planCacheListFilters_total": None,
        "metrics_commands_shutdown_failed": None,
        "metrics_commands_shutdown_total": None,
        "metrics_commands_listCollections_failed": None,
        "metrics_commands_listCollections_total": None,
        "metrics_commands_currentOpCtx_failed": None,
        "metrics_commands_currentOpCtx_total": None,
        "metrics_commands__getUserCacheGeneration_failed": None,
        "metrics_commands__getUserCacheGeneration_total": None,
        "metrics_commands_validate_failed": None,
        "metrics_commands_validate_total": None,
        "metrics_commands_repairDatabase_failed": None,
        "metrics_commands_repairDatabase_total": None,
        "metrics_commands_saslStart_failed": None,
        "metrics_commands_saslStart_total": None,
        "metrics_commands_distinct_failed": None,
        "metrics_commands_distinct_total": None,
        "metrics_commands_create_failed": None,
        "metrics_commands_create_total": None,
        "metrics_commands_splitVector_failed": None,
        "metrics_commands_splitVector_total": None,
        "metrics_commands_copydbsaslstart_failed": None,
        "metrics_commands_copydbsaslstart_total": None,
        "metrics_commands_dropAllRolesFromDatabase_failed": None,
        "metrics_commands_dropAllRolesFromDatabase_total": None,
        "metrics_commands_invalidateUserCache_failed": None,
        "metrics_commands_invalidateUserCache_total": None,
        "metrics_commands_whatsmyuri_failed": None,
        "metrics_commands_whatsmyuri_total": None,
        "metrics_commands_geoSearch_failed": None,
        "metrics_commands_geoSearch_total": None,
        "metrics_commands_updateRole_failed": None,
        "metrics_commands_updateRole_total": None,
        "metrics_commands_reIndex_failed": None,
        "metrics_commands_reIndex_total": None,
        "metrics_commands__isSelf_failed": None,
        "metrics_commands__isSelf_total": None,
        "metrics_commands_unsetSharding_failed": None,
        "metrics_commands_unsetSharding_total": None,
        "metrics_commands_getnonce_failed": None,
        "metrics_commands_getnonce_total": None,
        "metrics_commands_listIndexes_failed": None,
        "metrics_commands_listIndexes_total": None,
        "metrics_commands_collMod_failed": None,
        "metrics_commands_collMod_total": None,
        "metrics_commands_count_failed": None,
        "metrics_commands_count_total": None,
        "metrics_commands_filemd5_failed": None,
        "metrics_commands_filemd5_total": None,
        "metrics_commands_setShardVersion_failed": None,
        "metrics_commands_setShardVersion_total": None,
        "metrics_commands_parallelCollectionScan_failed": None,
        "metrics_commands_parallelCollectionScan_total": None,
        "metrics_commands_writebacklisten_failed": None,
        "metrics_commands_writebacklisten_total": None,
        "metrics_commands_delete_failed": None,
        "metrics_commands_delete_total": None,
        "metrics_commands_rolesInfo_failed": None,
        "metrics_commands_rolesInfo_total": None,
        "metrics_commands_replSetGetRBID_failed": None,
        "metrics_commands_replSetGetRBID_total": None,
        "metrics_commands_dropUser_failed": None,
        "metrics_commands_dropUser_total": None,
        "metrics_commands_resync_failed": None,
        "metrics_commands_resync_total": None,
        "metrics_commands_saslContinue_failed": None,
        "metrics_commands_saslContinue_total": None,
        "metrics_commands_repairCursor_failed": None,
        "metrics_commands_repairCursor_total": None,
        "metrics_commands_driverOIDTest_failed": None,
        "metrics_commands_driverOIDTest_total": None,
        "metrics_commands_getLastError_failed": None,
        "metrics_commands_getLastError_total": None,
        "metrics_commands_convertToCapped_failed": None,
        "metrics_commands_convertToCapped_total": None,
        "metrics_commands_replSetHeartbeat_failed": None,
        "metrics_commands_replSetHeartbeat_total": None,
        "metrics_commands_ping_failed": None,
        "metrics_commands_ping_total": None,
        "metrics_commands_availableQueryOptions_failed": None,
        "metrics_commands_availableQueryOptions_total": None,
        "metrics_commands_dropAllUsersFromDatabase_failed": None,
        "metrics_commands_dropAllUsersFromDatabase_total": None,
        "metrics_commands_cloneCollectionAsCapped_failed": None,
        "metrics_commands_cloneCollectionAsCapped_total": None,
        "metrics_commands_listCommands_failed": None,
        "metrics_commands_listCommands_total": None,
        "metrics_commands_profile_failed": None,
        "metrics_commands_profile_total": None,
        "metrics_commands_replSetElect_failed": None,
        "metrics_commands_replSetElect_total": None,
        "metrics_commands_cleanupOrphaned_failed": None,
        "metrics_commands_cleanupOrphaned_total": None,
        "metrics_commands_replSetFreeze_failed": None,
        "metrics_commands_replSetFreeze_total": None,
        "metrics_commands_clone_failed": None,
        "metrics_commands_clone_total": None,
        "metrics_commands_mapReduce_failed": None,
        "metrics_commands_mapReduce_total": None,
        "metrics_commands_eval_failed": None,
        "metrics_commands_eval_total": None,
        "metrics_commands_createUser_failed": None,
        "metrics_commands_createUser_total": None,
        "metrics_commands_aggregate_failed": None,
        "metrics_commands_aggregate_total": None,
        "metrics_commands_replSetUpdatePosition_failed": None,
        "metrics_commands_replSetUpdatePosition_total": None,
        "metrics_commands_mergeChunks_failed": None,
        "metrics_commands_mergeChunks_total": None,
        "metrics_commands_revokeRolesFromUser_failed": None,
        "metrics_commands_revokeRolesFromUser_total": None,
        "metrics_commands_createRole_failed": None,
        "metrics_commands_createRole_total": None,
        "metrics_commands_authSchemaUpgrade_failed": None,
        "metrics_commands_authSchemaUpgrade_total": None,
        "metrics_commands_findAndModify_failed": None,
        "metrics_commands_findAndModify_total": None,
        "metrics_commands_dbStats_failed": None,
        "metrics_commands_dbStats_total": None,
        "metrics_commands__recvChunkCommit_failed": None,
        "metrics_commands__recvChunkCommit_total": None,
        "metrics_commands_grantRolesToRole_failed": None,
        "metrics_commands_grantRolesToRole_total": None,
        "metrics_commands_buildInfo_failed": None,
        "metrics_commands_buildInfo_total": None,
        "metrics_commands_resetError_failed": None,
        "metrics_commands_resetError_total": None,
        "metrics_storage_freelist_search_requests": None,
        "metrics_storage_freelist_search_scanned": None,
        "metrics_storage_freelist_search_bucketExhausted": None,
        "metrics_getLastError_wtime_num": None,
        "metrics_getLastError_wtime_totalMillis": None,
        "metrics_getLastError_wtimeouts": None,
        "metrics_queryExecutor_scanned": None,
        "metrics_queryExecutor_scannedObjects": None,
        "metrics_cursor_timedOut": None,
        "metrics_cursor_open_pinned": None,
        "metrics_cursor_open_total": None,
        "metrics_cursor_open_noTimeout": None,
        "metrics_record_moves": None,
        "metrics_repl_buffer_count": None,
        "metrics_repl_buffer_sizeBytes": None,
        "metrics_repl_buffer_maxSizeBytes": None,
        "metrics_repl_apply_batches_num": None,
        "metrics_repl_apply_batches_totalMillis": None,
        "metrics_repl_apply_ops": None,
        "metrics_repl_preload_docs_num": None,
        "metrics_repl_preload_docs_totalMillis": None,
        "metrics_repl_preload_indexes_num": None,
        "metrics_repl_preload_indexes_totalMillis": None,
        "metrics_repl_network_bytes": None,
        "metrics_repl_network_readersCreated": None,
        "metrics_repl_network_getmores_num": None,
        "metrics_repl_network_getmores_totalMillis": None,
        "metrics_repl_network_ops": None,
        "metrics_ttl_passes": None,
        "metrics_ttl_deletedDocuments": None,
        "metrics_operation_writeConflicts": None,
        "metrics_operation_fastmod": None,
        "metrics_operation_scanAndOrder": None,
        "metrics_operation_idhack": None,
        "metrics_document_deleted": None,
        "metrics_document_updated": None,
        "metrics_document_inserted": None,
        "metrics_document_returned": None,
        "connections_current": None,
        "connections_available": None,
        "connections_totalCreated": None,
        "locks_Global_timeAcquiringMicros_r": None,
        "locks_Global_timeAcquiringMicros_W": None,
        "locks_Global_acquireWaitCount_r": None,
        "locks_Global_acquireWaitCount_W": None,
        "locks_Global_acquireCount_r": None,
        "locks_Global_acquireCount_W": None,
        "locks_Global_acquireCount_w": None,
        "locks_Collection_acquireCount_R": None,
        "locks_Database_acquireCount_R": None,
        "locks_Database_acquireCount_r": None,
        "locks_Database_acquireCount_W": None,
        "cursors_clientCursors_size": None,
        "cursors_pinned": None,
        "cursors_totalNoTimeout": None,
        "cursors_timedOut": None,
        "cursors_totalOpen": None,
        "globalLock_totalTime": None,
        "globalLock_currentQueue_total": None,
        "globalLock_currentQueue_writers": None,
        "globalLock_currentQueue_readers": None,
        "globalLock_activeClients_total": None,
        "globalLock_activeClients_writers": None,
        "globalLock_activeClients_readers": None,
        "extra_info_page_faults": None,
        "extra_info_heap_usage_bytes": None,
        "uptimeMillis": None,
        "network_numRequests": None,
        "network_bytesOut": None,
        "network_bytesIn": None,
        "version": None,
        "dur_compression": float,
        "dur_journaledMB": float,
        "dur_commits": None,
        "dur_writeToDataFilesMB": float,
        "dur_commitsInWriteLock": None,
        "dur_earlyCommits": None,
        "dur_timeMs_writeToJournal": None,
        "dur_timeMs_prepLogBuffer": None,
        "dur_timeMs_remapPrivateView": None,
        "dur_timeMs_commits": None,
        "dur_timeMs_commitsInWriteLock": None,
        "dur_timeMs_dt": None,
        "dur_timeMs_writeToDataFiles": None,
        "mem_resident": None,
        "mem_supported": None,
        "mem_virtual": None,
        "mem_mappedWithJournal": None,
        "mem_mapped": None,
        "mem_bits": None,
        "opcountersRepl_getmore": None,
        "opcountersRepl_insert": None,
        "opcountersRepl_update": None,
        "opcountersRepl_command": None,
        "opcountersRepl_query": None,
        "opcountersRepl_delete": None,
        "writeBacksQueued": None,
        "backgroundFlushing_last_finished": None,
        "backgroundFlushing_last_ms": None,
        "backgroundFlushing_flushes": None,
        "opcounters_getmore": None,
        "opcounters_insert": None,
        "opcounters_update": None,
        "opcounters_command": None,
        "opcounters_query": None,
        "opcounters_delete": None,
        "ok": float,
        "asserts_msg": None,
        "asserts_rollovers": None,
        "asserts_regular": None,
        "asserts_warning": None,
        "asserts_user": None,
    }

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self.category = "/nosql/mongodb"
        self.d_superv = None
        self.stats_per_col_enabled = True
        self.stats_per_idx_enabled = True

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

        self.stats_per_col_enabled = d.get("stats_per_col_enabled", True)
        self.stats_per_idx_enabled = d.get("stats_per_idx_enabled", True)

    def reset(self):
        """
        Reset
        """

        self.d_superv = dict()
        self.d_superv["total"] = defaultdict(int)
        self.d_superv["failed"] = defaultdict(int)

    def _execute_linux(self):
        """
        Exec
        """

        self._execute_native()

    def _execute_native(self):
        """
        Exec, native
        """

        # Load files
        d_config_files = self._mongo_config_load_files()

        # Get server list, browse, get status and push counters
        for port, t in self._mongo_config_get_server_list(d_config_files):
            self.notify_value_n("k.mongodb.type", {"PORT": str(port)}, t)

            # Status
            try:
                d_status = self._mongo_get_server_status("127.0.0.1", port)
                if d_status is not None:
                    self.process_mongo_server_status(d_status, port)
            except Exception as e:
                logger.warning("Ex=%s", SolBase.extostr(e))

            # Per db / col stats
            try:
                self.process_per_db_and_col("127.0.0.1", port)
            except Exception as e:
                logger.warning("Ex=%s", SolBase.extostr(e))

            # Lag (onto data only)
            #  port=27018, shardsvr=True, config_db=False, t=data
            try:
                if t == "data":
                    self.process_data_repl_lag("127.0.0.1", port)
            except Exception as e:
                logger.warning("Ex=%s", SolBase.extostr(e))

    def _mongo_get_client(self, host, port, direct_connection=False):
        """
        Mongo get client
        :param host: str
        :type host: str
        :param port: int
        :type port: int
        :param direct_connection: bool
        :type direct_connection: bool
        :return: pymongo.mongo_client.MongoClient
        :rtype pymongo.mongo_client.MongoClient
        """

        port = str(port)
        username = None
        password = None
        if "username" in self.d_local_conf and "password" in self.d_local_conf:
            username = self.d_local_conf["username"]
            password = self.d_local_conf["password"]

        db_auth = self.d_local_conf.get("db_auth", "admin")

        if username is not None:
            cnx_string = "mongodb://%s:%s@%s:%s/%s" % (username, password, host, port, db_auth)
        else:
            cnx_string = "mongodb://%s:%s/%s" % (host, port, db_auth)

        return pymongo.MongoClient(cnx_string, directConnection=direct_connection)

    def _mongo_get_client_to_db(self, host, port, db_name):
        """
        Mongo get client
        :param host: str
        :type host: str
        :param port: int
        :type port: int
        :param db_name: str
        :type db_name: str
        :return: pymongo.mongo_client.MongoClient
        :rtype pymongo.mongo_client.MongoClient
        """

        port = str(port)
        username = None
        password = None
        if "username" in self.d_local_conf and "password" in self.d_local_conf:
            username = self.d_local_conf["username"]
            password = self.d_local_conf["password"]

        db_auth = self.d_local_conf.get("db_auth", "admin")

        if username is not None:
            cnx_string = "mongodb://%s:%s@%s:%s/%s?authSource=%s" % (username, password, host, port, db_name, db_auth)
        else:
            cnx_string = "mongodb://%s:%s/%s" % (host, port, db_name)

        return pymongo.MongoClient(cnx_string)

    def _mongo_get_server_status(self, host, port):
        """
        Get server status from mongo
        :param host: host
        :type host: str
        :param port: port
        :type port: int
        :return: dict,None
        :rtype dict,None
        """
        try:
            mongo_connection = self._mongo_get_client(host, port)
        except Exception as e:
            logger.warning(SolBase.extostr(e))
            self.notify_value_n("k.mongodb.ok", {"PORT": str(port)}, "0")
            return None

        # -----------------------------
        # Get server statistics
        # -----------------------------
        mongo_db_handle = mongo_connection["admin"]
        try:
            d_status = mongo_db_handle.command("serverStatus")
        except OperationFailure as e:
            logger.warning("OperationFailure on %s", SolBase.extostr(e))
            return None

        if not d_status["ok"] and not d_status["ok"] == 1.0:
            logger.warning("server_status Failed")
            return None

        return d_status

    def process_mongo_server_status(self, d_status, port):
        """
        Process mongo server status dict
        :param d_status: dict
        :type d_status: dict
        :param port: str
        :type port: str
        """

        self.reset()
        self.recurse(port, d_status, "")
        self.send_to_superv(port)

    @classmethod
    def _mongo_config_load_files(cls):
        """
        Load mongo config file, return dict file_name => yaml loaded
        :return: dict
        :rtype dict
        """

        d_config_files = dict()
        for conf_file in glob.glob("/etc/mongod*.conf"):
            # Read yaml
            with open(conf_file, "r") as stream:
                try:
                    config = yaml.load(stream, Loader=SafeLoader)
                except yaml.YAMLError as e:
                    # We may have \n or not yaml (old conf like files)
                    logger.debug("Cannot load (bypass, possible not yaml), conf_file=%s, ex=%s", conf_file, SolBase.extostr(e).replace("\n", " "))
                    continue
            # Register
            d_config_files[conf_file] = config
        return d_config_files

    @classmethod
    def _mongo_config_get_server_list(cls, d_config_files):
        """
        Get server list from a preloaded dict of config files
        :param d_config_files: dict config_file to yaml
        :type d_config_files: dict
        :return: list of tuple (port, type)
        :rtype list
        """
        server_list = list()
        for conf_file, config in d_config_files.items():
            config_db = False
            shardsvr = False
            mongos_mode = False

            # Fetch port
            try:
                port = config["net"]["port"]
            except KeyError as e:
                port = 27017
                logger.debug("KeyError, port cast exception (fallback 27017), ex=%s", SolBase.extostr(e))
            except TypeError as e:
                port = 27017
                logger.debug("TypeError, port cast exception (fallback 27017), ex=%s", SolBase.extostr(e))

            # Fetch roles
            try:
                cluster_role = config["sharding"]["clusterRole"]
                if cluster_role == "configsvr":
                    config_db = True
                if cluster_role == "shardsvr":
                    shardsvr = True
            except KeyError as e:
                logger.debug("Role fetch exception (bypass), ex=%s", SolBase.extostr(e))
            except TypeError as e:
                logger.debug("Role fetch exception (bypass), ex=%s", SolBase.extostr(e))

            # Fetch config
            try:
                config_db = config["sharding"]["configDB"]
                if config_db:
                    mongos_mode = True
            except KeyError as e:
                logger.debug("Shard fetch exception (bypass), ex=%s", SolBase.extostr(e))
            except TypeError as e:
                logger.debug("Shard fetch exception (bypass), ex=%s", SolBase.extostr(e))

            # Compute
            if not shardsvr and config_db:
                t = "config"
            elif shardsvr and not config_db:
                t = "data"
            elif mongos_mode:
                t = "mongos"
            elif not shardsvr and not config_db:
                t = "standalone"
            else:
                # WTF ! how i pass here !
                t = "unknown"

            # Add
            logger.debug("Got server, conf_file=%s, port=%s, shardsvr=%s, config_db=%s, t=%s" % (conf_file, port, shardsvr, config_db, t))
            server_list.append((port, t))

        # Over
        return server_list

    @classmethod
    def clean_value(cls, v, key):
        """
        Clean
        :param v: str
        :type v: int, float, datetime
        :param key: str
        :type key: str
        :return int, float
        :rtype int, float
        """

        # Via type
        if isinstance(v, datetime):
            v = int(v.strftime("%s"))
        elif isinstance(v, float):
            v = round(v, 3)
        elif isinstance(v, int):
            v = abs(v)

        # Via keys
        if MongoDbStat.KEYS[key] is not None:
            # Use callable
            v = MongoDbStat.KEYS[key](v)
        else:
            # NO EXPLICIT CASTING
            # For influx, we cast int in all cases for numeric # TODO : float only ?
            if not isinstance(v, (datetime, str)):
                v = int(v)
        return v

    def recurse(self, port, d, subkey):
        """
        Recurse on d
        :param port: str
        :type port: str
        :param d: dict
        :type d: dict
        :param subkey: str
        :type subkey: str
        """
        for k, v in d.items():
            if k == "raw":
                continue
            elif isinstance(v, dict):
                # Dict, recurse stuff
                if subkey == "metrics_commands_":
                    self.agregate_recurse(v, subkey)
                else:
                    self.recurse(port, v, subkey + k + "_")
            elif subkey + k in MongoDbStat.KEYS:
                # Direct
                if len(subkey) > 0:
                    self.notify_value_n("k.mongodb.%s%s" % (subkey, k), {"PORT": str(port)}, self.clean_value(v, subkey + k))
                else:
                    self.notify_value_n("k.mongodb.%s" % k, {"PORT": str(port)}, self.clean_value(v, subkey + k))
            else:
                # Bypass, not handled here
                pass

    def agregate_recurse(self, d, subkey):
        """
        Aggregate, recursive
        :param d: dict
        :type d: dict
        :param subkey: str
        :type subkey: str
        """
        for key, value in d.items():
            if key in ("total", "failed"):  # Agregating 250+ keys
                master_key = "_".join(subkey.split("_", 3)[0:2])
                if key == "total":
                    self.d_superv["total"][master_key] += value
                elif key == "failed":
                    self.d_superv["failed"][master_key] += value

    def send_to_superv(self, port):
        """
        Send to supervision the d_superv dict
        :param port: str
        :type port: str
        """
        for cur_type in self.d_superv:
            for k, v in self.d_superv[cur_type].items():
                self.notify_value_n("k.mongodb.%s_%s" % (k, cur_type), {"PORT": str(port)}, v)

    # ==================================
    # PER DB / PER COLLECTION STAT
    # ==================================

    def process_from_buffer_db(self, port, db_name, db_stat_buf):
        """
        Process db from buffer
        :param port: int
        :type port: int
        :param db_name: str
        :type db_name: str
        :param db_stat_buf: str
        :type db_stat_buf: str
        """

        # str to dict if required
        if isinstance(db_stat_buf, str):
            d_stat = json.loads(db_stat_buf)
        else:
            d_stat = db_stat_buf

        # Check dict
        if not isinstance(d_stat, dict):
            raise Exception("Cannot process, not a dict, got=%s" % SolBase.get_classname(db_stat_buf))

        # Check ok
        if int(d_stat.get("ok", -1)) != 1:
            raise Exception("Cannot process ('ok' miss or invalid), got=%s" % db_stat_buf)

        # {
        #         "db" : "test_labo_mongo",
        #         "collections" : 1,
        #         "views" : 0,
        #         "objects" : 400000,
        #         "avgObjSize" : 58,
        #         "dataSize" : 23200000,
        #         "storageSize" : 15179776,
        #         "numExtents" : 0,
        #         "indexes" : 3,
        #         "indexSize" : 17924096,
        #         "fsUsedSize" : 26165620736,
        #         "fsTotalSize" : 33756561408,
        #         "ok" : 1
        # }

        d_tags = {"PORT": str(port), "DB": db_name}
        for s in [
            "collections",
            "objects",
            "avgObjSize",
            "dataSize",
            "storageSize",
            "indexes",
            "indexSize",
            "fsUsedSize",
            "fsTotalSize",
        ]:
            v = float(d_stat.get(s, -1))
            c = "k.mongodb.db.%s" % s
            self.notify_value_n(c, d_tags, v)
            SolBase.sleep(0)

    def process_from_buffer_col(self, port, db_name, col_name, col_stat_buf):
        """
        Process col from buffer
        :param port: int
        :type port: int
        :param db_name: str
        :type db_name: str
        :param col_name: str
        :type col_name: str
        :param col_stat_buf: str,dict
        :type col_stat_buf: str,dict
        """

        if not self.stats_per_col_enabled and not self.stats_per_idx_enabled:
            return

        # str to dict if required
        if isinstance(col_stat_buf, str):
            d_stat = json.loads(col_stat_buf)
        else:
            d_stat = col_stat_buf

        # Check dict
        if not isinstance(d_stat, dict):
            raise Exception("Cannot process, not a dict, got=%s" % SolBase.get_classname(col_stat_buf))

        # Check ok
        if int(d_stat.get("ok", -1)) != 1:
            raise Exception("Cannot process ('ok' miss or invalid), got=%s" % d_stat.get("ok", None))

        # Go
        if self.stats_per_col_enabled:
            d_tags = {"PORT": str(port), "DB": db_name, "COL": col_name}
            for s in [
                "size",
                "count",
                "avgObjSize",
                "storageSize",
                "totalIndexSize",
                "nindexes",
            ]:
                v = float(d_stat.get(s, -1))
                c = "k.mongodb.col.%s" % s
                self.notify_value_n(c, d_tags, v)

        # Per index size / cache / cursor
        if self.stats_per_idx_enabled:
            if "indexSizes" in d_stat:
                for k, v in d_stat["indexSizes"].items():
                    d_tags_index = {"PORT": str(port), "DB": db_name, "COL": col_name, "IDX": k}
                    c = "k.mongodb.col.idx.indexSizes"
                    self.notify_value_n(c, d_tags_index, float(v))
                    SolBase.sleep(0)

                    # Index details
                    if "indexDetails" in d_stat and k in d_stat["indexDetails"]:
                        d_idx_details = d_stat["indexDetails"][k]

                        if "cache" in d_idx_details:
                            for s in [
                                "bytes currently in the cache",
                                "bytes read into cache",
                                "bytes written from cache",
                                "pages read into cache",
                                "pages requested from the cache",
                                "pages written from cache",
                                "internal pages evicted",
                                "modified pages evicted",
                                "unmodified pages evicted",
                            ]:
                                v = float(d_idx_details["cache"].get(s, -1))
                                c = "k.mongodb.col.idx.detail.%s" % s.replace(" ", "_")
                                self.notify_value_n(c, d_tags_index, v)
                                SolBase.sleep(0)

                        if "cursor" in d_idx_details:
                            for s in [
                                "create calls",
                                "insert calls",
                                "insert key and value bytes",
                                "next calls",
                                "prev calls",
                                "remove calls",
                                "remove key bytes removed",
                                "reserve calls",
                                "reset calls",
                                "search calls",
                                "search near calls",
                                "truncate calls",
                                "update calls",
                                "update key and value bytes",
                            ]:
                                v = float(d_idx_details["cursor"].get(s, -1))
                                c = "k.mongodb.col.idx.cursor.%s" % s.replace(" ", "_")
                                self.notify_value_n(c, d_tags_index, v)
                                SolBase.sleep(0)

    def process_from_buffer_index_stat(self, port, db_name, col_name, index_stat_buf):
        """
        Process col from buffer
        :param port: int
        :type port: int
        :param db_name: str
        :type db_name: str
        :param col_name: str
        :type col_name: str
        :param index_stat_buf: list
        :type index_stat_buf: list
        """

        if not self.stats_per_col_enabled and not self.stats_per_idx_enabled:
            return

        list_stat = index_stat_buf

        # Check list
        if not isinstance(list_stat, list):
            raise Exception("Cannot process, not a list, got=%s" % SolBase.get_classname(index_stat_buf))

        # Go
        if self.stats_per_idx_enabled:
            d_tags = {"PORT": str(port), "DB": db_name, "COL": col_name}
            for index_stat in list_stat:
                if len(index_stat) == 0: continue

                # sample = {'accesses': {'ops': 0, 'since': datetime.datetime(2023, 5, 17, 8, 56, 37, 141000)},
                #     'host': 'node01:27017',
                #     'key': {'_id': 1},
                #     'name': '_id_',
                #     'spec': {'key': {'_id': 1}, 'name': '_id_', 'v': 2}}

                d_tags['IDX'] = index_stat['name']
                if "accesses" in index_stat:
                    accesses = index_stat["accesses"]
                    v = float(accesses.get("ops", 0.0))

                    self.notify_value_n("k.mongodb.index_stats.ops", d_tags, v)
                    if 'since' in accesses:
                        since = dateutil.parser.parse(accesses['since'])
                        since_millis = float((datetime.utcnow().timestamp() - since.timestamp()) * 1000)
                        self.notify_value_n("k.mongodb.index_stats.last_used_millis", d_tags, since_millis)

    def process_data_repl_lag(self, host, port):
        """
        Replication lag
        :param host: str
        :type host: str
        :param port: int
        :type port: int
        """

        # Connect (27018, direct connection)
        mongo_client = self._mongo_get_client(host, port, direct_connection=True)
        db_stats = mongo_client.admin.command({'replSetGetStatus': 1})

        # Detect if we are primary
        is_primary = False
        hostname = SolBase.get_machine_name()
        for d in db_stats['members']:
            name = d["name"]
            state = d["stateStr"]
            if state == "PRIMARY" and name.startswith(hostname):
                is_primary = True
                break

        # Go
        primary_optime = None
        ar_primary_secondaries_optime = list()
        secondary_optime = None

        for d in db_stats['members']:
            name = d["name"]
            state = d["stateStr"]
            optime = d["optimeDate"]
            logger.info("Got repl, name=%s, state=%s, optime=%s", name, state, optime)

            # Get primary
            if state == "PRIMARY":
                primary_optime = optime

            # Secondaries
            if state == "SECONDARY":
                if name.startswith(hostname):
                    # It is US, we are secondary, store our time
                    secondary_optime = optime
                elif is_primary:
                    # It is not us... we are primary, append to secondaries
                    ar_primary_secondaries_optime.append(optime)

        # Check
        lag_seconds = 0.0
        lag_seconds_max = 0.0
        if primary_optime is None:
            # No primary optime => giveup
            lag_seconds = -1.0
        elif secondary_optime is None:
            # We should be the master
            if is_primary:
                if len(ar_primary_secondaries_optime) > 0:
                    # We are master, with slave optimes, compute the max
                    for optime in ar_primary_secondaries_optime:
                        lag_seconds = float((primary_optime - optime).total_seconds())
                        if lag_seconds < 0.0:
                            lag_seconds = 0.0
                        lag_seconds_max = max(lag_seconds_max, lag_seconds)
                else:
                    # Master without secondaries
                    logger.info("secondary_optime None + is_primary True + ar_primary_secondaries_optime empty, cannot process")
                    lag_seconds = -2.0
            else:
                # Secondary optime without master flag...
                logger.info("secondary_optime None + is_primary False, cannot process")
                lag_seconds = -3.0
        else:
            # We are secondary
            # Note : we may have secondary_optime > primary_optime, which result in negative lag_seconds
            # refer to : https://www.mongodb.com/community/forums/t/replication-oplog-is-ahead-of-time/5666/8
            # => if < 0 : put 0
            lag_seconds = float((primary_optime - secondary_optime).total_seconds())
            if lag_seconds < 0.0:
                lag_seconds = 0.0

        # Notify
        logger.info("Got repl, lag_seconds/max=%s/%s, hostname=%s, is_primary=%s, optime.PRI/SEC=%s/%s, ar=%s", lag_seconds, lag_seconds_max, hostname, is_primary, primary_optime, secondary_optime, ar_primary_secondaries_optime)
        self.notify_value_n("k.mongodb.repli.sec.lag_sec", {"PORT": str(port)}, lag_seconds)
        self.notify_value_n("k.mongodb.repli.pri.max_sec_lag_sec", {"PORT": str(port)}, lag_seconds_max)

    def process_per_db_and_col(self, host, port):
        """
        Get per DB / COLLECTION stats
        :param host: str
        :type host: str
        :param port: int
        :type port: int
        """

        db = None
        col = None

        # Get exclusions
        ar_db_excluded = self.d_local_conf.get("stat_per_col_ar_db_excluded", ["admin", "config"])
        ar_port_excluded = self.d_local_conf.get("stat_per_col_ar_port_excluded", [])
        ar_col_excluded = self.d_local_conf.get("stat_per_col_ar_col_excluded", ["__schema__"])
        logger.debug("Using ar_db_excluded=%s", ar_db_excluded)
        logger.debug("Using ar_port_excluded=%s", ar_port_excluded)
        logger.debug("Using ar_col_excluded=%s", ar_col_excluded)
        try:
            # Check
            if port in ar_port_excluded:
                return

            # Connect (to admin)
            mongo_client = self._mongo_get_client(host, port)

            # For each db
            for db in mongo_client.list_database_names():
                db = str(db)
                col = None

                # Skip admin and config (mongo stuff)
                if db in ar_db_excluded:
                    continue

                # Connect (to current db)
                mongo_client_to_db = self._mongo_get_client_to_db(host, port, db)
                cur_db = mongo_client_to_db[db]

                # Get stats (database)
                # https://www.mongodb.com/docs/manual/reference/command/dbStats/
                db_stats = cur_db.command("dbstats")
                SolBase.sleep(0)
                self.process_from_buffer_db(port, db, db_stats)
                SolBase.sleep(0)

                # For each collection : get stats (collections / indexex)
                # https://www.mongodb.com/docs/manual/reference/command/collStats/
                # db.runCommand({collStats: "col_name"});
                try:
                    for col in cur_db.list_collection_names():
                        col = str(col)
                        # Skip
                        if col in ar_col_excluded:
                            continue
                        # Skip "system."
                        if col.startswith("system."):
                            continue

                        # Go
                        try:
                            col_stats = cur_db.command("collStats", col)
                            SolBase.sleep(0)
                            try:
                                self.process_from_buffer_col(port, db, col, col_stats)
                            except Exception as e:
                                logger.warning("Ex (skipped, bug, process_from_buffer_col), host=%s, port=%s, db=%s, col=%s, =%s", host, port, db, col, SolBase.extostr(e))
                            SolBase.sleep(0)
                        except Exception as e:
                            logger.warning("Ex (skipped, possible rights, collStats), host=%s, port=%s, db=%s, col=%s, =%s", host, port, db, col, SolBase.extostr(e))

                        # Go index stats
                        try:
                            index_stats = cur_db.aggregate([{'$indexStats': {}}])
                            SolBase.sleep(0)
                            try:
                                self.process_from_buffer_index_stat(port, db, col, index_stats)
                            except Exception as e:
                                logger.warning("Ex (skipped, bug, process_from_buffer_index_stat), host=%s, port=%s, db=%s, col=%s, =%s", host, port, db, col, SolBase.extostr(e))
                            SolBase.sleep(0)
                        except Exception as e:
                            logger.warning("Ex (skipped, possible rights, indexStats), host=%s, port=%s, db=%s, col=%s, =%s", host, port, db, col, SolBase.extostr(e))

                except Exception as e:
                    logger.warning("Ex(skipped, possible rights, list_collection_names), host=%s, port=%s, db=%s, col=%s, =%s", host, port, db, col, SolBase.extostr(e))
        except Exception as e:
            logger.warning("Ex(fatal, possible rights, list_database_names), host=%s, port=%s, db=%s, col=%s, =%s", host, port, db, col, SolBase.extostr(e))

    @classmethod
    def mongo_cleanup_buffer(cls, buf):
        """
        Mongo cleanup buffer
        :param buf: str
        :type buf: str
        :return: str
        :rtype str
        """

        # NumberLong(772349720)
        # NumberLong("6970055494123651073")
        # ISODate("2021-09-16T08:12:00.002Z")
        # Timestamp(1631779918, 11)
        # BinData(0,"mPIrxO2yyOyZgIXyYGL7awzFgKo="),
        ar_regex = [
            r'NumberLong\(\d+\)',
            r'NumberLong\("\d+"\)',
            r'ISODate\(".*"\)',
            r'Timestamp\(\d+, \d+\)',
            r'BinData\(.*\)',
        ]

        # Totally sub-optimal, unittests, we dont care
        for s in ar_regex:
            for ss in re.findall(s, buf):
                if 'NumberLong("' in ss:
                    buf = buf.replace(ss, ss.replace('NumberLong("', '').replace('")', ''))
                elif 'NumberLong(' in ss:
                    buf = buf.replace(ss, ss.replace('NumberLong(', '').replace(')', ''))
                elif 'ISODate("' in ss:
                    buf_dt = ss.replace('ISODate("', "").replace('")', "")
                    try:
                        dt = dateutil.parser.parse(buf_dt)
                    except TypeError as e:
                        logger.error("Parse date error %s, %s", buf_dt, SolBase.extostr(e))
                    buf = buf.replace(ss, f'"{dt.isoformat()}"')
                elif 'Timestamp(' in ss:
                    ts = ss.replace('Timestamp(', '').replace(')', '').split(',')[0]
                    buf = buf.replace(ss, ts)
                elif 'BinData(' in ss:
                    buf = buf.replace(ss, '"bin_data"')
                else:
                    raise Exception("Invalid ss=%s" % ss)

        return buf
