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

import glob
import logging
from collections import defaultdict
from datetime import datetime

import pymongo
import yaml
from pysolbase.SolBase import SolBase

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

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self.strport = None
        self.super_key = dict()
        self.super_key['total'] = defaultdict(int)
        self.super_key['failed'] = defaultdict(int)
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
            self.notify_discovery_n("k.mongodb.discovery", {"PORT": str(port)})
            self.notify_value_n("k.mongodb.type", {"PORT": str(port)}, t)

            try:
                self.getstat("127.0.0.1", port)
            except Exception as e:
                logger.warn(SolBase.extostr(e))

    def getstat(self, host, port):
        """
        Get stats
        :param host: host
        :param port: port
        :return:
        """
        self.strport = str(port)

        try:
            username = None
            password = None
            if self.d_local_conf.get('username', False):
                username = self.d_local_conf.get('username', False)
                password = self.d_local_conf.get('password', False)
            mongo_connection = pymongo.MongoClient(host, port, username=username, password=password)

        except Exception as e:
            logger.warn(SolBase.extostr(e))
            self.notify_value_n("k.mongodb.ok", {"PORT": self.strport}, "0")
            return

        # -----------------------------
        # Get server statistics
        # -----------------------------
        mongo_db_handle = mongo_connection["config"]

        server_status = mongo_db_handle.command("serverStatus")

        if not server_status['ok'] and not server_status['ok'] == 1.0:
            logger.warn("server_status Failed")
            return
        else:
            self.recurse(server_status, '')
            self.send_super_key()

    # noinspection PyMethodMayBeStatic
    def __getserverlist(self):
        """
        Get
        :return:
        """
        server_list = list()

        conf_files = glob.glob('/etc/mongod*.conf')
        logger.debug("initd files : %s", conf_files)

        for conf_file in conf_files:
            config_db = False
            # port = 0
            shardsvr = False
            mongos_mode = False
            # config = dict()

            with open(conf_file, 'r') as stream:
                try:
                    config = yaml.load(stream)
                except yaml.YAMLError as e:
                    logger.warn('Error loadding %s %s ', conf_file, SolBase.extostr(e))
                    continue
            try:
                port = config['net']['port']
            except KeyError as e:
                port = 27017
                logger.warn(SolBase.extostr(e))

            try:
                cluster_role = config['sharding']['clusterRole']
                if cluster_role == 'configsvr':
                    config_db = True
                if cluster_role == 'shardsvr':
                    shardsvr = True
            except KeyError as e:
                logger.debug(SolBase.extostr(e))

            try:
                config_db = config['sharding']['configDB']
                if config_db:
                    mongos_mode = True
            except KeyError as e:
                logger.debug(SolBase.extostr(e))

            if not shardsvr and config_db:
                t = "config"
            elif shardsvr and not config_db:
                t = "data"
            elif mongos_mode:
                t = "mongos"
            elif not shardsvr and not config_db:
                t = 'standalone'
            else:
                # WTF ! how i pass here !
                t = "unknown"

            server_list.append((port, t))
            logger.debug("conf %s - port %s - shard %s - confiDb %s - type %s" % (
                conf_file, port, shardsvr, config_db, t))
        return server_list

    # noinspection PyMethodMayBeStatic
    def cleanvalue(self, v, key):
        """
        Clean
        :param v: str
        :param key: str
        """

        if isinstance(v, datetime):
            v = int(v.strftime('%s'))
        elif isinstance(v, float):
            v = round(v, 3)
        elif isinstance(v, (int, long)):
            v = abs(v)
        if MongodDbStatKeys.Key[key] is not None:
            v = MongodDbStatKeys.Key[key](v)
        else:
            # NO EXPLICIT CASTING
            # For influx, we cast int in all cases for numeric
            if not isinstance(v, (datetime, str, unicode, basestring)):
                v = int(v)

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
                if subkey == 'metrics_commands_':
                    self.agregate_recurse(value, subkey)
                    continue
                self.recurse(value, subkey + key + "_")
            else:
                if subkey + key in MongodDbStatKeys.Key:
                    self.notify_value_n("k.mongodb." + subkey + key, {"PORT": self.strport}, self.cleanvalue(value, subkey + key))

    def agregate_recurse(self, dictionary, subkey):
        """

        :param dictionary:
        :param subkey:
        :return:
        """
        for key, value in dictionary.items():

            if key in ('total', 'failed'):  # Agregating 250+ keys
                master_key = '_'.join(subkey.split('_', 3)[0:2])
                if key == 'total':
                    self.super_key['total'][master_key] += value
                elif key == 'failed':
                    self.super_key['failed'][master_key] += value

    def send_super_key(self):
        """

        :return:
        """
        for cur_type in self.super_key:
            for k, v in self.super_key[cur_type].iteritems():
                self.notify_value_n("k.mongodb." + k + "_" + cur_type, {"PORT": self.strport}, v)


