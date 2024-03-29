import imp
import os.path
import unittest

from fakes import FakeJob

parameter_functions_py = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '../zuul/parameter_functions.py')
imp.load_source('zuul_config', parameter_functions_py)
import zuul_config


class TestSetGatedExtensions(unittest.TestCase):

    def test_deps_applied_on_gate_jobs(self):
        params = {
            'ZUUL_PIPELINE': 'test',
            'ZUUL_PROJECT': 'mediawiki/core',
            'ZUUL_BRANCH': 'master',
        }
        gate_job = FakeJob('wmf-quibble-foo')
        zuul_config.set_gated_extensions(None, gate_job, params)
        self.assertIn('EXT_DEPENDENCIES', params)

    def test_experimental_injects_project(self):
        params = {
            'ZUUL_PIPELINE': 'experimental',
            'ZUUL_PROJECT': 'mediawiki/extensions/SomeExt',
            'ZUUL_BRANCH': 'master',
        }
        gate_job = FakeJob('wmf-quibble-foo')
        zuul_config.set_gated_extensions(None, gate_job, params)
        self.assertIn('\\nmediawiki/extensions/SomeExt',
                      params['EXT_DEPENDENCIES'])

    def test_wikibase_master(self):
        params = {
            'ZUUL_PIPELINE': 'test',
            'ZUUL_PROJECT': 'mediawiki/core',
            'ZUUL_BRANCH': 'master',
        }
        gate_job = FakeJob('wmf-quibble-foo')
        zuul_config.set_gated_extensions(None, gate_job, params)
        self.assertIn('\\nmediawiki/extensions/Wikibase',
                      params['EXT_DEPENDENCIES'])
        self.assertNotIn('\\nmediawiki/extensions/Wikidata',
                         params['EXT_DEPENDENCIES'])

    def test_wikibase_notonethirty(self):
        params = {
            'ZUUL_PIPELINE': 'test',
            'ZUUL_PROJECT': 'mediawiki/core',
            'ZUUL_BRANCH': 'REL1_30',
        }
        gate_job = FakeJob('wmf-quibble-foo')
        zuul_config.set_gated_extensions(None, gate_job, params)
        self.assertNotIn('\\nmediawiki/extensions/Wikibase',
                         params['EXT_DEPENDENCIES'])
