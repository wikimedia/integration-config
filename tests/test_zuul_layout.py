# Parse Zuul layout.yaml file
#
# Copyright (c) 2016 - Antoine "hashar" Musso
# Copyright (c) 2016 - Wikimedia Foundation Inc.

from copy import deepcopy
import os
import unittest

import yaml

from test_zuul_scheduler import MEDIAWIKI_VERSIONS


class TestZuulLayout(unittest.TestCase):
    """
    Tests solely asserting on the Zuul YAML configuration.

    Notably expansion of templates are not available which is provied by the
    scheduler and tested via test_zuul_scheduler.py
    """

    layout = None

    @classmethod
    def setUpClass(cls):
        wmf_zuul_layout = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../zuul/layout.yaml')
        with open(wmf_zuul_layout, 'r') as f:
            cls.layout = yaml.safe_load(f)

    def getExtSkinRepos(self):
        projects = []
        for project in self.layout['projects']:
            if not project['name'].startswith((
                    'mediawiki/skins', 'mediawiki/extensions')):
                continue
            if len(project['name'].split('/')) != 3:
                # Skip sub repositories
                continue
            projects.append(project)

        return projects

    def getProjectTemplates(self):
        templates = {}
        for project_template in self.layout['project-templates']:
            name = project_template['name']

            # Delete the template name to only retain pipelines, it is done on
            # a copy to prevent alteration to the original self.layout
            pipes = deepcopy(project_template)
            del(pipes['name'])

            templates[name] = project_template
        return templates

    def test_mediawiki_ext_skins_have_test_templates(self):
        one_of_templates = (
            'archived',
            'extension-broken',
            'extension-unittests',
            'extension-quibble',
            'skin-tests',
            'skin-quibble',
            'extension-gate',
            'quibble-vendor',
            )
        # Special cases for Fundraising reasons
        special_cases = (
            'mediawiki/extensions/DonationInterface'
            )

        errors = []
        for project in self.getExtSkinRepos():

            if project['name'] in special_cases:
                continue

            try:
                has_extension_unittests = any([
                    template['name'].startswith(one_of_templates)
                    for template in project.get('template', {})
                    ])
                self.assertTrue(
                    has_extension_unittests,
                    'Project %s in Zuul lacks an extension-unittests* '
                    'template' % project['name'])
            except AssertionError, e:
                errors.append(str(e))

        self.maxDiff = None
        self.assertListEqual([], errors)

    def test_gated_extensions_have_quibble_regular_template(self):
        errors = []
        for project in self.getExtSkinRepos():
            try:
                if 'template' not in project:
                    continue

                templates = [template['name']
                             for template in project.get('template')]
                if 'extension-gate' not in templates:
                    continue

                # Extract singular 'extension' or 'skin'
                kind = project['name'].split('/')[1][:-1]

                if 'extension-quibble-only-selenium' in templates:
                    self.assertIn(
                        'extension-quibble-noselenium',
                        templates,
                        'Must have both noselenium and only-selenium'
                    )
                    self.assertNotIn('extension-quibble', templates)
                else:
                    self.assertIn(
                        '%s-quibble' % kind,
                        templates,
                        'Must have "%s-quibble": %s' % (kind, project['name'])
                    )

            except AssertionError, e:
                errors.append(str(e))

        self.maxDiff = None
        self.assertListEqual([], errors)

    def test_bluespice_repos_use_composer_template(self):
        errors = []
        bsrepos = [r for r in self.getExtSkinRepos()
                   if '/BlueSpice' in r['name']]
        archivedRepos = [
            'mediawiki/extensions/BlueSpiceBookshelfUI',
            'mediawiki/extensions/BlueSpiceEditNotifyConnector',
            'mediawiki/extensions/BlueSpiceExtensions',
            'mediawiki/extensions/BlueSpiceMenues',
            'mediawiki/skins/BlueSpiceSkin'
        ]
        for project in bsrepos:
            if project['name'] in archivedRepos:
                # Ignore archived projects
                continue
            try:
                if 'template' not in project:
                    continue
                templates = [template['name']
                             for template in project.get('template')]

                # Extract singular 'extension' or 'skin'
                kind = project['name'].split('/')[1][:-1]

                required = [
                    '%s-broken' % kind,
                    '%s-quibble-composer-noselenium' % kind,
                    '%s-quibble-composer' % kind,
                    ]
                self.assertTrue(
                    any([r in templates for r in required]),
                    '%s must have one of [%s]. Got: %s' % (
                        project['name'],
                        ', '.join(required),
                        ', '.join(templates),
                    )
                )
            except AssertionError, e:
                errors.append(str(e))

        self.maxDiff = None
        self.assertListEqual([], errors)

    def test_templates_test_jobs_are_all_in_gate(self):
        errors = []
        self.maxDiff = None

        templates = self.getProjectTemplates()
        for template_name in templates:
            # Some templates are non voting or have no point in adding a job to
            # the gate.
            if 'gate-and-submit' not in templates[template_name]:
                continue

            for pipeline in templates[template_name]:
                if not pipeline.startswith('test'):
                    continue

                # Find the matching gate-and-submit pipeline
                if pipeline == 'test':
                    gate_pipeline = 'gate-and-submit'
                else:
                    suffix = pipeline.rpartition('-')[2]
                    gate_pipeline = 'gate-and-submit' + '-' + suffix

                for test_job in templates[template_name][pipeline]:
                    try:
                        gate_jobs = templates[template_name][gate_pipeline]
                        self.assertIn(
                            test_job,
                            gate_jobs,
                            'Template %s job %s in %s must also be in %s' % (
                                template_name, test_job,
                                pipeline, gate_pipeline)
                        )
                    except AssertionError as e:
                        errors.append(str(e))

        self.assertEqual([], errors)

    def test_pipelines_names_do_not_have_dots(self):
        self.longMessage = True
        for p in self.layout['pipelines']:
            self.assertNotIn('.', p['name'])

    def test_wikimedia_production_repos_have_requirements(self):
        errors = []
        for project in self.getExtSkinRepos():
            try:
                if 'template' not in project:
                    continue

                templates = [template['name']
                             for template in project.get('template')]
                if 'in-wikimedia-production' not in templates:
                    continue

                name = project['name'].split('/')[2]
                # Extract singular 'extension' or 'skin'
                kind = project['name'].split('/')[1][:-1]

                if 'extension-quibble-only-selenium' in templates:
                    self.assertNotIn(
                        'extension-quibble',
                        templates,
                        'Production %s %s shouldn\'t also have "%s-quibble"'
                        % (kind, name, kind)
                    )
                    self.assertIn(
                        'extension-quibble-noselenium',
                        templates,
                        'Production %s %s must have "%s-quibble-noselenium"'
                        % (kind, name, kind)
                    )
                else:
                    noQuibble = [
                        # Fix tracked in T249576
                        'mediawiki/extensions/DonationInterface',
                        # Fix tracked in T250420
                        'mediawiki/extensions/OpenStackManager',
                        # Fix tracked in T250418
                        'mediawiki/extensions/WikimediaIncubator',
                        # Uses special composer libraries; being replaced
                        'mediawiki/extensions/FundraisingEmailUnsubscribe'
                        ]

                    if project['name'] not in noQuibble:
                        self.assertIn(
                            '%s-quibble' % kind,
                            templates,
                            'Production %s %s must have "%s-quibble"'
                            % (kind, name, kind)
                        )

                # (T287918) Coverage publish job
                noCoverage = [
                    'mediawiki/extensions/DonationInterface',
                    'mediawiki/extensions/OpenStackManager',
                    'mediawiki/extensions/SearchVue',  # JS only
                    'mediawiki/extensions/Wikibase',
                    'mediawiki/extensions/WikimediaMaintenance'
                ]

                if project['name'] not in noCoverage:
                    self.assertIn(
                        '%s-coverage' % kind,
                        templates,
                        'Production %s %s must have "%s-coverage"'
                        % (kind, name, kind)
                    )

            except AssertionError, e:
                errors.append(str(e))

        self.maxDiff = None
        self.assertListEqual([], errors)

    def test_wikimedia_fundraising_production_repos_have_requirements(self):
        errors = []
        for project in self.getExtSkinRepos():
            try:
                if 'template' not in project:
                    continue

                templates = [template['name']
                             for template in project.get('template')]
                if 'in-wikimedia-fundraising-production' not in templates:
                    continue

                name = project['name'].split('/')[2]
                # Extract singular 'extension' or 'skin'
                kind = project['name'].split('/')[1][:-1]

                # TODO: Rename to quibble-fundraising-donationinterface-REL...
                # for consistency with all the others. (Note that the DI job
                # runs all four extensions, whereas the others currently only
                # run themselves, so this is a non-trivial change.)
                if project['name'] == 'mediawiki/extensions/DonationInterface':
                    self.assertIn(
                        'quibble-donationinterface-REL1_35-php73-docker',
                        project['gate-and-submit'],
                        'Fundraising %s %s must have FR G&S job for REL1_35'
                        % (kind, name)
                    )
                else:
                    self.assertIn(
                        'quibble-fundraising-%s-REL1_35-php73-docker' % name,
                        project['gate-and-submit'],
                        'Fundraising %s %s must have FR job G&S for REL1_35'
                        % (kind, name)
                    )

            except AssertionError, e:
                errors.append(str(e))

        self.maxDiff = None
        self.assertListEqual([], errors)

    def test_mediawiki_templates_have_all_rel_pipelines(self):
        errors = []
        rel_suffixes = [
            version['pipeline-suffix']
            for version in MEDIAWIKI_VERSIONS.values()
            if version['branch'].startswith('REL')
        ]
        expected_pipelines = set()
        for rel_suffix in rel_suffixes:
            expected_pipelines.add('test-' + rel_suffix)
            expected_pipelines.add('gate-and-submit-' + rel_suffix)

        templates = self.getProjectTemplates()
        for template_name in templates:
            if not template_name.startswith(('extension-', 'skin-')):
                continue
            # Exclude some from REL branches
            if template_name.endswith((
                    '-apitests',
                    '-codehealth',
                    '-coverage',
                    '-gate',
                    '-javascript-documentation',
                    '-phpbench',
                    )):
                continue

            try:
                actual_pipelines = set(templates[template_name].keys())
                self.assertGreaterEqual(
                    actual_pipelines,
                    expected_pipelines,
                    '%s template misses release pipelines: %s' % (
                        template_name,
                        ', '.join(
                            sorted(expected_pipelines - actual_pipelines)
                        )
                    )
                )
            except AssertionError, e:
                errors.append(str(e))

        self.maxDiff = None
        self.assertListEqual([], sorted(errors))
