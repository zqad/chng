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

from .fileutils import AutoUnpackableFile

import re
import tempfile
from xml.etree import ElementTree
from pathlib import Path
import urllib.parse
import logging

class ModFile(AutoUnpackableFile):
    def __init__(self, name, version, url, directory, server=True, client=True,
                 optional=False, pack_format=None, md5sum=None, filename=None):
        super().__init__(url, directory, pack_format=pack_format,
                         md5sum=md5sum, filename=filename)
        self.name = name
        self.version = version
        self._server = server
        self._client = client
        self.optional = optional
        self.download = not optional

    def ensure(self, server=True):
        if not self.download:
            return
        download = False
        if server:
            download = self._server
        else:
            download = self._client
        if download:
            super().ensure()

class ModPack():
    BASE_URL = "http://download.nodecdn.net/containers/atl/"

    def __init__(self, name, version, directory):
        self._name = name
        self._safe_name = re.sub("[^A-Za-z0-9]", "", name)
        self._version = version
        self._base_directory = Path(directory)
        if not self._base_directory.exists():
            self._base_directory.mkdir(mode=0o755, parents=True)

        # Download the mod config xml
        config_url = self.BASE_URL + "packs/%s/versions/%s/Configs.xml" % \
                                     (self._safe_name, version)
        config_file = AutoUnpackableFile(config_url, self._base_directory,
                                         pack_format="none",
                                         filename=".Configs.xml")
        config_file.ensure()
        config_path = self._base_directory / ".Configs.xml"

        # Parse the XML and extract all elements
        tree = ElementTree.parse(str(config_path))
        root = tree.getroot()
        minecraft_version = root.find("./pack/minecraft").text

        # Generate all destination directories
        download_directories = {
            'forge':        self._base_directory,
            'resourcepack': self._base_directory,
            'mods':         self._base_directory / 'mods',
            'dependency':   self._base_directory / 'mods' / minecraft_version,
            'denlib':       self._base_directory / 'mods' / 'denlib/',
            'flan':         self._base_directory / 'mods' / 'Flan/',
            'ic2lib':       self._base_directory / 'mods' / 'ic2', 
            'bin':          self._base_directory / 'bin',
            'coremods':     self._base_directory / 'coremods',
            'disabled':     self._base_directory / 'disabledmods',
            'jarmod':       self._base_directory / 'jarmods',
            'natives':      self._base_directory / 'natives',
            'plugins':      self._base_directory / 'plugins',
        }

        # Zip all mods and libs together
        mods_and_lib_nodes = []
        for mod in root.findall("./mods/mod"):
            mods_and_lib_nodes.append((mod, 'mod'))
        for lib in root.findall("./libraries/library"):
            mods_and_lib_nodes.append((lib, 'lib'))

        # Parse all mod and lib nodes
        self._modfiles = []
        for node, type in mods_and_lib_nodes:
            # Get/generate common parameters
            url = self._expand_url(node.attrib['url'], node.attrib['download'])
            md5 = node.attrib.get('md5sum')
            filename = None
            directory = None
            pack_format = None #auto
            name = node.attrib.get("name")
            version = node.attrib.get("version")
            description = node.attrib.get("description")
            server = True
            client = True
            # Most mods and all libs are not optional
            optional = False

            if type == 'mod':
                filename = node.attrib.get('file')
                # Figure out pack_format and directory
                node_type = node.attrib['type']
                if node_type == "resourcepack":
                    pack_format = "none" # These should be kept as .zips
                if node_type in download_directories:
                    directory = download_directories[node_type]
                elif node_type == "extract":
                    # Special files of extract type should just be extracted
                    extractto = node.attrib['extractto']
                    # These are always zip files
                    pack_format = "zip"
                    if extractto == "root":
                        directory = self._base_directory
                    elif extractto == "mods":
                        directory = download_directories['mods']
                        k
                # Optional?
                if 'optional' in node.attrib and node.attrib['optional'] == "yes":
                    optional = True

                # Server/client?
                server = self._yesno_parse(node.attrib.get("server", "yes"))
                client = self._yesno_parse(node.attrib.get("client", "yes"))

            elif type == 'lib':
                filename = node.attrib.get('server')
                directory = self._base_directory / "libraries"

            modfile = ModFile(name, version, url, directory,
                              pack_format=pack_format, md5sum=md5,
                              filename=filename, server=server, client=client,
                              optional=optional)

            self._modfiles.append(modfile)

        # Add minecraft server jar
        url = "http://s3.amazonaws.com/Minecraft.Download/versions/%s/minecraft_server.%s.jar" \
            % (minecraft_version, minecraft_version)
        file = ModFile("minecraft_server", minecraft_version, url,
                       self._base_directory, pack_format="none", server=True,
                       client=False, optional=False)
        self._modfiles.append(file)

    def get_modfiles(self):
        return self._modfiles

    @staticmethod
    def _yesno_parse(yesno):
        if yesno == "yes":
            return True
        elif yesno == "no":
            return False
        else:
            raise Exception("String '%s' not yes or no" % yesno)

    def _expand_url(self, url, type):
        if type == 'direct':
            return url
        elif type == 'server':
            return self.BASE_URL + urllib.parse.quote(url)
        elif type == 'browser':
            # Probably adf.ly, Handled by downloading magic
            return url

    def ensure(self, server):
        # Configs zip
        configs_url = self.BASE_URL + "packs/%s/versions/%s/Configs.zip" % \
            (self._safe_name, self._version)
        configs = AutoUnpackableFile(configs_url, self._base_directory,
                                     pack_format="zip")

        # Download all files
        configs.ensure()

        for modfile in self._modfiles:
            modfile.ensure(server)

        # Create eula.txt
        eula = self._base_directory / "eula.txt"
        with eula.open("w") as f:
            f.write("eula=true")
