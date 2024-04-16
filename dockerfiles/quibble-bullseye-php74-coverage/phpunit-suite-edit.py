#!/usr/bin/env python3
"""
Edit MediaWiki's PHPUnit suite.xml file
Copyright (C) 2018, 2022 Kunal Mehta <legoktm@debian.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import argparse
import xml.etree.cElementTree as etree


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('suite', help='Path to suite.xml')
    parser.add_argument('--cover-extension',
                        help='Extension path to set for coverage')
    parser.add_argument('--cover-service',
                        help='Service path to set for coverage')
    parser.add_argument('--cover-skin',
                        help='Skin path to set for coverage')

    args = parser.parse_args()
    tree = etree.parse(args.suite)
    root = tree.getroot()
    for child in list(root):
        # Switched to <coverage> in PHPUnit 9
        if child.tag in ['filter', 'coverage']:
            include = list(child)[0]
            if include.tag == "include":
                # Ensure that this property is true for CI.
                child.set("includeUncoveredFiles", "true")
            elif include.tag == "whitelist":
                # Pre-PHPUnit 9
                include.set('addUncoveredFilesFromWhitelist', 'true')
            else:
                raise ValueError(
                    "Unexpected tag, looking for include, found {}".format(
                        include.tag
                    )
                )

            if args.cover_extension:
                # Remove the current directories that are there,
                # we don't want to include any of them
                for ichild in list(include):
                    include.remove(ichild)
                # Add the three directories we care about
                for folder in ['src', 'includes', 'maintenance']:
                    sub = etree.SubElement(include, 'directory')
                    sub.text = '../../extensions/%s/%s' \
                        % (args.cover_extension, folder)
                    sub.set('suffix', '.php')

            if args.cover_service:
                # Remove the current directories that are there,
                # we don't want to include any of them
                for ichild in list(include):
                    include.remove(ichild)
                # Add the three directories we care about
                for folder in ['src', 'includes', 'maintenance']:
                    sub = etree.SubElement(include, 'directory')
                    sub.text = '../../services/%s/%s' \
                        % (args.cover_service, folder)
                    sub.set('suffix', '.php')

            if args.cover_skin:
                # Remove the current directories that are there,
                # we don't want to include any of them
                for ichild in list(include):
                    include.remove(ichild)
                # Add the three directories we care about
                for folder in ['src', 'includes', 'maintenance']:
                    sub = etree.SubElement(include, 'directory')
                    sub.text = '../../skins/%s/%s' \
                        % (args.cover_skin, folder)
                    sub.set('suffix', '.php')

    # This produces a dirty diff, strips comments, ignores newlines,
    # and so on, but no human should ever read it, hopefully.
    tree.write(args.suite)


if __name__ == '__main__':
    main()
