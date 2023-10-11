Knock Daemon v2
============

Welcome to Knock Daemon source code repository

https://knock.center

Copyright (C) 2013/2022 Laurent Labatut / Laurent Champagnac

Source code
===============

- We are pep8 compliant (as far as we can, with some exemptions)
- We use a right margin of 360 characters (please don't talk me about 80 chars)
- Daemon code is located inside "./knockdaemon2"
- Unittests are located inside "./knockdaemon2_test"
- All test files must begin with `test_`, should implement setUp & tearDown methods
- All tests must adapt to any running directory
- The whole daemon is backed by gevent (http://www.gevent.org/), and rely on pythonsol lib (https://bitbucket.org/LoloCH/pythonsol)
- The daemon is not using threads but relies on coroutines (gevent greenlets)
- We are still bound to python 2.7 (we will move to python 3 later on)
- We are using docstring (:return, :rtype, :param, :type etc..), PyCharm "noinspection", feel free to use them
- User running tests must be able to raise rlimit to 1048576
- User running tests must be able to fire several commands as sudo without password
Debian : /usr/bin/apt-get,/usr/sbin/dmidecode,/usr/sbin/smartctl,/sbin/sysctl,/usr/bin/uwsgi,/bin/cat

Requirements
===============

- Debian 10 or greater

Unittests
===============

To run unittests, you will need:

- internet outbound access
- nginx running, with a status page replying on "http://127.0.0.1:8090/nginx_status" or "http://127.0.0.1:80/nginx_status"
- port 7900 free and available on your computer (HttpMock will listen onto it)
- apache running, with a status page replying on "http://127.0.0.1:80/server-status", "http://127.0.0.1:8080/server-status", or "http://127.0.0.1:8090/server-status"
- varnish running, "varnishstat -1" and "varnishstat -j" working
- mysql running
- uwsgi running, with at least one application named z_frontends and stats enabled in configuration
- memcached running, listening on localhost or unix domain socket
- redis running (using localhost, default port)
- smartmontools installed
- /etc/resolv.conf set to nameserver 208.67.222.222, nameserver 194.98.65.65, nameserver 213.186.33.99
- sysctl tuned, allowing max open files raised to 1048576

--------

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


