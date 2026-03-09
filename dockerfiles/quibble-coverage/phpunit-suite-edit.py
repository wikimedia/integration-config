#!/usr/bin/env python3
"""
Edit MediaWiki's PHPUnit configuration file
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
import os
from xml.dom import minidom


def add_php_directory(dom, include_element, path):
    directory = dom.createElement('directory')
    directory.setAttribute('suffix', '.php')
    directory.appendChild(dom.createTextNode(path))

    include_element.appendChild(dom.createTextNode('\n\t\t\t'))
    include_element.appendChild(directory)
    include_element.appendChild(dom.createTextNode('\n\t\t'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('suite', help='Path to the PHPUnit config')

    parser.add_argument('--cover-extension',
                        help='Extension path to set for coverage '
                             '(ex: extensions/Foo, skins/Beautiful)')

    args = parser.parse_args()
    assert args.cover_extension == "" or args.cover_extension.startswith((
        'extensions/',
        'skins/',
        'services/parsoid',
    ))

    dom = minidom.parse(args.suite)
    phpunit = dom.documentElement

    # The coverage filters used to be in a <filter> element, PHPUnit 9 switched
    # to <coverage>.
    coverage_element = (
        phpunit.getElementsByTagName('filter')
        or phpunit.getElementsByTagName('coverage')
    )[0]

    include = coverage_element.getElementsByTagName('include')
    if include:
        include = include[0]
        # Ensure that this property is true for CI.
        coverage_element.setAttribute("includeUncoveredFiles", "true")

    whitelist = coverage_element.getElementsByTagName('whitelist')
    if whitelist:
        # Pre-PHPUnit 9
        whitelist[0].setAttribute('addUncoveredFilesFromWhitelist', 'true')

    if args.cover_extension:
        # Remove the current directories that are inside <include>,
        # we don't want to include any of them
        while child := include.lastChild:
            include.removeChild(child)

        added_cover = False
        # Add the three directories we care about
        for folder in ['src', 'includes', 'maintenance']:
            path = os.path.join(args.cover_extension, folder)
            if os.path.exists(os.path.join(os.path.dirname(args.suite), path)):
                added_cover = True
                add_php_directory(dom, include, path)

        # If the none of the covers we added correspond to a folder,
        # no coverage report is generated. Add the extension base path
        # here instead. (T288396)
        if not added_cover:
            add_php_directory(dom, include, args.cover_extension)

    # This produces a dirty diff:
    # - self closing elements lack a final space,
    # - attributes are concatenated on a single line
    # - there is no final new line,
    # but no human should ever read it, hopefully.
    dom.writexml(open(args.suite, 'w'))


if __name__ == '__main__':
    main()
