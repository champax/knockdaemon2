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

D_UWSGI_SAMPLE = {
    "version": "2.0.7-debian",
    "listen_queue": 0,
    "listen_queue_errors": 0,
    "signal_queue": 0,
    "load": 0,
    "pid": 74133,

    "uid": 33,
    "gid": 33,
    "cwd": "/var/www/totoo_frontends",
    "locks": [
        {
            "user 0": 0
        },
        {
            "signal": 0
        },
        {
            "filemon": 0
        },
        {
            "timer": 0
        },
        {
            "rbtimer": 0
        },
        {
            "cron": 0
        },
        {
            "rpc": 0
        },
        {
            "snmp": 0
        }
    ],
    "sockets": [
        {
            "name": "/run/uwsgi/app/totoo_frontends/socket",
            "proto": "uwsgi",
            "queue": 0,
            "max_queue": 0,
            "shared": 0,
            "can_offload": 0
        }
    ],
    "workers": [
        {
            "id": 1,
            "pid": 74141,
            "accepting": 1,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "idle",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 1462230277,
            "respawn_count": 1,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        },
        {
            "id": 0,
            "pid": 0,
            "accepting": 0,
            "requests": 0,
            "delta_requests": 0,
            "exceptions": 0,
            "harakiri_count": 0,
            "signals": 0,
            "signal_queue": 0,
            "status": "cheap",
            "rss": 0,
            "vsz": 0,
            "running_time": 0,
            "last_spawn": 0,
            "respawn_count": 0,
            "tx": 0,
            "avg_rt": 0,
            "apps": [
            ],
            "cores": [
                {
                    "id": 0,
                    "requests": 0,
                    "static_requests": 0,
                    "routed_requests": 0,
                    "offloaded_requests": 0,
                    "write_errors": 0,
                    "read_errors": 0,
                    "in_request": 0,
                    "vars": [
                    ]
                }
            ]
        }
    ]
}
