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
import imp
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
}

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('zuul-mw-jobs-runner')
log.setLevel(logging.INFO)


class JobToRun():

    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        return '<%s job=%s deps=%s>' % (
            self.params['ZUUL_PROJECT'],
            self.name,
            ','.join([
                dep.removeprefix('mediawiki/extensions/')
                for dep in self.params['EXT_DEPENDENCIES'].split('\\n')
            ])
        )


class ZuulMwJobsRunner():

    def __init__(self, args):
        self.client = None
        self.queue = Queue()
        self.jenkins_jobs_to_run = []

        self.zuul_layout = args.zuul_layout
        self.params_file = args.params_file
        self.num_jobs = args.jobs
        self.requested_projects = args.projects
        self.projects_filter = args.projects_filter
        self.phpunit = args.phpunit
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
                        'ZUUL_BRANCH': 'master',
                    },
                )
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
        imp.load_source('zuul_config', params_file)
        import zuul_config
        set_parameters = zuul_config.set_parameters
        log.info('Successfully loaded Zuul set_parameters()')
        return set_parameters

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
                ))
                or p['name'] in IGNORE_PROJECTS
            ):
                continue

            if (
                self.requested_projects is not None
                and p['name'] not in self.requested_projects
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
        templates = {t['name'] for t in templates}

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
            if self.phpunit:
                jobs += ['quibble-vendor-mysql-php81']
            if self.selenium:
                jobs += ['quibble-composer-mysql-php81-selenium']
            return jobs

        # Extensions using composer
        if (
            'extension-quibble-composer' in templates
            or 'extension-quibble-php81-or-later' in templates
        ):
            if self.phpunit:
                jobs += ['quibble-composer-mysql-php81']
            if self.selenium:
                jobs += ['quibble-composer-mysql-php81-selenium']
            return jobs

        # The ones without Selenium
        if 'extension-quibble-noselenium' in templates:
            if self.phpunit:
                jobs += ['quibble-vendor-mysql-php81']
            return jobs
        if 'extension-quibble-composer-noselenium' in templates:
            if self.phpunit:
                jobs += ['quibble-composer-mysql-php81']
            return jobs
        # Bluespice
        if 'extension-quibble-bluespice' in templates:
            if self.phpunit:
                jobs += ['quibble-composer-mysql-php81']
            return jobs

        if 'skin-quibble' in templates:
            if self.phpunit:
                jobs += ['quibble-vendor-mysql-php81']
            return jobs
        if 'skin-quibble-composer' in templates:
            if self.phpunit:
                jobs += ['quibble-composer-mysql-php81']
            return jobs

        raise Exception("Unhandled set of templates for %s: %s" % (
            project_name, templates))

    def dump(self):
        pass

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
        threads_to_start = min(self.num_jobs, self.jenkins_jobs_to_run)

        log.info('Starting %s processing threads', threads_to_start)
        for x in range(0, self.threads_to_start):
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
    parser = argparse.ArgumentParser()
    parser.add_argument('zuul_layout')
    parser.add_argument('params_file')
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--jobs', default=2, type=int)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--phpunit', action=argparse.BooleanOptionalAction,
                        default=True)
    parser.add_argument('--selenium', action=argparse.BooleanOptionalAction,
                        default=True)

    projects = parser.add_mutually_exclusive_group()
    projects.add_argument(
        '--projects', nargs='*',
        help='Space separated list of projects to run. '
             'Example: Echo Flow')
    projects.add_argument(
        '--projects-filter', metavar='REGEX',
        help='Runs on project matching pattern. '
        'Example: ^mediawiki/extensions/Blue')

    return parser.parse_args(args)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    if args.debug:
        log.setLevel(logging.DEBUG)

    runner = ZuulMwJobsRunner(args)
    runner.prepare()
    if args.start:
        runner.start()
    else:
        runner.print_queue()
        print('Use --start to run them')
