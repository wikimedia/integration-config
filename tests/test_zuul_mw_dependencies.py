import imp
import os
import unittest

from fakes import FakeJob

parameter_functions_py = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '../zuul/parameter_functions.py')
imp.load_source('zuul_config', parameter_functions_py)
import zuul_config


class TestMwDependencies(unittest.TestCase):

    def setUp(self):
        # Let test mangle the 'dependencies' global
        self._deps_copy = zuul_config.dependencies.copy()

    def tearDown(self):
        # Restore the 'dependencies' global from the shallow clone
        zuul_config.dependencies = self._deps_copy
        self.assertIn('AbuseFilter', zuul_config.dependencies)

    def assertHasDependencies(self, params):
        self.assertIn('EXT_DEPENDENCIES', params)

    def assertMissingDependencies(self, params):
        self.assertNotIn('EXT_DEPENDENCIES', params)
        self.assertNotIn('SKIN_DEPENDENCIES', params)

    def fetch_dependencies(self, job_name=None, project=None, branch='master'):
        if project:
            params = {'ZUUL_PROJECT': project}
        else:
            params = {'ZUUL_PROJECT': 'mediawiki/extensions/Example'}
        params['ZUUL_BRANCH'] = branch

        job = FakeJob(job_name if job_name
                      else 'mediawiki-quibble-composer-mysql-php74')
        zuul_config.set_parameters(None, job, params)
        return params

    def test_ext_name(self):
        params = self.fetch_dependencies(
            project='mediawiki/extensions/Example')

        self.assertIn('EXT_NAME', params)
        self.assertEqual(params['EXT_NAME'], 'Example')

    def test_skin_name(self):
        params = self.fetch_dependencies(
            project='mediawiki/skins/Vector')

        self.assertIn('SKIN_NAME', params)
        self.assertEqual(params['SKIN_NAME'], 'Vector')

    def test_inject_dependencies(self):
        # VisualEditor adds extra DiscussionTools
        params = self.fetch_dependencies(
            project='mediawiki/extensions/VisualEditor')
        self.assertIn('EXT_DEPENDENCIES', params)
        self.assertIn(
            'mediawiki/extensions/DiscussionTools',
            params.get('EXT_DEPENDENCIES').strip().split('\\n')
        )

        # Wikibase adds extra ArticlePlaceholder
        params = self.fetch_dependencies(
            project='mediawiki/extensions/Wikibase')
        self.assertIn('EXT_DEPENDENCIES', params)
        self.assertIn(
            'mediawiki/extensions/ArticlePlaceholder',
            params.get('EXT_DEPENDENCIES').strip().split('\\n')
        )

        # No recursion. Math adds VE/Wikibase without inheriting more (T389998)
        params = self.fetch_dependencies(
            project='mediawiki/extensions/Math')
        self.assertIn('EXT_DEPENDENCIES', params)
        self.assertEqual(
            ['mediawiki/extensions/VisualEditor', 'mediawiki/extensions/Wikibase'],
            params.get('EXT_DEPENDENCIES').strip().split('\\n')
        )

    def test_resolvable_dependencies(self):
        """verifies that we can resolve all of the dependencies"""
        for base_name in zuul_config.dependencies:
            if base_name.startswith('skins/'):
                project = 'mediawiki/' + base_name
            else:
                project = zuul_config.remap_parsoid(
                    'mediawiki/extensions/' + base_name)

            self.assertHasDependencies(self.fetch_dependencies(
                project=project))

    def test_job_name(self):
        self.assertHasDependencies(self.fetch_dependencies(
            job_name='mediawiki-quibble-composer-mysql-php74'))

        self.assertHasDependencies(self.fetch_dependencies(
            job_name='quibble-composer-mysql-php74'))

        self.assertMissingDependencies(self.fetch_dependencies(
            job_name='mediawiki-core-phplint'))

    def test_zuul_project_name(self):
        self.assertHasDependencies(self.fetch_dependencies(
            project='mediawiki/extensions/Example'))

        self.assertMissingDependencies(self.fetch_dependencies(
            project='mediawiki/extensions'))
        self.assertMissingDependencies(self.fetch_dependencies(
            project='mediawiki/skins'))
        self.assertMissingDependencies(self.fetch_dependencies(
            project='mediawiki/extensions/Example/vendor'))
        self.assertMissingDependencies(self.fetch_dependencies(
            project='foo/bar/baz'))

    def test_inject_skin_on_an_extension(self):
        deps = self.fetch_dependencies(
            job_name='mediawiki-quibble-composer-mysql-php74',
            project='mediawiki/extensions/MobileFrontend')
        self.assertDictContainsSubset(
            {
                'EXT_NAME': 'MobileFrontend',
                'SKIN_DEPENDENCIES': 'mediawiki/skins/MinervaNeue',
            },
            deps)

    def test_inject_dependencies_on_quibble_jobs(self):
        self.maxDiff = None
        deps = self.fetch_dependencies(
            job_name='quibble-composer-mysql-php74',
            project='mediawiki/extensions/PropertySuggester')
        self.assertIn('EXT_DEPENDENCIES', deps)
        self.assertEqual(
            ['mediawiki/extensions/EventLogging', 'mediawiki/extensions/Wikibase'],
            deps['EXT_DEPENDENCIES'].strip().split('\\n')
        )

    def test_bluespice_branch_exception(self):
        deps = self.fetch_dependencies(
            job_name='quibble-composer-mysql-php74',
            project='mediawiki/extensions/BlueSpiceFoundation')
        self.assertIn('EXT_DEPENDENCIES', deps)
        self.assertEqual(
            ['mediawiki/extensions/OOJSPlus'],
            deps['EXT_DEPENDENCIES'].strip().split('\\n')
        )
