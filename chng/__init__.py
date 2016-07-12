# chng - Deploy ATLauncher mods
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

from .modpack import ModPack

import requests_cache
import logging
import re
import sys
import os
import argparse

logging.basicConfig(level=logging.INFO)

def run():
    requests_cache.install_cache('.requests_cache')

    # Parse arguments
    parser = argparse.ArgumentParser(description='Download modpacks from ATLauncher')
    parser.add_argument('-p', '--pack', dest="pack", metavar='NAME',
                        help='name of the pack')
    parser.add_argument('-v', '--version', dest="version", metavar='VERSION',
                        #TODO#help='version of the pack (use latest if not supplied)')
                        help='version of the pack')
    parser.add_argument('-d', '--dir', dest="dir", metavar='DIR',
                        default=(os.getcwd() + "/install"),
                        help='directory to install to')
    #TODO#parser.add_argument('-c', '--client', dest="client", action='store_const',
    #TODO#                    const=True, default=False,
    #TODO#                    help='install as client (default is server)')
    args = parser.parse_args()

    # Create modpack instance
    modpack = ModPack(args.pack, args.version, args.dir)

    # Figure out which mods are optional
    optional_modfiles = []
    for modfile in modpack.get_modfiles():
        if modfile.optional:
            optional_modfiles.append(modfile)

    # Let the user select which optional mods to install
    print()
    print("Please select which optional mods to install:")
    print()
    print("      %20s %10s" % ("Mod", "Version"))
    select_done = False
    while not select_done:
        i = 1
        print()
        for modfile in optional_modfiles:
            marker = "X" if modfile.download else " "
            print("%d [%s] %20s %10s" % (i, marker, modfile.name,
                                         modfile.version))
            i += 1
        print("d  - Done")
        print("a  - Abort")
        print()
        cmd = input("Select action: ").strip()
        for subcmd in re.split("[ ]+", cmd):
            if subcmd == "d":
                select_done = True
            elif subcmd == "a":
                return
            else:
                try:
                    num = int(subcmd)
                    if num < 1 or num > len(optional_modfiles):
                        print("Value out of bound")
                        continue

                    idx = num - 1
                    if optional_modfiles[idx].download:
                        optional_modfiles[idx].download = False
                    else:
                        optional_modfiles[idx].download = True
                except ValueError:
                    print("Not a valid command: '%s'" % subcmd)
                    break

    # Ensure that everything is available
    server = True
    #TODO#server = not args.client
    modpack.ensure(server)
