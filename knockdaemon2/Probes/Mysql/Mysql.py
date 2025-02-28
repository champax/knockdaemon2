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
import os.path

from pysolbase.FileUtility import FileUtility
from pysolbase.SolBase import SolBase
from pysolmysql.Mysql.MysqlApi import MysqlApi

from knockdaemon2.Api.ButcherTools import ButcherTools
from knockdaemon2.Core.KnockProbe import KnockProbe

logger = logging.getLogger(__name__)


class Mysql(KnockProbe):
    """
    Probe
    """

    MYSQL_CONF_DIR = "/etc/mysql"

    # Debian : extract creds from file
    MYSQL_CONFIG_FILES = [
        # Will use daemon configuration
        # As /etc/mysql/debian.cnf is deprecated, will be removed and this was the only file containing login/pwd
        ("V2", None),
        # Old ones
        ("V1", "/etc/mysql/debian.cnf"),
    ]

    KEYS = [
        # float => per second
        # int   => current (aka cur)
        # k.x   => internal

        # Status :
        # 0  : RUNNING
        # >0 : FAILED

        # Format is
        # - native counter
        # - type (float|int)
        # - target counter
        # - target cumulative counter (can be None)

        ("k.mysql.exec.ss.ms", "float", "k.mysql.exec.ss.ms", None),
        ("k.mysql.started", "int", "k.mysql.started", None),

        ("Aborted_clients", "float", "k.mysql.conn.abort.client", None),
        ("Aborted_connects", "float", "k.mysql.conn.abort.connect", None),
        ("Connections", "float", "k.mysql.conn.total", None),

        ("Bytes_received", "float", "k.mysql.bytes.recv", None),
        ("Bytes_sent", "float", "k.mysql.bytes.sent", None),

        ("Com_delete", "float", "k.mysql.com.delete", None),
        ("Com_insert", "float", "k.mysql.com.insert", None),
        ("Com_select", "float", "k.mysql.com.select", None),
        ("Com_update", "float", "k.mysql.com.update", None),

        ("Com_begin", "float", "k.mysql.com.begin", None),
        ("Com_commit", "float", "k.mysql.com.commit", None),
        ("Com_rollback", "float", "k.mysql.com.rollback", None),

        ("Com_slave_start", "float", "k.mysql.com.slave.start", None),
        ("Com_slave_stop", "float", "k.mysql.com.slave.stop", None),

        # Mariadb
        ("Com_start_slave", "float", "k.mysql.com.slave.start", None),
        ("Com_stop_slave", "float", "k.mysql.com.slave.stop", None),

        ("Created_tmp_disk_tables", "float", "k.mysql.tmp.disktables", None),
        ("Created_tmp_files", "float", "k.mysql.tmp.files", None),
        ("Created_tmp_tables", "float", "k.mysql.tmp.tables", None),

        ("Innodb_data_fsyncs", "float", "k.mysql.inno.fsyncs", None),
        ("Innodb_data_reads", "float", "k.mysql.inno.count.read", None),
        ("Innodb_data_writes", "float", "k.mysql.inno.count.write", None),
        ("Innodb_data_read", "float", "k.mysql.inno.bytes.read", None),
        ("Innodb_data_written", "float", "k.mysql.inno.bytes.write", None),

        # This is removed maria 10.10
        # https://mariadb.com/kb/en/innodb-status-variables/#innodb_rows_deleted
        ("Innodb_rows_deleted", "float", "k.mysql.inno.rows.delete", None),  # now is Handler_delete
        ("Innodb_rows_inserted", "float", "k.mysql.inno.rows.insert", None),  # removed, no equivalent
        ("Innodb_rows_read", "float", "k.mysql.inno.rows.select", None),  # Sum of "Handler_read_"
        ("Innodb_rows_updated", "float", "k.mysql.inno.rows.update", None),  # now is Handler_update

        # Maria >= 10.10
        ("Handler_delete", "float", "k.mysql.inno.rows.delete", None),

        ("Handler_read_first", "float", "k.mysql.inno.rows.read_first", "k.mysql.inno.rows.select"),
        ("Handler_read_key", "float", "k.mysql.inno.rows.read_key", "k.mysql.inno.rows.select"),
        ("Handler_read_last", "float", "k.mysql.inno.rows.read_last", "k.mysql.inno.rows.select"),
        ("Handler_read_next", "float", "k.mysql.inno.rows.read_next", "k.mysql.inno.rows.select"),
        ("Handler_read_prev", "float", "k.mysql.inno.rows.read_prev", "k.mysql.inno.rows.select"),
        ("Handler_read_retry", "float", "k.mysql.inno.rows.read_retry", "k.mysql.inno.rows.select"),
        ("Handler_read_rnd", "float", "k.mysql.inno.rows.read_rnd", "k.mysql.inno.rows.select"),
        ("Handler_read_rnd_deleted", "float", "k.mysql.inno.rows.read_rnd_deleted", "k.mysql.inno.rows.select"),
        ("Handler_read_rnd_next", "float", "k.mysql.inno.rows.read_next", "k.mysql.inno.rows.select"),

        ("Handler_update", "float", "k.mysql.inno.rows.update", None),

        # -----------------------
        # MEMORY POOLS
        # -----------------------

        # Inno pool bytes clean and dirty (hacked) (bytes)
        ("k.mysql.inno.pool.cur_clean_bytes", "int", "k.mysql.inno.pool.cur_clean_bytes", None),
        ("k.mysql.inno.pool.cur_dirty_bytes", "int", "k.mysql.inno.pool.cur_dirty_bytes", None),
        # Inno log buffer in ram (bytes)
        ("innodb_log_buffer_size", "int", "k.mysql.inno.pool.cur_logbuffer_bytes", None),
        # Inno additional buffer (bytes)
        # Removed in mariadb 10.2
        ("innodb_additional_mem_pool_size", "int", "k.mysql.inno.pool.cur_addpool_bytes", None),
        # Myisam key buffer in ram (bytes)
        ("key_buffer_size", "int", "k.mysql.myisam.pool.cur_keybuffer_bytes", None),
        # Query cache buffer in ram (bytes)
        ("query_cache_size", "int", "k.mysql.qcache.pool.cur_bytes", None),
        # Connection allocated ram (Threads_connected * bytes per connection)
        # Bytes per connection approx : join_buffer_size + sort_buffer_size + read_buffer_size + read_rnd_buffer_size + binlog_cache_size
        # This is a maximum (buffers can be allocated or not depending on underlying requests)
        ("k.mysql.conn.pool.cur_bytes", "int", "k.mysql.conn.pool.cur_bytes", None),
        # Thread allocated ram (Threads_cached * (thread_stack + net_buffer_length + net_buffer_length))
        ("k.mysql.thread.pool.cur_bytes", "int", "k.mysql.thread.pool.cur_bytes", None),

        # QUERY CACHE HITS
        # Query hit rate = qcache_hits / (qcache_hits + com_select)
        ("Qcache_hits", "int", "k.mysql.com.select_qcache_hit", None),

        # OPEN STUFF
        ("Open_files", "int", "k.mysql.open.cur.files", None),
        ("Open_tables", "int", "k.mysql.open.cur.tables", None),
        ("Opened_files", "float", "k.mysql.open.total.files", None),
        ("Opened_tables", "float", "k.mysql.open.total.tables", None),

        # THREAD STUFF
        ("Threads_cached", "int", "k.mysql.thread.cur.cached", None),
        ("Threads_connected", "int", "k.mysql.thread.cur.connected", None),
        ("Threads_running", "int", "k.mysql.thread.cur.running", None),

        # Lag in second (failed : -1, no repli ; 0, repli : value from server)
        ("Seconds_Behind_Master", "float", "k.mysql.repli.cur.lag_sec", None),

        # Max stuff / limit etc..

        # Compared to => Threads_Connected
        ("max_connections", "int", "k.mysql.limit.max_connections", None),
        # Compared to => Open_tables
        ("table_open_cache", "int", "k.mysql.limit.table_open_cache", None),
    ]

    def __init__(self):
        """
        Init
        """

        KnockProbe.__init__(self)
        self.category = "/sql/mysql"

    # noinspection PyMethodMayBeStatic
    def _parse_config_debian(self):
        """
        Parse config file
        :return: tuple (login,pwd,socket,file used,version used), tuple (None, None, None, None, None)
        :rtype tuple
        """

        for cur_version, cur_file in Mysql.MYSQL_CONFIG_FILES:
            try:
                if cur_version == "V1":
                    # File is root access only, try to load
                    buf = None

                    if FileUtility.is_file_exist(cur_file):
                        buf = FileUtility.file_to_textbuffer(cur_file, "ascii")

                    # Check
                    if not buf:
                        # IOError 13 possible (file is root only) Retry invoke, invoke sudo (unittest mainly)
                        logger.debug("Load failed, retry invoke, fallback invoke now")
                        cmd = "cat {0}".format(cur_file)
                        ec, so, se = ButcherTools.invoke(cmd)
                        if ec != 0:
                            logger.debug("invoke failed, retry sudo, ec=%s, so=%s, se=%s", ec, so, se)
                            # Retry sudo
                            cmd = "sudo cat {0}".format(cur_file)
                            ec, so, se = ButcherTools.invoke(cmd)
                            if ec != 0:
                                logger.info("invoke failed (sudo fallback), give up, ec=%s, so=%s, se=%s", ec, so, se)
                                continue
                        # Ok
                        buf = so

                    # Split
                    logger.debug("Buffer loaded, parsing...")
                    ar = buf.split("\n")
                    cur_section = None
                    cur_login = None
                    cur_pwd = None
                    cur_socket = None
                    for r in ar:
                        r = r.strip()

                        # Empty
                        if len(r) == 0:
                            continue
                        # Comment
                        if r[0] == "\"":
                            continue

                        # Section
                        if r.find("[") == 0:
                            # Section start
                            cur_section = r
                            logger.debug("Section set, cur_section=%s", cur_section)
                            continue

                        if not cur_section == "[client]":
                            continue

                        # Item in cur_section
                        # Do not log this... (pwd)
                        # logger.debug("Parsing now, r=%s", r)
                        row_ar = r.split("=", 1)
                        row_ar[0] = row_ar[0].strip()
                        row_ar[1] = row_ar[1].strip()
                        if row_ar[0] == "user":
                            cur_login = row_ar[1]
                        elif row_ar[0] == "password":
                            cur_pwd = row_ar[1]
                        elif row_ar[0] == "socket":
                            cur_socket = row_ar[1]

                    # Check
                    if not cur_login or not cur_pwd or not cur_socket:
                        if buf is not None:
                            buf = buf.replace("\n", "")
                        logger.info("Unable to detect creds, buf=%s", buf)
                        continue

                    # Ok
                    t_out = cur_login, cur_pwd, cur_socket, cur_file, cur_version
                elif cur_version == "V2":
                    # We use daemon configuration if we have (mysql_login based)
                    if "mysql_login" in self.d_local_conf and self.d_local_conf["mysql_login"] is not None and len(self.d_local_conf["mysql_login"]) > 0:
                        t_out = self.d_local_conf["mysql_login"], self.d_local_conf["mysql_password"], self.d_local_conf["mysql_socket"], "", cur_version
                else:
                    raise Exception("Invalid version=%s" % cur_version)

                # This one is OK
                logger.debug("Located stuff, t_out=%s", t_out)
                return t_out

            except Exception as e:
                logger.warning("Parse failed, ex=%s", SolBase.extostr(e))

        # All parsing failed
        return None, None, None, None, None

    def _execute_linux(self):
        """
        Execute
        """
        self._execute_native()

    def _execute_native(self):
        """
        Exec, native
        """

        # Check we have the mysql DIR (in this case we go ahead, otherwise we do not go)
        if not os.path.exists(self.MYSQL_CONF_DIR):
            return
        elif not os.path.isdir(self.MYSQL_CONF_DIR):
            return

        id_mysql = "default"

        try:
            # Fetch (MUST NOT FAILS)
            login, pwd, soc, config_file, config_version = self._parse_config_debian()

            self._execute_via_creds(login, pwd, soc, id_mysql)
        except Exception as e:
            # Notify instance down (type : 0)
            logger.warning("Execute failed, signaling instance down, started=0, ex=%s", SolBase.extostr(e))
            self.notify_value_n("k.mysql.started", {"ID": id_mysql}, 0)
            return

    def _execute_via_creds(self, login, pwd, soc, id_mysql):
        """
        Execute
        :param login: str:
        :type login: str 
        :param pwd: str
        :type pwd: str
        :param soc: str
        :type soc: str
        :param id_mysql: str
        :type id_mysql: str
        """

        # Check
        if not login:
            # FATAL
            # Notify instance down (type : 0)
            logger.info("_parse_config returned None, signaling instance down, started=0")
            self.notify_value_n("k.mysql.started", {"ID": id_mysql}, 0)
            return

        # Config OK
        d_conf = {
            "unix": soc,
            "port": 3306,
            "database": None,
            "user": login,
            "password": pwd,
            "autocommit": True,
            "pool_name": "p1",  # not used
            "pool_size": 5  # not used
        }

        # -----------------------------
        # MYSQL FETCH
        # -----------------------------

        # Fetch variables
        ms = SolBase.mscurrent()

        logger.debug("Mysql connect/exec now")
        ar_show_global_status = MysqlApi.exec_n(d_conf, "show global status;")

        logger.debug("Mysql connect/exec now")
        ar_show_slave_status = MysqlApi.exec_n(d_conf, "show slave status;")

        logger.debug("Mysql connect/exec now")
        ar_show_global_variables = MysqlApi.exec_n(d_conf, "show global variables;")

        # Stats
        # https://mariadb.com/kb/en/mysqlinnodb_index_stats/
        # => later

        # https://mariadb.com/kb/en/mysqlinnodb_table_stats/
        try:
            ar_innodb_table_stats = MysqlApi.exec_n(d_conf, "SELECT * FROM mysql.innodb_table_stats;")
            logger.info("innodb_table_stats OK, len=%s", len(ar_innodb_table_stats))
        except Exception as e:
            logger.info("innodb_table_stats failed (non fatal), ex=%s", SolBase.extostr(e))
            ar_innodb_table_stats = None

        # https://mariadb.com/kb/en/user-statistics/
        try:
            ar_user_stats = MysqlApi.exec_n(d_conf, "SELECT * FROM INFORMATION_SCHEMA.USER_STATISTICS;")
            logger.info("USER_STATISTICS OK, len=%s", len(ar_user_stats))
        except Exception as e:
            logger.info("USER_STATISTICS failed (non fatal), ex=%s", SolBase.extostr(e))
            ar_user_stats = None

        # https://mariadb.com/kb/en/information-schema-client_statistics-table/
        # => later

        # https://mariadb.com/kb/en/information-schema-index_statistics-table/
        try:
            ar_index_stats = MysqlApi.exec_n(d_conf, "SELECT * FROM information_schema.INDEX_STATISTICS;")
            logger.info("INDEX_STATISTICS OK, len=%s", len(ar_index_stats))
        except Exception as e:
            logger.info("INDEX_STATISTICS failed (non fatal), ex=%s", SolBase.extostr(e))
            ar_index_stats = None

        # https://mariadb.com/kb/en/information-schema-table_statistics-table/
        try:
            ar_table_stats = MysqlApi.exec_n(d_conf, "SELECT * FROM information_schema.TABLE_STATISTICS;")
            logger.info("TABLE_STATISTICS OK, len=%s", len(ar_table_stats))
        except Exception as e:
            logger.info("TABLE_STATISTICS failed (non fatal), ex=%s", SolBase.extostr(e))
            ar_table_stats = None

        # Process
        self.process_mysql_buffers(
            ar_show_global_status, ar_show_slave_status, ar_show_global_variables,
            ar_table_stats, ar_user_stats, ar_index_stats,
            ar_innodb_table_stats,
            id_mysql, SolBase.msdiff(ms)
        )

    def process_mysql_buffers(
            self,
            ar_show_global_status, ar_show_slave_status, ar_show_global_variables,
            ar_table_stats, ar_user_stats, ar_index_stats,
            ar_innodb_table_stats,
            mysql_id, ms_mysql):
        """
        Process mysql buffer
        :param ar_show_global_status: list
        :type ar_show_global_status: list
        :param ar_show_slave_status: list
        :type ar_show_slave_status: list
        :param ar_show_global_variables: list
        :type ar_show_global_variables: list
        :param ar_table_stats: list,None
        :type ar_table_stats: list,None
        :param ar_user_stats: list,None
        :type ar_user_stats: list,None
        :param ar_index_stats: list,None
        :type ar_index_stats: list,None
        :param ar_innodb_table_stats: list,None
        :type ar_innodb_table_stats: list,None
        :param mysql_id: str
        :type mysql_id: str
        :param ms_mysql: float
        :type ms_mysql: float
        """

        # Allocate output dict
        d_out = dict()

        # Notify exec time
        self.notify_value_n("k.mysql.exec.ss.ms", {"ID": mysql_id}, ms_mysql)

        # -----------------------------
        # SHOW GLOBAL STATUS
        # -----------------------------

        # Process
        logger.debug("Mysql global status ok, got ar_show_global_status, values below, building output")
        for d in ar_show_global_status:
            logger.debug("Got row")
            for k, v in d.items():
                logger.debug("Got k=%s, v=%s, type=%s", k, v, type(v))

            key = d["Variable_name"]
            value = d["Value"]
            d_out[key] = value

        # -----------------------------
        # SHOW GLOBAL VARIABLES
        # -----------------------------

        # Process
        logger.debug("Mysql global variables ok, got ar_show_global_variables, values below, building output")
        for d in ar_show_global_variables:
            logger.debug("Got row")
            for k, v in d.items():
                logger.debug("Got k=%s, v=%s, type=%s", k, v, type(v))

            key = d["Variable_name"]
            value = d["Value"]
            d_out[key] = value

        # -----------------------------
        # SPECIAL
        # -----------------------------

        try:
            # Special processing - Innodb_buffer_pool_bytes_data (clean+dirty) / Innodb_buffer_pool_bytes_dirty (dirty only)
            pool_total_bytes = int(d_out.get("Innodb_buffer_pool_bytes_data", 0))
            pool_dirty_bytes = int(d_out.get("Innodb_buffer_pool_bytes_dirty", 0))
            pool_clean_bytes = pool_total_bytes - pool_dirty_bytes
            d_out["k.mysql.inno.pool.cur_clean_bytes"] = pool_clean_bytes
            d_out["k.mysql.inno.pool.cur_dirty_bytes"] = pool_dirty_bytes

            # Special processing : query_cache on/off (type 0 or OFF : OFF, size 0 : OFF)
            # Hum, in fact, no trigger on query_cache => this is usefull only for the log, lets keep it
            q_type = d_out.get("query_cache_type", "0").lower()
            q_max = d_out.get("query_cache_size", 0)
            if q_type == "0" or q_type == "off":
                q_enabled = False
            elif q_max == 0:
                q_enabled = False
            else:
                q_enabled = True
            logger.debug("q_enabled=%s, q_type=%s, q_max=%s", q_enabled, q_type, q_max)

            # Special processing : Connection allocated ram (Threads_connected * bytes per connection)
            # Bytes per connection approx : join_buffer_size + sort_buffer_size + read_buffer_size + read_rnd_buffer_size + binlog_cache_size
            # This is a maximum (buffers can be allocated or not depending on underlying requests)
            conn_cur = int(d_out.get("Threads_connected", 0))
            bytes_per_conn = \
                int(d_out.get("join_buffer_size", 0)) + \
                int(d_out.get("sort_buffer_size", 0)) + \
                int(d_out.get("read_buffer_size", 0)) + \
                int(d_out.get("read_rnd_buffer_size", 0)) + \
                int(d_out.get("binlog_cache_size", 0))
            d_out["k.mysql.conn.pool.cur_bytes"] = conn_cur * bytes_per_conn

            # Special processing : Thread allocated ram (Threads_cached * (thread_stack + net_buffer_length + net_buffer_length))
            thread_cached = int(d_out.get("Threads_cached", 0))
            stack_bytes = int(d_out.get("thread_stack", 0))
            net_bytes = int(d_out.get("net_buffer_length", 0))
            d_out["k.mysql.thread.pool.cur_bytes"] = thread_cached * (stack_bytes + net_bytes + net_bytes)

            # Debug
            debug_total = 0
            debug_inno_clean = int(d_out.get("k.mysql.inno.pool.cur_clean_bytes", 0)) / 1024 / 1024
            debug_total += debug_inno_clean
            debug_inno_dirty = int(d_out.get("k.mysql.inno.pool.cur_dirty_bytes", 0)) / 1024 / 1024
            debug_total += debug_inno_dirty
            debug_inno_logbuf = int(d_out.get("innodb_log_buffer_size", 0)) / 1024 / 1024
            debug_total += debug_inno_logbuf
            debug_inno_addmem = int(d_out.get("innodb_additional_mem_pool_size", 0)) / 1024 / 1024
            debug_total += debug_inno_addmem
            debug_isam_keybuf = int(d_out.get("key_buffer_size", 0)) / 1024 / 1024
            debug_total += debug_isam_keybuf
            debug_qcache = int(d_out.get("query_cache_size", 0)) / 1024 / 1024
            debug_total += debug_qcache
            debug_conn_pool = int(d_out.get("k.mysql.conn.pool.cur_bytes", 0)) / 1024 / 1024
            debug_total += debug_conn_pool
            debug_thread_pool = int(d_out.get("k.mysql.thread.pool.cur_bytes", 0)) / 1024 / 1024
            debug_total += debug_thread_pool

            logger.debug(
                "total=%s, inno.clean/dirty/logbuf/add=%s/%s/%s/%s, isam=%s, qcache=%s, conn=%s, thread=%s",
                debug_total,
                debug_inno_clean,
                debug_inno_dirty,
                debug_inno_logbuf,
                debug_inno_addmem,
                debug_isam_keybuf,
                debug_qcache,
                debug_conn_pool,
                debug_thread_pool)
        except Exception as e:
            logger.warning("Abnormal exception in special processing, ex=%s", SolBase.extostr(e))

        # -----------------------------
        # SHOW SLAVE STATUS
        # -----------------------------

        # Process (we got one dict in ar_out, fetch direct)
        logger.debug("Mysql slave status ok, got ar_show_slave_status, building output")
        logger.debug("Mysql ar_show_slave_status=%s", ar_show_slave_status)
        try:
            repli_lag_sec = 0
            if len(ar_show_slave_status) == 1:
                # Here, replication MUST work (we have output from show slave status)
                v = ar_show_slave_status[0].get("Seconds_Behind_Master", None)
                s_io_running = ar_show_slave_status[0].get("Slave_IO_Running", "").lower()
                s_sql_running = ar_show_slave_status[0].get("Slave_SQL_Running", "").lower()

                # Detect both threads running
                if s_io_running == "yes" and s_sql_running == "yes":
                    s_all_running = True
                else:
                    s_all_running = False

                # Seconds lag : None, null, or set
                if not v:
                    logger.debug("Found direct v=None")
                    if s_all_running:
                        repli_lag_sec = 0
                    else:
                        # Not all threads running, signal it
                        repli_lag_sec = -2
                elif isinstance(v, str) and v.lower() == "null":
                    logger.debug("Found direct bytes/str null, v=%s", v)
                    if s_all_running:
                        repli_lag_sec = 0
                    else:
                        # Not all threads running, signal it
                        repli_lag_sec = -2
                elif isinstance(v, int):
                    logger.debug("Found direct int, v=%s", v)
                    repli_lag_sec = v
                else:
                    logger.debug("Found indirect int, v=%s, type=%s", v, type(v))
                    repli_lag_sec = int(v)

                # Ok
                logger.debug("Found v=%s, repli_lag_sec=%s, io/sql/all=%s/%s/%s", v, repli_lag_sec, s_io_running, s_sql_running, s_all_running)
            else:
                logger.debug("Found no record, repli_lag_sec=%s", repli_lag_sec)

            # Set in output dict
            d_out["Seconds_Behind_Master"] = repli_lag_sec
        except Exception as e:
            logger.warning("Slave status failed, ex=%s", SolBase.extostr(e))
            # Fallback
            d_out["Seconds_Behind_Master"] = -1

        # Log
        logger.debug("Got d_out[Seconds_Behind_Master]=%s", d_out["Seconds_Behind_Master"])

        # -----------------------------
        # ar_table_stats
        # -----------------------------

        # GOT : TABLE_SCHEMA, TABLE_NAME, ROWS_READ, ROWS_CHANGED, ROWS_CHANGED_X_INDEXES
        if ar_table_stats is not None:
            for d in ar_table_stats:
                schema = d["TABLE_SCHEMA"].strip()
                table = d["TABLE_NAME"].strip()
                tags = {"ID": mysql_id, "schema": schema, "table": table}
                d_values = dict()
                for f in ["ROWS_READ", "ROWS_CHANGED", "ROWS_CHANGED_X_INDEXES"]:
                    v = float(d[f])
                    d_values[f] = v
                self.notify_value_n("k.mysql.stats.table", tags, counter_value=0.0, d_values=d_values)
        else:
            logger.info("ar_table_stats None")

        # -----------------------------
        # ar_user_stats
        # -----------------------------

        # GOT : USER, TOTAL_CONNECTIONS, CONCURRENT_CONNECTIONS, CONNECTED_TIME,
        # GOT : BUSY_TIME, CPU_TIME, BYTES_RECEIVED, BYTES_SENT, BINLOG_BYTES_WRITTEN,
        # GOT : ROWS_READ, ROWS_SENT, ROWS_DELETED, ROWS_INSERTED, ROWS_UPDATED,
        # GOT : SELECT_COMMANDS, UPDATE_COMMANDS, OTHER_COMMANDS,
        # GOT : COMMIT_TRANSACTIONS, ROLLBACK_TRANSACTIONS,
        # GOT : DENIED_CONNECTIONS, LOST_CONNECTIONS, ACCESS_DENIED, EMPTY_QUERIES, TOTAL_SSL_CONNECTIONS, MAX_STATEMENT_TIME_EXCEEDED,

        if ar_user_stats is not None:
            for d in ar_user_stats:
                user = d["USER"].strip()
                tags = {"ID": mysql_id, "user": user}
                d_values = dict()
                for f in ["TOTAL_CONNECTIONS", "CONCURRENT_CONNECTIONS", "CONNECTED_TIME", "BUSY_TIME", "CPU_TIME",
                          "BYTES_RECEIVED", "BYTES_SENT",
                          "BINLOG_BYTES_WRITTEN", "ROWS_READ", "ROWS_SENT", "ROWS_DELETED", "ROWS_INSERTED", "ROWS_UPDATED",
                          "SELECT_COMMANDS", "UPDATE_COMMANDS", "OTHER_COMMANDS", "COMMIT_TRANSACTIONS", "ROLLBACK_TRANSACTIONS",
                          "DENIED_CONNECTIONS", "LOST_CONNECTIONS", "ACCESS_DENIED",
                          "EMPTY_QUERIES", "TOTAL_SSL_CONNECTIONS", "MAX_STATEMENT_TIME_EXCEEDED", ]:
                    v = float(d[f])
                    d_values[f] = v
                self.notify_value_n("k.mysql.stats.user", tags, 0.0, d_values=d_values)
        else:
            logger.info("ar_user_stats None")

        # -----------------------------
        # ar_index_stats
        # -----------------------------

        if ar_index_stats is not None:
            for d in ar_index_stats:
                schema = d["TABLE_SCHEMA"].strip()
                table = d["TABLE_NAME"].strip()
                index = d["INDEX_NAME"].strip()
                tags = {"ID": mysql_id, "schema": schema, "table": table, "index": index}
                d_values = dict()
                for f in ["ROWS_READ"]:
                    v = float(d[f])
                    d_values[f] = v
                self.notify_value_n("k.mysql.stats.index", tags, 0.0, d_values=d_values)
        else:
            logger.info("ar_index_stats None")

        # -----------------------------
        # ar_innodb_table_stats
        # -----------------------------

        if ar_innodb_table_stats is not None:
            for d in ar_innodb_table_stats:
                schema = d["database_name"].strip()
                table = d["table_name"].strip()
                tags = {"ID": mysql_id, "schema": schema, "table": table}
                d_values = dict()
                for f in ["n_rows", "clustered_index_size", "sum_of_other_index_sizes"]:
                    v = float(d[f])
                    d_values[f] = v
                self.notify_value_n("k.mysql.stats.innodb_table", tags, 0.0, d_values=d_values)
        else:
            logger.info("ar_index_stats None")

        # -----------------------------
        # Debug
        # -----------------------------
        for k, v in d_out.items():
            logger.debug("Final, k=%s, v=%s, vtype=%s", k, v, type(v))

        # Browse our stuff and try to locate
        d_accumulate = dict()
        for k, knock_type, knock_key, knock_key_accumulate in Mysql.KEYS:
            # Try
            if k not in d_out:
                if k.find("k.mysql.") != 0:
                    logger.debug("Unable to locate k=%s in d_out", k)
                continue

            # Ok, fetch and cast
            v = d_out[k]
            if knock_type == "int":
                v = int(v)
            elif knock_type == "float":
                v = float(v)
            else:
                logger.warning("Not managed type=%s", knock_type)

            # Ok, notify it (no discovery, we assume 1 instance per box)

            # Push it
            self.notify_value_n(knock_key, {"ID": mysql_id}, v)

            # Accumulate
            if knock_key_accumulate is not None:
                # We need to accumulate and push at the end
                if knock_key_accumulate not in d_accumulate:
                    d_accumulate[knock_key_accumulate] = v
                else:
                    d_accumulate[knock_key_accumulate] = d_accumulate[knock_key_accumulate] + v

        # Push accumulated
        for knock_key_accumulate, v in d_accumulate.items():
            self.notify_value_n(knock_key_accumulate, {"ID": mysql_id}, v)

        # Over, instance up
        logger.debug("Execute ok, signaling instance up, started=1")
        self.notify_value_n("k.mysql.started", {"ID": mysql_id}, 1)
