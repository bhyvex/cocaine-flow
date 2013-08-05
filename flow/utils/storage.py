#
#   Copyright (c) 2011-2013 Anton Tyurin <noxiouz@yandex.ru>
#    Copyright (c) 2011-2013 Other contributors as noted in the AUTHORS file.
#
#    This file is part of Cocaine.
#
#    Cocaine is free software; you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Cocaine is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import logging
import json
from functools import partial

SEREALIZE = json.dumps
DESEREALIZE = json.loads

from cocaine.services import Service

from flow.utils.decorators import RewrapResult

from cocaine.futures.chain import Chain

FLOW_USERS = "cocaine_flow_users"
FLOW_USERS_TAG = "flow_users"

FLOW_PROFILES = "cocaine_flow_profiles"
FLOW_PROFILES_TAG = "flow_profiles"

FLOW_APPS_DATA = "cocaine_flow_apps_data"
FLOW_APPS = "cocaine_flow_apps"


class Singleton(type):

    def __init__(cls, *args, **kwargs):
        cls.__instance = None
        super(Singleton, cls).__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Singleton, cls).__call__(*args, **kwargs)
            return cls.__instance
        else:
            return cls.__instance


def ensure_connected(func):
    def wrapper(self, callback, *args, **kwargs):
        if self.connected:
            return func(self, callback, *args, **kwargs)
        else:
            self.log.warning("Disconnected. Try reconnect")

            def on_reconnect(res):
                try:
                    res.get()
                    self.log.info("Reconnect to %s" % self.endpoint)
                    return func(self, callback, *args, **kwargs)
                except Exception as err:
                    self.log.error("Unable to reconnect %s" % str(err))
                    callback(res)
            self.backend.async_reconnect(on_reconnect, 1)
    return wrapper


class Storage(object):

    __metaclass__ = Singleton

    log = logging.getLogger()

    def __init__(self):
        self._storage = Service("storage")
        self.log.info("Initialize storage successfully: %s"
                      % self._storage.service_endpoint)

    @property
    def connected(self):
        return self._storage.connected

    @property
    def endpoint(self):
        return self._storage.service_endpoint

    @property
    def backend(self):
        return self._storage

    @ensure_connected
    def find_user(self, callback, name):
        tag = name or "users"

        def on_check(_all):
            out = list()
            for i in _all.get():
                tmp = yield self._storage.read(FLOW_USERS, i)
                out.append(DESEREALIZE(tmp))
            callback(RewrapResult(out))

        self.check_user(tag).then(on_check)

    @ensure_connected
    def remove_user(self, callback, name):
        Chain([partial(self._on_remove_action, callback, FLOW_USERS, name)])

    @ensure_connected
    def store_profile(self, callback, name, data):
        #self._storage.write(FLOW_PROFILES, name, data, ["profiles", name])
        Chain([partial(self._on_write_action, callback,
                       FLOW_PROFILES, name, data, ["profiles"])])

    @ensure_connected
    def remove_profile(self, callback, name):
        Chain([partial(self._on_remove_action, callback, FLOW_PROFILES, name)])

    @ensure_connected
    def write_apps_data(self, callback, name, data):
        Chain([partial(self._on_write_action, callback,
                       FLOW_APPS_DATA, name, data, ["apps_data"])])

    @ensure_connected
    def write_apps(self, callback, name, data):
        Chain([partial(self._on_write_action, callback,
                       FLOW_APPS, name, data, ["apps"])])

    # futures for helpers
    # app
    def list_app_future(self):
        return self._storage.find(FLOW_APPS, ["apps"])

    def read_app_future(self, name):
        return self._storage.read(FLOW_APPS, name)

    # user
    def read_user_future(self, name):
        return self._storage.read(FLOW_USERS, name)

    def write_user_furure(self, name, data):
        return self._storage.write(FLOW_USERS, name, data, [FLOW_USERS_TAG])

    # profile
    def read_profile_future(self, name):
        return self._storage.read(FLOW_PROFILES, name)

    def write_profile_future(self, name, data):
        return self._storage.write(FLOW_PROFILES, name, data, [FLOW_PROFILES_TAG])

    def list_profile_future(self):
        return self._storage.find(FLOW_PROFILES, [FLOW_PROFILES_TAG])

    def delete_profile_future(self, name):
        return self._storage.remove(FLOW_PROFILES, name)



    # actions: DEPRECATED
    def _on_remove_action(self, callback, namespace, item):
        try:
            yield self._storage.remove(namespace, item)
        except Exception as err:
            print err
        finally:
            callback("OK")

    def _on_write_action(self, callback, namespace, item, data, tags):
        try:
            yield self._storage.write(namespace, item, data, tags)
        except Exception as err:
            print err
        finally:
            callback("OK")