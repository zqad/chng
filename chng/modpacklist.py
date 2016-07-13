# chng - Deploy ATLauncher modpacks
#
# Copyright (C) 2016  Jonas Eriksson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import requests
import logging
import re

from .modpack import ModPack

class ModPackVersion():
    def __init__(self, info):
        self.version = info.get("version")
        self.is_dev = info.get("isDev")
        self.is_recommended = info.get("isRecommended")
        self.can_update = info.get("canUpdate")
        self.has_json = info.get("hasJson")
        self.minecraft = info.get("minecraft")
        self.hash = info.get("hash")

class ModPackInfo():
    def __init__(self, info):
        self.name = info['name']
        self.id = info['id']
        self.description = info.get("description")
        self.code = info.get("code")
        self.leaderboards = info.get("leaderboards")
        self.logging = info.get("logging")
        self.crash_reports = info.get("crashReports")
        self.create_server = info.get("createServer")
        self.position = info.get("position")
        self.type = info.get("type")
        self.website = info.get("websiteURL")
        self.support = info.get("supportURL")

        # Save versions, both as list and dict
        self._versions_dict = {}
        self.dev_versions = []
        for vinfo in info['devVersions']:
            modver = ModPackVersion(vinfo)
            self._versions_dict[vinfo['version']] = modver
            self.dev_versions.append(modver)
        self.versions = []
        for vinfo in info['versions']:
            modver = ModPackVersion(vinfo)
            self._versions_dict[vinfo['version']] = modver
            self.versions.append(modver)
        self._version_latest = None
        if len(self.versions) > 0:
            self._version_latest = self.versions[0]
        elif len(self.dev_versions) > 0:
            self._version_latest = self.dev_versions[0]

    def to_modpack(self, directory, version=None):
        # Figure out the correct version
        modver = None
        if version is None:
            modver = self._version_latest
        else:
            modver = self._versions_dict.get(version)
        if modver is None:
            raise Exception("Unable to select version")

        # Create modpack instance
        return ModPack(self.name, modver.version, directory)

class ModPackList():
    BASE_URL = "http://download.nodecdn.net/containers/atl/"

    def __init__(self):
        # Download the packs.json
        packs_url = self.BASE_URL + "launcher/json/packs.json"
        request = requests.get(packs_url)
        self._modpackinfos = {}
        self._modpackinfos_safe_name = {}
        for mod in request.json():
            modpackinfo = ModPackInfo(mod)
            self._modpackinfos[mod['name']] = modpackinfo
            # Save the safe name as well, so that we can use it for lookups
            safe_name = re.sub("[^A-Za-z0-9]", "", mod['name'])
            self._modpackinfos_safe_name[safe_name] = modpackinfo

    def modpackinfos(self):
        return list(self._modpackinfos.values())

    def get_modpackinfo(self, name):
        modpackinfo = self._modpackinfos.get(name)
        if modpackinfo is None:
            # No match for the official name? Try matching using the safe name
            safe_name = re.sub("[^A-Za-z0-9]", "", name)
            modpackinfo = self._modpackinfos_safe_name.get(safe_name)
        return modpackinfo
