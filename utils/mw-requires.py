#!/usr/bin/env python3

import argparse
import json
import logging
import os.path
import sys

import yaml

# Extensions that have not been convered to extension registry (they lack an
# extension.json). Their CI dependencies will be copied as-is
NO_EXTENSION_REGISTRY = [
    'RegexFun',
    'SemanticMediaWiki',
    'SocialProfile',
    'Wikibase',
    'parsoid',
]

# Requirements that are not in extension.json yet
MISSING_REQUIREMENTS = {
    'Flow': ['Echo'],  # https://gerrit.wikimedia.org/r/c/mediawiki/extensions/Flow/+/1194629
}

logging.basicConfig(
    level=logging.INFO,
    # Format without the logger name (default is 'root')
    format='%(levelname)s:%(message)s',
)
log = logging.getLogger('mw-requires')


class MwRequires():

    def __init__(self, args):
        self.extensions_dir = args.extensions_dir.rstrip('/')
        self.dependencies_file = args.dependencies_file
        self.comments = args.comments
        self.merge = args.merge
        self.project = args.project
        self.requirements_cache = {}

    def comment(self, msg):
        if not self.comments:
            return
        print(msg)

    def check(self):
        errored = False
        log.info('Reading %s', self.dependencies_file)
        with open(self.dependencies_file) as f:
            zuul_deps = yaml.safe_load(f)
        log.info('Found %s extensions with dependencies', len(zuul_deps))

        if not self.comments and self.merge:
            log.info("Will merge requirements and extras")
        else:
            log.info("Will sort requirements and extras independently"
                     + " with comments" if self.comments else "")

        for (ext, ci_deps) in zuul_deps.items():

            if self.project and ext != self.project:
                continue

            requirements = self.get_requirements(ext, recursive=False)
            if requirements is None:
                errored = True
                continue

            transitives = self.get_requirements(ext, recursive=True) - requirements

            print('%s:' % ext)

            # Any extension defined in CI which is NOT already in extension registry
            extras = {ci_dep for ci_dep in ci_deps
                      if ci_dep not in requirements
                      and ci_dep not in transitives}

            extras_transitives = {
                extra_dep
                for extra in extras
                for extra_dep in self.get_requirements(extra, recursive=True)
            } - requirements - extras

            # When using no comments, the dependencies from extension.json and
            # zuul/dependencies.yaml are printed sorted as a unique list. This
            # makes it easier to compare with zuul/dependencies.yaml
            if not self.comments:
                if self.merge:
                    deps = sorted(requirements + transitives + extras, key=str.casefold)
                else:
                    # Sort them independently
                    deps = sorted(requirements, key=str.casefold) \
                        + sorted(transitives, key=str.casefold) \
                        + sorted(extras, key=str.casefold)

                for dep in deps:
                    print(' - %s' % dep)

                print()
                continue  # proceed with next extension

            # Else when we get comments, each list is printed by itself

            if requirements:
                self.comment('# From extension.json:')
                for requirement in sorted(requirements, key=str.casefold):
                    print(' - %s' % requirement)
            else:
                self.comment('# no requirements in extension.json')

            if transitives:
                self.comment('# Transitive requirements:')
                for requirement in sorted(transitives, key=str.casefold):
                    print(' - %s' % requirement)

            if extras:
                self.comment('# extras')
                for extra in sorted(extras, key=str.casefold):
                    print(' - %s' % extra)

            if extras_transitives:
                self.comment('# extras transitive requirements:')
                for requirement in sorted(extras_transitives, key=str.casefold):
                    print(' - %s' % requirement)

            print()

        if errored:
            return 1

    def get_requirements(self, ext, recursive=False):
        # Static cache to return early

        if not recursive:
            if ext in self.requirements_cache:
                return self.requirements_cache[ext]

        ext_file = os.path.join(self.extensions_dir, ext, 'extension.json')

        if ext.startswith('skins/'):
            ext_file = os.path.join(
                os.path.dirname(self.extensions_dir),
                ext, 'skin.json')

        ext_file = os.path.realpath(ext_file)

        try:
            if ext in NO_EXTENSION_REGISTRY:
                registry = {}
            else:
                with open(ext_file) as f:
                    registry = json.loads(f.read())
        except FileNotFoundError:  # noqa lint is done with Python 2.7
            log.error('File missing: %s', ext_file)
            self.requirements_cache[ext] = None
            return None

        requirements = {
            str(key)
            for key in registry
                .get('requires', {})  # noqa
                .get('extensions', {})
                .keys()
        }
        if ext in MISSING_REQUIREMENTS:
            for missing_req in MISSING_REQUIREMENTS[ext]:
                if missing_req not in requirements:
                    log.info("%s: added missing requirement: %s", ext, missing_req)
                    requirements.add(missing_req)
        self.requirements_cache[ext] = requirements

        if recursive:
            transitives_requirements = set()
            for req in requirements:
                if req not in self.requirements_cache:
                    self.requirements_cache[req] = self.get_requirements(req, recursive=False)
                transitives = self.get_requirements(req, recursive=True)
                if transitives:
                    transitives_requirements.update(transitives)
            requirements.update(transitives_requirements)

        return requirements


def parse_args(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

    # Arguments ####

    parser.add_argument(
        'extensions_dir',
        help='Path to a checkout of mediawiki/extensions.git',
    )
    parser.add_argument(
        'dependencies_file',
        nargs='?',
        default='zuul/dependencies.yaml',
        help='Path to Zuul file defining dependencies',
        )

    # Options ####

    parser.add_argument(
        '-p', '--project',
        nargs='?',
        help='Act solely on the given project',
    )

    parser.add_argument(
        '--comments',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Do not add comments to the output. Helpful to compare '
             'the output with zuul/dependencies.yaml.',
        )

    parser.add_argument(
        '--merge',
        action='store_true',
        help='With --no-comments, sort requires and extras as a single list',
        )

    return parser.parse_args(args)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    requires = MwRequires(args)

    if requires.check() is not None:
        log.critical("Script has completed with errors (see stderr)")
        sys.exit(1)
