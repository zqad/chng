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

from .modpack import ModPack
from .modpacklist import ModPackList

import requests_cache
import logging
import re
import sys
import os
import shutil
import argparse

logging.basicConfig(level=logging.INFO)

def run():
    # Initialize requests cache
    home = os.path.expanduser("~")
    requests_cache.install_cache(home + '/.chng_requests_cache')

    # Parse arguments
    parser = argparse.ArgumentParser(description='Download modpacks from ATLauncher')
    parser.add_argument('-p', '--pack', dest="pack", metavar='NAME',
                        help='name of the pack')
    parser.add_argument('-v', '--version', dest="version", metavar='VERSION',
                        help='version of the pack (use latest if not supplied)')
    parser.add_argument('-d', '--dir', dest="dir", metavar='DIR',
                        default=(os.getcwd() + "/install"),
                        help='directory to install to')
    parser.add_argument('-l', '--list', dest="list", action='store_const',
                        const=True, default=False,
                        help='list all modpacks with installable versions')
    parser.add_argument('-L', '--list-all', dest="list_all", action='store_const',
                        const=True, default=False,
                        help='list all modpacks')
    parser.add_argument('--full', dest="full", action='store_const',
                        const=True, default=False,
                        help='do not cut version text')
    parser.add_argument('-i', '--install', dest="install", action='store_const',
                        const=True, default=False,
                        help='install the selected pack')
    parser.add_argument('-s', '--show', dest="show", action='store_const',
                        const=True, default=False,
                        help='show more information about a pack')
    #TODO#parser.add_argument('-c', '--client', dest="client", action='store_const',
    #TODO#                    const=True, default=False,
    #TODO#                    help='install as client (default is server)')
    args = parser.parse_args()

    # Create modlist instance
    modpacklist = ModPackList()

    if (args.list or args.list_all) and args.show:
        print("Error: only one of list and show allowed")
        parser.print_help()
        return 1
    elif args.list or args.list_all:
        # Get terminal size to be able to cut output
        term_size = shutil.get_terminal_size((80, 20))
        for modpackinfo in modpacklist.modpackinfos():
            # Generate a version string of all installable versions
            versions = ""
            if len(modpackinfo.versions) > 0:
                versions = ", ".join([v.version for v in modpackinfo.versions])
            elif len(modpackinfo.versions) > 0:
                versions = ", ".join([v.version + "[dev]"
                                      for v in modpackinfo.versions])
            elif not args.list_all:
                # Only display modpacks with no installable versions if we have
                # been instructed to list *all* modpacks
                continue
            if (not args.full) and len(versions) > (term_size.columns - 31):
                versions = versions[:(term_size.columns - 35)] + " ..."
            print("%-30s %s" % (modpackinfo.name, versions))
    elif args.show:
        modpackinfo = modpacklist.get_modpackinfo(args.pack)
        if modpackinfo is None:
            #XXX error
            pass

        print("Name: %s" % modpackinfo.name)
        if modpackinfo.website:
            print("Website: %s" % modpackinfo.website)
        if modpackinfo.support:
            print("Support: %s" % modpackinfo.support)
        if modpackinfo.description:
            print("Description:\n%s" % modpackinfo.description)
            print()
        if len(modpackinfo.versions) > 0:
            print("Stable versions:")
            for v in modpackinfo.versions:
                print("    %s" % v.version)
            print()
        if len(modpackinfo.dev_versions) > 0:
            print("Development versions:")
            for v in modpackinfo.dev_versions:
                print("    %s" % v.version)
            print()

    elif args.install:
        # Install mod
        if args.pack is None:
            print("No modpack specified")
            parser.print_help()
            return 1

        # Create modpack instance
        modpackinfo = modpacklist.get_modpackinfo(args.pack)
        if modpackinfo is None:
            print("No such modpack: %s" % args.pack)
            return 1
        modpack = modpackinfo.to_modpack(args.dir, version=args.version)

        # Figure out which mods are optional
        optional_modfiles = []
        for modfile in modpack.get_modfiles():
            if modfile.optional:
                optional_modfiles.append(modfile)

        # Let the user select which optional mods to install
        if not select_optional(optional_modfiles):
            return 1

        # Ensure that everything is available on disk
        server = True
        #TODO#server = not args.client
        modpack.ensure(server)
    else:
        print("No action requested")
        parser.print_help()
        return 1

    return 0

def select_optional(optional_modfiles):
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
                return False
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
    return True
