import imp
import os
import unittest

from nose.plugins.attrib import attr

parameter_functions_py = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '../zuul/parameter_functions.py')
imp.load_source('zuul_config', parameter_functions_py)
import zuul_config


class GatedRepos(set):
    def __repr__(self):
        return "<gated repos>"

    def __str__(self):
        return "<gated repos>"


gatedrepos = GatedRepos(
    zuul_config.gatedextensions
    + ['skins/%s' % s for s in zuul_config.gatedskins])

test = unittest.TestCase('__init__')

# Retrieve dependencies of each projects and keep track of the gated project
# that depends on it.
gated_deps = {}
for gated_project in gatedrepos:
    deps = zuul_config.get_dependencies(
        gated_project,
        zuul_config.dependencies)
    for dep in deps:
        if dep not in gated_deps:
            gated_deps[dep] = [gated_project]
        else:
            gated_deps[dep].append(gated_project)


@attr('qa')
def test_deps_of_gated_are_in_gate():
    for (gated_dep, origin) in sorted(gated_deps.iteritems()):
        test.assertIn.__func__.description = (
            'Dependency of gated project is in gate: %s' % (gated_dep))
        yield (
            test.assertIn,
            gated_dep, gatedrepos,
            '%s must be in gate since it is a dependency of: %s' % (
                gated_dep, ', '.join(sorted(origin))))
    del(test.assertIn.__func__.description)
