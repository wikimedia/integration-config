#!/usr/bin/env python3
#
# Copyright (c) 2025 - Antoine "hashar" Musso
# Copyright (c) 2025 - Wikimedia Foundation Inc.
#
# Script to manually launch MediaWiki Jenkins jobs with dependencies injected.
#
# The script runs PHPUnit and Selenium jobs for any repository having a
# dependency set.  This is done by submitting requests to the Zuul Gearman
# server, it report back the repo/job/success.
#
# This was written to stop recursively processing extensions dependencies,
# see https://phabricator.wikimedia.org/T389998
#
# Setup the environment:
#
# virtualenv foo
# . ./foo/bin/activate
# pip install gear PyYAML
#
# Example usage:
#
# ./zuul-mw-jobs-runner.py  ../zuul/layout.yaml ../zuul/parameter_functions.py
#
# Pass `--start` to start submitting jobs against a Gearman server on localhost:
#
# ./utils/zuul-mw-jobs-runner.py zuul/layout.yaml \
#     zuul/parameter_functions.py \
#     --start --jobs 4 |& tee run.log

import argparse
import importlib.util
import importlib.machinery
import json
import logging
import os
from queue import Queue
import re
import sys
import threading
from time import sleep
from uuid import uuid4

import gear
import yaml

IGNORE_PROJECTS = {
    # Uses a custom job
    'mediawiki/extensions/DonationInterface',
    'mediawiki/extensions/FundraisingEmailUnsubscribe',
    'mediawiki/services/parsoid/testreduce',
}

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('zuul-mw-jobs-runner')
log.setLevel(logging.INFO)


class JobToRun():

    def getDeps(self):
        return sorted([
            dep.removeprefix('mediawiki/extensions/')
            for dep in self.params.get('EXT_DEPENDENCIES', '').split('\\n')
            ],
            key=str.casefold)

    def getProject(self):
        return self.params['ZUUL_PROJECT']

    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        branch = self.params['ZUUL_BRANCH']
        return '<%s %sjob=%s deps=%s>' % (
            self.params['ZUUL_PROJECT'],
            '' if branch == 'master' else ('branch=%s ' % branch),
            self.name,
            ','.join(self.getDeps()) or '[]'
        )


