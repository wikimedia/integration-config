import imp
import os
import unittest

from fakes import FakeJob

parameter_functions_py = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '../zuul/parameter_functions.py')
imp.load_source('zuul_config', parameter_functions_py)
import zuul_config


class TestZuulSetParameters(unittest.TestCase):

    def test_debian_glue_default_to_no_network(self):
        job = FakeJob('debian-glue')
        params = {'ZUUL_PROJECT': 'some/project'}
        zuul_config.set_parameters(None, job, params)
        self.assertNotIn('PBUILDER_USENETWORK', params)

    def test_zuul_debian_glue_with_network(self):
        job = FakeJob('debian-glue')
        params = {'ZUUL_PROJECT': 'integration/zuul'}
        zuul_config.set_parameters(None, job, params)
        self.assertIn('PBUILDER_USENETWORK', params)

    def test_debian_glue_backports(self):
        # Zuul injects BACKPORTS=yes - T173999
        for job_name in (
                'debian-glue-backports',
                'debian-glue-backports-non-voting',
                ):
            job = FakeJob(job_name)
            params = {'ZUUL_PROJECT': 'fake_project'}
            zuul_config.set_parameters(None, job, params)
            self.assertIn('BACKPORTS', params)
            self.assertEquals('yes', params['BACKPORTS'])

    def test_wmf_quibble_jobs_are_gates(self):
        job = FakeJob('wmf-quibble-anything')
        params = {
            'ZUUL_PROJECT': 'mediawiki/core',
            'ZUUL_PIPELINE': 'test',
            'ZUUL_BRANCH': 'master',
            }
        zuul_config.set_parameters(None, job, params)

        self.assertIn('EXT_DEPENDENCIES', params)
        self.assertIn('mediawiki/extensions/AbuseFilter\\n',
                      params['EXT_DEPENDENCIES'])

    def test_quibble_jobs_are_parallel_and_results_cache_server_set(self):
        job = FakeJob('quibble-anything')
        params = {
            'ZUUL_PROJECT': 'mediawiki/core',
            'ZUUL_PIPELINE': 'test',
            'ZUUL_BRANCH': 'master',
            }
        zuul_config.set_parameters(None, job, params)

        self.assertIn('QUIBBLE_PHPUNIT_PARALLEL', params)
        self.assertIn('MW_RESULTS_CACHE_SERVER_BASE_URL', params)
