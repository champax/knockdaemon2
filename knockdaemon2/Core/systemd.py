# -*- coding: utf-8 -*-
"""
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

# Written by Aleksandr Aleksandrov <aleksandr.aleksandrov@emlid.com>
#
# Copyright (c) 2016, Emlid Limited
# All rights reserved.
#
# Redistribution and use in source and binary forms,
# with or without modification,
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import logging

import dbus

logger = logging.getLogger(__name__)


class SystemdManager(object):
    UNIT_INTERFACE = "org.freedesktop.systemd1.Unit"
    SERVICE_UNIT_INTERFACE = "org.freedesktop.systemd1.Service"

    def __init__(self):
        self.__bus = dbus.SystemBus()

    def start_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()

        if interface is None:
            return False

        try:
            interface.StartUnit(unit_name, mode)
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def stop_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()

        if interface is None:
            return False

        try:
            interface.StopUnit(unit_name, mode)
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def restart_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()

        if interface is None:
            return False

        try:
            interface.RestartUnit(unit_name, mode)
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def enable_unit(self, unit_name):
        interface = self._get_interface()

        if interface is None:
            return False

        try:
            interface.EnableUnitFiles([unit_name],
                                      dbus.Boolean(False),
                                      dbus.Boolean(True))
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def disable_unit(self, unit_name):
        interface = self._get_interface()

        if interface is None:
            return False

        try:
            interface.DisableUnitFiles([unit_name], dbus.Boolean(False))
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def _get_unit_file_state(self, unit_name):
        interface = self._get_interface()

        if interface is None:
            return None

        try:
            state = interface.GetUnitFileState(unit_name)
            return state
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def _get_interface(self):
        try:
            obj = self.__bus.get_object("org.freedesktop.systemd1",
                                        "/org/freedesktop/systemd1")
            return dbus.Interface(obj, "org.freedesktop.systemd1.Manager")
        except dbus.exceptions.DBusException as error:
            print(error)
            return None

    def get_pid(self, unit_name):
        pid = self._get_unit_property(unit_name, self.SERVICE_UNIT_INTERFACE, 'MainPID')
        try:
            if isinstance(pid, bytes):
                pid = int(pid.decode('utf8'), 10)
            elif isinstance(pid, str):
                pid = int(pid, 10)
            return pid
        except Exception as e:
            logger.warning("Cant cast to int %s:%s", type(pid), pid)
            raise e

    def get_active_state(self, unit_name):
        properties = self._get_unit_properties(unit_name, self.UNIT_INTERFACE)

        if properties is None:
            return False

        try:
            state = properties["ActiveState"].encode("utf8")
            return state
        except KeyError:
            return False

    def is_active(self, unit_name):
        unit_state = self.get_active_state(unit_name)
        return unit_state == b"active"

    def is_failed(self, unit_name):
        unit_state = self.get_active_state(unit_name)
        return unit_state == b"failed"

    def get_error_code(self, unit_name):
        service_properties = self._get_unit_properties(unit_name, self.SERVICE_UNIT_INTERFACE)

        if service_properties is None:
            return None

        return self._get_exec_status(service_properties)

    # noinspection PyMethodMayBeStatic
    def _get_exec_status(self, properties):
        try:
            exec_status = int(properties["ExecMainStatus"])
            return exec_status
        except KeyError:
            return None

    # noinspection PyMethodMayBeStatic
    def _get_result(self, properties):
        try:
            result = properties["Result"].encode("utf8")
            return result
        except KeyError:
            return False

    def _get_unit_properties(self, unit_name, unit_interface):
        properties_interface = self._get_unit_interface(unit_name)
        try:
            return properties_interface.GetAll(unit_interface)

        except dbus.exceptions.DBusException as error:
            print(error)
            return None

    def _get_unit_property(self, unit_name, unit_interface, property_name):
        properties_interface = self._get_unit_interface(unit_name)
        try:
            return properties_interface.Get(unit_interface, property_name)

        except dbus.exceptions.DBusException as error:
            print(error)
            return None

    def _get_unit_interface(self, unit_name):
        interface = self._get_interface()

        if interface is None:
            return None

        try:
            unit_path = interface.LoadUnit(unit_name)

            obj = self.__bus.get_object(
                "org.freedesktop.systemd1", unit_path)

            properties_interface = dbus.Interface(
                obj, "org.freedesktop.DBus.Properties")
            return properties_interface

        except dbus.exceptions.DBusException as error:
            print(error)
            return None


if __name__ == "__main__":
    s = SystemdManager()
    print(s.get_pid("ngnix.service"))