class ZuulMwJobsRunner():

    def __init__(self, args):
        self.client = None
        self.queue = Queue()
        self.jenkins_jobs_to_run = []

        self.zuul_layout = args.zuul_layout
        self.params_file = args.params_file
        self.num_jobs = args.jobs
        self.in_production = args.in_production
        self.requested_projects = args.projects
        self.projects_filter = args.projects_filter
        self.branch = args.branch
        self.phpunit = args.phpunit
        self.requires_only = args.requires_only
        self.disable_recurse = args.disable_recurse
        self.selenium = args.selenium

    def prepare(self):
        set_parameters = self._load_function(self.params_file)
        projects = self._read_projects(self.zuul_layout)

        for (project, jobs) in projects.items():
            for job_name in jobs:
                jenkins_job = JobToRun(
                    name=job_name,
                    params={
                        'ZUUL_PROJECT': project,
                        'ZUUL_BRANCH': self.branch,
                    },
                )
                if self.disable_recurse:
                    # Processed by set_mw_dependencies() in
                    # zuul/parameter_functions.py
                    jenkins_job.params['DISABLE_RECURSE'] = 1

                # quibble --resolve-requires does not need parameters
                if job_name in [
                    'quibble-requires-only-vendor-non-voting',
                    'quibble-requires-only-composer-non-voting',
                    'quibble-requires-only-composer-selenium',
                    'quibble-requires-only-vendor-selenium',
                ]:
                    # Added without EXT_DEPENDENCIES
                    self.jenkins_jobs_to_run.append(jenkins_job)
                    continue

                set_parameters(None, jenkins_job, jenkins_job.params)

                if not jenkins_job.params.get('EXT_DEPENDENCIES'):
                    del jenkins_job
                    break
                self.jenkins_jobs_to_run.append(jenkins_job)
        log.info('Found %s jobs to run' % len(self.jenkins_jobs_to_run))

    def print_queue(self):
        for j in self.jenkins_jobs_to_run:
            print(j)

    def _load_function(self, params_file):
        log.info('Loading Zuul function from %s', params_file)
        loader = importlib.machinery.SourceFileLoader('zuul_config', params_file)
        spec = importlib.util.spec_from_file_location('zuul_config', params_file, loader=loader)
        zuul_config = importlib.util.module_from_spec(spec)
        loader.exec_module(zuul_config)

        set_parameters = zuul_config.set_parameters
        log.info('Successfully loaded Zuul set_parameters()')
        return set_parameters

    def _templates_names(self, templates):
        return {t['name'] for t in templates}

    def _read_projects(self, zuul_layout):
        log.info('Reading projects from %s', zuul_layout)
        with open(zuul_layout) as f:
            layout = yaml.safe_load(f)

        projects = {}
        for p in layout['projects']:
            if (
                not p['name'].startswith((
                    'mediawiki/core', 'mediawiki/vendor',
                    'mediawiki/skins/', 'mediawiki/extensions',
                    'mediawiki/services/parsoid',
                ))
                or p['name'] in IGNORE_PROJECTS
            ):
                continue

            if (
                self.requested_projects is not None
                and p['name'] not in self.requested_projects
            ):
                continue

            # To only process extensions that are marked as being in Production
            #
            # --in-production default to None which prevents skipping in the
            # following XOR block.
            if (
                    self.in_production is True
                    and 'in-wikimedia-production' not in self._templates_names(p['template'])
                ) or (  # noqa
                    self.in_production is False
                    and 'in-wikimedia-production' in self._templates_names(p['template'])
            ):
                continue

            if self.projects_filter is not None:
                if not re.search(self.projects_filter, p['name']):
                    continue

            jobs = self._mapTemplatesToJobs(p['name'], p['template'])
            if not jobs:
                continue

            projects[p['name']] = jobs

        log.info('Found %s projects' % len(projects))
        return projects

    def _mapTemplatesToJobs(self, project_name, templates):
        templates = self._templates_names(templates)

        if templates.issubset({'archived', 'extension-broken'}):
            return []

        jobs = []
        # Gated extensions and vendor based extensions
        if (
            # mediawiki/core
            templates == {'extension-gate'}
            # mediawiki/vendor
            or templates == {'extension-gate', 'extension-apitests'}
            or 'extension-quibble' in templates
        ):
            if self.requires_only:
                if self.phpunit:
                    jobs += ['quibble-requires-only-vendor-non-voting']
                if self.selenium:
                    jobs += ['quibble-requires-only-vendor-selenium']
            else:
                if self.phpunit:
                    jobs += ['quibble-vendor-mysql-php83']
                if self.selenium:
                    jobs += ['quibble-composer-mysql-php83-selenium']
            return jobs

        # Extensions using composer
        if (
            'extension-quibble-composer' in templates
            or 'extension-quibble-php83-or-later' in templates
        ):
            if self.requires_only:
                if self.phpunit:
                    jobs += ['quibble-requires-only-composer-non-voting']
                if self.selenium:
                    jobs += ['quibble-requires-only-composer-selenium']
            else:
                if self.phpunit:
                    jobs += ['quibble-composer-mysql-php83']
                if self.selenium:
                    jobs += ['quibble-composer-mysql-php83-selenium']
            return jobs

        # The ones without Selenium
        if 'extension-quibble-noselenium' in templates:
            if self.requires_only:
                if self.phpunit:
                    jobs += ['quibble-requires-only-vendor-non-voting']
                if self.selenium:
                    jobs += ['quibble-requires-only-vendor-selenium']
            elif self.phpunit:
                jobs += ['quibble-vendor-mysql-php83']
            return jobs
        if 'extension-quibble-composer-noselenium' in templates:
            if self.requires_only:
                if self.phpunit:
                    jobs += ['quibble-requires-only-composer-non-voting']
                if self.selenium:
                    jobs += ['quibble-requires-only-composer-selenium']
            elif self.phpunit:
                jobs += ['quibble-composer-mysql-php83']
            return jobs
        # Bluespice
        if 'extension-quibble-bluespice' in templates:
            if self.requires_only:
                if self.phpunit:
                    jobs += ['quibble-requires-only-composer-non-voting']
                if self.selenium:
                    jobs += ['quibble-requires-only-composer-selenium']
            elif self.phpunit:
                jobs += ['quibble-composer-mysql-php83']
            return jobs

        raise Exception("Unhandled set of templates for %s: %s" % (
            project_name, templates))

    def dump(self):
        seen_projects = set()
        for j in self.jenkins_jobs_to_run:
            project = j.getProject()
            if project in seen_projects:
                continue
            seen_projects.add(project)

            print('%s: %s' % (
                project.removeprefix('mediawiki/extensions/'),
                ', '.join(j.getDeps())
            ))

    def start(self):
        def worker(num):
            worker_log = log.getChild('worker-%02d' % (num + 1))
            while True:
                item = self.queue.get()

                project = item.params['ZUUL_PROJECT']
                job_name = item.name

                worker_log.debug('%s starting %s', project, job_name)
                job = gear.Job(
                    name='build:%s' % item.name,
                    unique=str(uuid4().hex),
                    arguments=json.dumps(item.params).encode(),
                )
                self.client.submitJob(job=job, precedence=gear.PRECEDENCE_LOW)
                while job.complete is not True:
                    sleep(0.1)
                worker_log.debug('%s completed %s', project, job_name)

                if job.exception:
                    worker_log.error('Job %s for %s failed with an exception: %s',
                                     project, job_name, job.exception.decode())
                elif job.failure:
                    worker_log.error('Job %s for %s failed. Job data: %s',
                                     project, job_name, job.data)
                else:
                    isSuccess = json.loads(job.data[-1])['result'] == 'SUCCESS'
                    print('%s %s %s' % (
                        item.params['ZUUL_PROJECT'],
                        json.loads(job.data[0])['url'] + '/console',
                        "\033[32mSUCCESS\033[0m" if isSuccess else "\033[31mFAILURE\033[0m"
                    ))
                    sys.stdout.flush()

                self.queue.task_done()

        self._connect()

        # No point in starting more threads than total number of jobs
        threads_to_start = min(self.num_jobs, len(self.jenkins_jobs_to_run))

        log.info('Starting %s processing threads', threads_to_start)
        for x in range(0, threads_to_start):
            threading.Thread(target=worker, name='worker-%s' % x, args=[x], daemon=True).start()

        for job in self.jenkins_jobs_to_run:
            self.queue.put(job)

        log.info('Waiting for jobs to complete')
        self.queue.join()

    def _connect(self):
        log.info('Connecting to Gearman server')
        self.client = gear.Client(client_id='%s-%s' % (
            os.environ.get('USER', 'unknown user'),
            os.path.basename(__file__),
            )
        )
        self.client.addServer('127.0.0.1')
        self.client.waitForServer()
        log.info('Connected to Gearman server')