class MongodDbStatKeys(object):
    """

    """
    Key = {
        'metrics_commands_updateUser_failed': None,
        'metrics_commands_updateUser_total': None,
        'metrics_commands_dropRole_failed': None,
        'metrics_commands_dropRole_total': None,
        'metrics_commands_renameCollection_failed': None,
        'metrics_commands_renameCollection_total': None,
        'metrics_commands_planCacheSetFilter_failed': None,
        'metrics_commands_planCacheSetFilter_total': None,
        'metrics_commands_top_failed': None,
        'metrics_commands_top_total': None,
        'metrics_commands_usersInfo_failed': None,
        'metrics_commands_usersInfo_total': None,
        'metrics_commands_applyOps_failed': None,
        'metrics_commands_applyOps_total': None,
        'metrics_commands_setParameter_failed': None,
        'metrics_commands_setParameter_total': None,
        'metrics_commands_find_failed': None,
        'metrics_commands_find_total': None,
        'metrics_commands_compact_failed': None,
        'metrics_commands_compact_total': None,
        'metrics_commands_createIndexes_failed': None,
        'metrics_commands_createIndexes_total': None,
        'metrics_commands_handshake_failed': None,
        'metrics_commands_handshake_total': None,
        'metrics_commands_group_failed': None,
        'metrics_commands_group_total': None,
        'metrics_commands_moveChunk_failed': None,
        'metrics_commands_moveChunk_total': None,
        'metrics_commands__mergeAuthzCollections_failed': None,
        'metrics_commands__mergeAuthzCollections_total': None,
        'metrics_commands_explain_failed': None,
        'metrics_commands_explain_total': None,
        'metrics_commands__migrateClone_failed': None,
        'metrics_commands__migrateClone_total': None,
        'metrics_commands_checkShardingIndex_failed': None,
        'metrics_commands_checkShardingIndex_total': None,
        'metrics_commands_logRotate_failed': None,
        'metrics_commands_logRotate_total': None,
        'metrics_commands_getPrevError_failed': None,
        'metrics_commands_getPrevError_total': None,
        'metrics_commands_replSetGetStatus_failed': None,
        'metrics_commands_replSetGetStatus_total': None,
        'metrics_commands_grantRolesToUser_failed': None,
        'metrics_commands_grantRolesToUser_total': None,
        'metrics_commands_shardConnPoolStats_failed': None,
        'metrics_commands_shardConnPoolStats_total': None,
        'metrics_commands_diagLogging_failed': None,
        'metrics_commands_diagLogging_total': None,
        'metrics_commands_splitChunk_failed': None,
        'metrics_commands_splitChunk_total': None,
        'metrics_commands_planCacheClear_failed': None,
        'metrics_commands_planCacheClear_total': None,
        'metrics_commands_getCmdLineOpts_failed': None,
        'metrics_commands_getCmdLineOpts_total': None,
        'metrics_commands_insert_failed': None,
        'metrics_commands_insert_total': None,
        'metrics_commands_replSetInitiate_failed': None,
        'metrics_commands_replSetInitiate_total': None,
        'metrics_commands_replSetGetConfig_failed': None,
        'metrics_commands_replSetGetConfig_total': None,
        'metrics_commands_fsync_failed': None,
        'metrics_commands_fsync_total': None,
        'metrics_commands_appendOplogNote_failed': None,
        'metrics_commands_appendOplogNote_total': None,
        'metrics_commands_drop_failed': None,
        'metrics_commands_drop_total': None,
        'metrics_commands_mapreduce_shardedfinish_failed': None,
        'metrics_commands_mapreduce_shardedfinish_total': None,
        'metrics_commands__recvChunkAbort_failed': None,
        'metrics_commands__recvChunkAbort_total': None,
        'metrics_commands_replSetSyncFrom_failed': None,
        'metrics_commands_replSetSyncFrom_total': None,
        'metrics_commands_connectionStatus_failed': None,
        'metrics_commands_connectionStatus_total': None,
        'metrics_commands_touch_failed': None,
        'metrics_commands_touch_total': None,
        'metrics_commands__recvChunkStatus_failed': None,
        'metrics_commands__recvChunkStatus_total': None,
        'metrics_commands_copydbgetnonce_failed': None,
        'metrics_commands_copydbgetnonce_total': None,
        'metrics_commands_planCacheListPlans_failed': None,
        'metrics_commands_planCacheListPlans_total': None,
        'metrics_commands_dataSize_failed': None,
        'metrics_commands_dataSize_total': None,
        'metrics_commands_dbHash_failed': None,
        'metrics_commands_dbHash_total': None,
        'metrics_commands_medianKey_failed': None,
        'metrics_commands_medianKey_total': None,
        'metrics_commands__recvChunkStart_failed': None,
        'metrics_commands__recvChunkStart_total': None,
        'metrics_commands_authenticate_failed': None,
        'metrics_commands_authenticate_total': None,
        'metrics_commands_cursorInfo_failed': None,
        'metrics_commands_cursorInfo_total': None,
        'metrics_commands_revokeRolesFromRole_failed': None,
        'metrics_commands_revokeRolesFromRole_total': None,
        'metrics_commands_grantPrivilegesToRole_failed': None,
        'metrics_commands_grantPrivilegesToRole_total': None,
        'metrics_commands_geoNear_failed': None,
        'metrics_commands_geoNear_total': None,
        'metrics_commands_replSetFresh_failed': None,
        'metrics_commands_replSetFresh_total': None,
        'metrics_commands_planCacheClearFilters_failed': None,
        'metrics_commands_planCacheClearFilters_total': None,
        'metrics_commands_getParameter_failed': None,
        'metrics_commands_getParameter_total': None,
        'metrics_commands_dropIndexes_failed': None,
        'metrics_commands_dropIndexes_total': None,
        'metrics_commands_listDatabases_failed': None,
        'metrics_commands_listDatabases_total': None,
        'metrics_commands_collStats_failed': None,
        'metrics_commands_collStats_total': None,
        'metrics_commands_hostInfo_failed': None,
        'metrics_commands_hostInfo_total': None,
        'metrics_commands_getShardVersion_failed': None,
        'metrics_commands_getShardVersion_total': None,
        'metrics_commands_cloneCollection_failed': None,
        'metrics_commands_cloneCollection_total': None,
        'metrics_commands_dropDatabase_failed': None,
        'metrics_commands_dropDatabase_total': None,
        'metrics_commands_update_failed': None,
        'metrics_commands_update_total': None,
        'metrics_commands_logout_failed': None,
        'metrics_commands_logout_total': None,
        'metrics_commands__transferMods_failed': None,
        'metrics_commands__transferMods_total': None,
        'metrics_commands_isMaster_failed': None,
        'metrics_commands_isMaster_total': None,
        'metrics_commands_getShardMap_failed': None,
        'metrics_commands_getShardMap_total': None,
        'metrics_commands_shardingState_failed': None,
        'metrics_commands_shardingState_total': None,
        'metrics_commands_replSetReconfig_failed': None,
        'metrics_commands_replSetReconfig_total': None,
        'metrics_commands_getLog_failed': None,
        'metrics_commands_getLog_total': None,
        'metrics_commands_connPoolSync_failed': None,
        'metrics_commands_connPoolSync_total': None,
        'metrics_commands_revokePrivilegesFromRole_failed': None,
        'metrics_commands_revokePrivilegesFromRole_total': None,
        'metrics_commands_replSetMaintenance_failed': None,
        'metrics_commands_replSetMaintenance_total': None,
        'metrics_commands_serverStatus_failed': None,
        'metrics_commands_serverStatus_total': None,
        'metrics_commands_replSetStepDown_failed': None,
        'metrics_commands_replSetStepDown_total': None,
        'metrics_commands_features_failed': None,
        'metrics_commands_features_total': None,
        'metrics_commands_connPoolStats_failed': None,
        'metrics_commands_connPoolStats_total': None,
        'metrics_commands_planCacheListQueryShapes_failed': None,
        'metrics_commands_planCacheListQueryShapes_total': None,
        'metrics_commands_copydb_failed': None,
        'metrics_commands_copydb_total': None,
        'metrics_commands_forceerror_failed': None,
        'metrics_commands_forceerror_total': None,
        'metrics_commands_planCacheListFilters_failed': None,
        'metrics_commands_planCacheListFilters_total': None,
        'metrics_commands_shutdown_failed': None,
        'metrics_commands_shutdown_total': None,
        'metrics_commands_listCollections_failed': None,
        'metrics_commands_listCollections_total': None,
        'metrics_commands_currentOpCtx_failed': None,
        'metrics_commands_currentOpCtx_total': None,
        'metrics_commands__getUserCacheGeneration_failed': None,
        'metrics_commands__getUserCacheGeneration_total': None,
        'metrics_commands_validate_failed': None,
        'metrics_commands_validate_total': None,
        'metrics_commands_repairDatabase_failed': None,
        'metrics_commands_repairDatabase_total': None,
        'metrics_commands_saslStart_failed': None,
        'metrics_commands_saslStart_total': None,
        'metrics_commands_distinct_failed': None,
        'metrics_commands_distinct_total': None,
        'metrics_commands_create_failed': None,
        'metrics_commands_create_total': None,
        'metrics_commands_splitVector_failed': None,
        'metrics_commands_splitVector_total': None,
        'metrics_commands_copydbsaslstart_failed': None,
        'metrics_commands_copydbsaslstart_total': None,
        'metrics_commands_dropAllRolesFromDatabase_failed': None,
        'metrics_commands_dropAllRolesFromDatabase_total': None,
        'metrics_commands_invalidateUserCache_failed': None,
        'metrics_commands_invalidateUserCache_total': None,
        'metrics_commands_whatsmyuri_failed': None,
        'metrics_commands_whatsmyuri_total': None,
        'metrics_commands_geoSearch_failed': None,
        'metrics_commands_geoSearch_total': None,
        'metrics_commands_updateRole_failed': None,
        'metrics_commands_updateRole_total': None,
        'metrics_commands_reIndex_failed': None,
        'metrics_commands_reIndex_total': None,
        'metrics_commands__isSelf_failed': None,
        'metrics_commands__isSelf_total': None,
        'metrics_commands_unsetSharding_failed': None,
        'metrics_commands_unsetSharding_total': None,
        'metrics_commands_getnonce_failed': None,
        'metrics_commands_getnonce_total': None,
        'metrics_commands_listIndexes_failed': None,
        'metrics_commands_listIndexes_total': None,
        'metrics_commands_collMod_failed': None,
        'metrics_commands_collMod_total': None,
        'metrics_commands_count_failed': None,
        'metrics_commands_count_total': None,
        'metrics_commands_filemd5_failed': None,
        'metrics_commands_filemd5_total': None,
        'metrics_commands_setShardVersion_failed': None,
        'metrics_commands_setShardVersion_total': None,
        'metrics_commands_parallelCollectionScan_failed': None,
        'metrics_commands_parallelCollectionScan_total': None,
        'metrics_commands_writebacklisten_failed': None,
        'metrics_commands_writebacklisten_total': None,
        'metrics_commands_delete_failed': None,
        'metrics_commands_delete_total': None,
        'metrics_commands_rolesInfo_failed': None,
        'metrics_commands_rolesInfo_total': None,
        'metrics_commands_replSetGetRBID_failed': None,
        'metrics_commands_replSetGetRBID_total': None,
        'metrics_commands_dropUser_failed': None,
        'metrics_commands_dropUser_total': None,
        'metrics_commands_resync_failed': None,
        'metrics_commands_resync_total': None,
        'metrics_commands_saslContinue_failed': None,
        'metrics_commands_saslContinue_total': None,
        'metrics_commands_repairCursor_failed': None,
        'metrics_commands_repairCursor_total': None,
        'metrics_commands_driverOIDTest_failed': None,
        'metrics_commands_driverOIDTest_total': None,
        'metrics_commands_getLastError_failed': None,
        'metrics_commands_getLastError_total': None,
        'metrics_commands_convertToCapped_failed': None,
        'metrics_commands_convertToCapped_total': None,
        'metrics_commands_replSetHeartbeat_failed': None,
        'metrics_commands_replSetHeartbeat_total': None,
        'metrics_commands_ping_failed': None,
        'metrics_commands_ping_total': None,
        'metrics_commands_availableQueryOptions_failed': None,
        'metrics_commands_availableQueryOptions_total': None,
        'metrics_commands_dropAllUsersFromDatabase_failed': None,
        'metrics_commands_dropAllUsersFromDatabase_total': None,
        'metrics_commands_cloneCollectionAsCapped_failed': None,
        'metrics_commands_cloneCollectionAsCapped_total': None,
        'metrics_commands_listCommands_failed': None,
        'metrics_commands_listCommands_total': None,
        'metrics_commands_profile_failed': None,
        'metrics_commands_profile_total': None,
        'metrics_commands_replSetElect_failed': None,
        'metrics_commands_replSetElect_total': None,
        'metrics_commands_cleanupOrphaned_failed': None,
        'metrics_commands_cleanupOrphaned_total': None,
        'metrics_commands_replSetFreeze_failed': None,
        'metrics_commands_replSetFreeze_total': None,
        'metrics_commands_clone_failed': None,
        'metrics_commands_clone_total': None,
        'metrics_commands_mapReduce_failed': None,
        'metrics_commands_mapReduce_total': None,
        'metrics_commands_eval_failed': None,
        'metrics_commands_eval_total': None,
        'metrics_commands_createUser_failed': None,
        'metrics_commands_createUser_total': None,
        'metrics_commands_aggregate_failed': None,
        'metrics_commands_aggregate_total': None,
        'metrics_commands_replSetUpdatePosition_failed': None,
        'metrics_commands_replSetUpdatePosition_total': None,
        'metrics_commands_mergeChunks_failed': None,
        'metrics_commands_mergeChunks_total': None,
        'metrics_commands_revokeRolesFromUser_failed': None,
        'metrics_commands_revokeRolesFromUser_total': None,
        'metrics_commands_createRole_failed': None,
        'metrics_commands_createRole_total': None,
        'metrics_commands_authSchemaUpgrade_failed': None,
        'metrics_commands_authSchemaUpgrade_total': None,
        'metrics_commands_findAndModify_failed': None,
        'metrics_commands_findAndModify_total': None,
        'metrics_commands_dbStats_failed': None,
        'metrics_commands_dbStats_total': None,
        'metrics_commands__recvChunkCommit_failed': None,
        'metrics_commands__recvChunkCommit_total': None,
        'metrics_commands_grantRolesToRole_failed': None,
        'metrics_commands_grantRolesToRole_total': None,
        'metrics_commands_buildInfo_failed': None,
        'metrics_commands_buildInfo_total': None,
        'metrics_commands_resetError_failed': None,
        'metrics_commands_resetError_total': None,
        'metrics_storage_freelist_search_requests': None,
        'metrics_storage_freelist_search_scanned': None,
        'metrics_storage_freelist_search_bucketExhausted': None,
        'metrics_getLastError_wtime_num': None,
        'metrics_getLastError_wtime_totalMillis': None,
        'metrics_getLastError_wtimeouts': None,
        'metrics_queryExecutor_scanned': None,
        'metrics_queryExecutor_scannedObjects': None,
        'metrics_cursor_timedOut': None,
        'metrics_cursor_open_pinned': None,
        'metrics_cursor_open_total': None,
        'metrics_cursor_open_noTimeout': None,
        'metrics_record_moves': None,
        'metrics_repl_buffer_count': None,
        'metrics_repl_buffer_sizeBytes': None,
        'metrics_repl_buffer_maxSizeBytes': None,
        'metrics_repl_apply_batches_num': None,
        'metrics_repl_apply_batches_totalMillis': None,
        'metrics_repl_apply_ops': None,
        'metrics_repl_preload_docs_num': None,
        'metrics_repl_preload_docs_totalMillis': None,
        'metrics_repl_preload_indexes_num': None,
        'metrics_repl_preload_indexes_totalMillis': None,
        'metrics_repl_network_bytes': None,
        'metrics_repl_network_readersCreated': None,
        'metrics_repl_network_getmores_num': None,
        'metrics_repl_network_getmores_totalMillis': None,
        'metrics_repl_network_ops': None,
        'metrics_ttl_passes': None,
        'metrics_ttl_deletedDocuments': None,
        'metrics_operation_writeConflicts': None,
        'metrics_operation_fastmod': None,
        'metrics_operation_scanAndOrder': None,
        'metrics_operation_idhack': None,
        'metrics_document_deleted': None,
        'metrics_document_updated': None,
        'metrics_document_inserted': None,
        'metrics_document_returned': None,
        'connections_current': None,
        'connections_available': None,
        'connections_totalCreated': None,
        'locks_Global_timeAcquiringMicros_r': None,
        'locks_Global_timeAcquiringMicros_W': None,
        'locks_Global_acquireWaitCount_r': None,
        'locks_Global_acquireWaitCount_W': None,
        'locks_Global_acquireCount_r': None,
        'locks_Global_acquireCount_W': None,
        'locks_Global_acquireCount_w': None,
        'locks_Collection_acquireCount_R': None,
        'locks_Database_acquireCount_R': None,
        'locks_Database_acquireCount_r': None,
        'locks_Database_acquireCount_W': None,
        'cursors_clientCursors_size': None,
        'cursors_pinned': None,
        'cursors_totalNoTimeout': None,
        'cursors_timedOut': None,
        'cursors_totalOpen': None,
        'globalLock_totalTime': None,
        'globalLock_currentQueue_total': None,
        'globalLock_currentQueue_writers': None,
        'globalLock_currentQueue_readers': None,
        'globalLock_activeClients_total': None,
        'globalLock_activeClients_writers': None,
        'globalLock_activeClients_readers': None,
        'extra_info_page_faults': None,
        'extra_info_heap_usage_bytes': None,
        'uptimeMillis': None,
        'network_numRequests': None,
        'network_bytesOut': None,
        'network_bytesIn': None,
        'version': None,
        'dur_compression': float,
        'dur_journaledMB': float,
        'dur_commits': None,
        'dur_writeToDataFilesMB': float,
        'dur_commitsInWriteLock': None,
        'dur_earlyCommits': None,
        'dur_timeMs_writeToJournal': None,
        'dur_timeMs_prepLogBuffer': None,
        'dur_timeMs_remapPrivateView': None,
        'dur_timeMs_commits': None,
        'dur_timeMs_commitsInWriteLock': None,
        'dur_timeMs_dt': None,
        'dur_timeMs_writeToDataFiles': None,
        'mem_resident': None,
        'mem_supported': None,
        'mem_virtual': None,
        'mem_mappedWithJournal': None,
        'mem_mapped': None,
        'mem_bits': None,
        'opcountersRepl_getmore': None,
        'opcountersRepl_insert': None,
        'opcountersRepl_update': None,
        'opcountersRepl_command': None,
        'opcountersRepl_query': None,
        'opcountersRepl_delete': None,
        'writeBacksQueued': None,
        'backgroundFlushing_last_finished': None,
        'backgroundFlushing_last_ms': None,
        'backgroundFlushing_flushes': None,
        'opcounters_getmore': None,
        'opcounters_insert': None,
        'opcounters_update': None,
        'opcounters_command': None,
        'opcounters_query': None,
        'opcounters_delete': None,
        'ok': float,
        'asserts_msg': None,
        'asserts_rollovers': None,
        'asserts_regular': None,
        'asserts_warning': None,
        'asserts_user': None,
    }
