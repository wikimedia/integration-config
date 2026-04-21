#!/usr/bin/env python3
"""Find images in dockerfiles/ that aren't referenced in jjb/."""

import os
import re
import subprocess
import sys
from glob import glob

BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
DOCKERFILES_DIR = os.path.join(BASE_DIR, 'dockerfiles')
JJB_DIR = os.path.join(BASE_DIR, 'jjb')

IMAGE_NAME_RE = re.compile(r'docker-registry\.wikimedia\.org/releng/([\w.-]+)')

# Matches the first line of a Debian changelog: "package (version) ..."
CHANGELOG_FIRST_LINE_RE = re.compile(r'^(\S+)\s+\(([^)]+)\)')


def get_dockerfile_images():
    """Return set of image names defined in dockerfiles/."""
    images = set()
    for changelog_file in glob(os.path.join(DOCKERFILES_DIR, '*', 'changelog')):
        with open(changelog_file) as f:
            first_line = f.readline()
        m = CHANGELOG_FIRST_LINE_RE.match(first_line)
        if m:
            images.add(m.group(1))
        else:
            print('Warning: could not parse %s' % changelog_file, file=sys.stderr)
    return images


def get_control_dep_images():
    """Return set of image names listed as Depends in other images' control files."""
    images = set()
    for control_file in glob(os.path.join(DOCKERFILES_DIR, '*', 'control')):
        with open(control_file) as f:
            for line in f:
                if not line.startswith('Depends:'):
                    continue
                deps = line[len('Depends:'):].strip()
                for dep in deps.split(','):
                    images.add(dep.strip())
    return images


def get_jjb_images():
    """Return set of image names referenced in jjb/."""
    try:
        output = subprocess.check_output(
            ['git', 'grep', '-h', '-o', '-P',
             r'docker-registry\.wikimedia\.org/releng/[\w.-]+',
             JJB_DIR],
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:  # grep found no matches
            return set()
        print('git grep failed: %s' % e, file=sys.stderr)
        sys.exit(1)

    images = set()
    for line in output.decode().splitlines():
        m = IMAGE_NAME_RE.search(line)
        if m:
            images.add(m.group(1))
    return images


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        print('usage: docker-unused')
        sys.exit(0)

    dockerfile_images = get_dockerfile_images()
    jjb_images = get_jjb_images()
    control_dep_images = get_control_dep_images()

    unused = sorted(dockerfile_images - jjb_images - control_dep_images)

    if not unused:
        print('All dockerfiles/ images are referenced in jjb/')
        sys.exit(0)

    for image in unused:
        print(image)


if __name__ == '__main__':
    main()