def parse_args(args):
    zuul_config_dir = os.path.realpath(os.path.join(
        os.path.dirname(__file__), '../zuul/'))

    parser = argparse.ArgumentParser()
    parser.add_argument('zuul_layout', nargs='?',
                        default=os.path.join(zuul_config_dir, 'layout.yaml'),
                        help='Path to zuul/layout.yaml')
    parser.add_argument('params_file', nargs='?',
                        default=os.path.join(zuul_config_dir, 'parameter_functions.py'),
                        help='Path to zuul/parameter_functions.py')

    actions = parser.add_argument_group('Actions')
    group = actions.add_mutually_exclusive_group()
    group.add_argument('--dump', action='store_true',
                       help='Show dependencies one per line')
    group.add_argument('--print', action='store_true', default=True,
                       help='Print representation of projects/jobs')
    group.add_argument('--start', action='store_true',
                       help='Start the jobs on the Gearman server')

    jenkins_jobs_num = 12
    parser.add_argument('--jobs', default=jenkins_jobs_num, type=int,
                        help='Number of Jenkins jobs to run in parallel '
                        ' (default: %s)' % jenkins_jobs_num)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--phpunit', action=argparse.BooleanOptionalAction,
                        default=True,
                        help='Run PHPUnit test suite (enabled by default')
    parser.add_argument('--selenium', action=argparse.BooleanOptionalAction,
                        default=True,
                        help='Run Selenium tests (enabled by default')

    requires = parser.add_mutually_exclusive_group()
    requires.add_argument('--requires-only', action='store_true',
                          help='Use requires field from extension.json '
                               'and do not use zuul/dependencies.yaml '
                               'to set dependencies)')
    requires.add_argument('--disable-recurse', action='store_true',
                          help='Disable recursion of extensions dependencies')

    projects = parser.add_mutually_exclusive_group()
    projects.add_argument(
        '--projects', nargs='*',
        help='Space separated list of projects to run. '
             'Example: Echo Flow')
    projects.add_argument(
        '--projects-filter', metavar='REGEX',
        help='Runs on project matching pattern. '
        'Example: ^mediawiki/extensions/Blue')
    parser.add_argument('--branch', default='master', metavar='ZUUL_BRANCH',
                        help='git branch to run jobs against (default: master)')

    parser.add_argument(
        '--in-production', action=argparse.BooleanOptionalAction, default=None,
        help='Only act/do not act on projects having "in-wikimedia-production template" '
             'in Zuul layout')

    return parser.parse_args(args)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    if args.debug:
        log.setLevel(logging.DEBUG)

    runner = ZuulMwJobsRunner(args)
    runner.prepare()
    if args.start:
        runner.start()
    elif args.dump:
        runner.dump()
    else:
        runner.print_queue()
        print('Use --start to run them')
