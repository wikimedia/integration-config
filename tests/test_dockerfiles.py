import os
import re

from debian.changelog import Changelog
from debian.deb822 import Deb822
from nose.tools import assert_equals

DOCKERFILES_DIR = os.path.relpath(os.path.join(
    os.path.dirname(__file__),
    '../dockerfiles/'))

IMAGES_DIR = sorted([
    os.path.join(DOCKERFILES_DIR, d)
    for d in os.listdir(DOCKERFILES_DIR)
    if d not in ['__pycache__', '.tox', 'tests']
    and os.path.isdir(os.path.join(DOCKERFILES_DIR, d))
])

IMAGES_NAME = set([os.path.basename(d) for d in IMAGES_DIR])


def assertImageHasFile(image_dir, filename):
    assert os.path.isfile(os.path.join(image_dir, filename)), \
        "Image directory %s must have a '%s' file" % (
            os.path.join(image_dir), filename)


def test_has_template():
    for image_dir in IMAGES_DIR:
        yield assertImageHasFile, image_dir, 'Dockerfile.template'


def test_has_changelog():
    for image_dir in IMAGES_DIR:
        yield assertImageHasFile, image_dir, 'changelog'


def test_has_control():
    for image_dir in IMAGES_DIR:
        yield assertImageHasFile, image_dir, 'control'


def assertChangelogPackage(changelog_filename):
    with open(changelog_filename) as f:
        package = Changelog(f).get_package()

    image_dir = os.path.basename(
        os.path.dirname(changelog_filename))

    assert package == image_dir, \
        'Changelog package name %s matches directory name %s' % (
            package, image_dir)


def test_changelog_has_proper_package():
    for image_dir in IMAGES_DIR:
        changelog_filename = os.path.join(image_dir, 'changelog')
        yield assertChangelogPackage, changelog_filename


def assertChangelogHasNoWarning(image_dir):
    with open(os.path.join(image_dir, 'changelog')) as f:
        # strict to raise an exception
        Changelog(f, strict=True)


def test_changelog_has_no_warning():
    for image_dir in IMAGES_DIR:
        yield assertChangelogHasNoWarning, image_dir


def getDepends(control_filename):
    with open(control_filename) as f:
        control = Deb822(f)

    defined_deps = str(
        control.get('Depends', '') + ',' + control.get('Build-Depends', '')
        )
    deps = set(d.strip() for d in defined_deps.split(','))
    deps.discard('')
    return deps


def assertControlFile(control_filename):
    deps = getDepends(control_filename)
    if not deps:
        return

    assert deps.issubset(IMAGES_NAME), 'control dependencies must exist'


def test_control_files():
    for image_dir in IMAGES_DIR:
        control_filename = os.path.join(image_dir, 'control')
        if os.path.isfile(control_filename):
            yield assertControlFile, control_filename


def assertDockerfileFromsMatchesControlDepends(image_dir):
    DOCKER_FROM_RE = re.compile('FROM (?:{{ "(.*?)" \\| image_tag }}|"(.*?"))')
    control_deps = getDepends(os.path.join(image_dir, 'control'))
    with open(os.path.join(image_dir, 'Dockerfile.template')) as f:
        froms = set()
        for matches in DOCKER_FROM_RE.findall(f.read()):
            for m in matches:
                if m != '':
                    froms.add(m)
        # unitestTestCase.longMessage defaults to false in python 2.7
        assert_equals.__self__.longMessage = True
        assert_equals(
            control_deps,
            froms,
            "\n%s: mismatch between control Depends/Build-Depends fields "
            "and FROM statements in Dockerfile.template\nControl: "
            "%s\nDockerfile.template: %s\n" % (
                image_dir,
                ", ".join(control_deps),
                ", ".join(froms)
            )
        )


def test_dockerfile_froms_and_control_depends_matches():
    for image_dir in IMAGES_DIR:
        yield assertDockerfileFromsMatchesControlDepends, image_dir


def test_quibble_images_version_is_in_sync():

    # Get Quibble version installed by pip
    base_dockerfile = os.path.join(
        DOCKERFILES_DIR, 'quibble-buster/Dockerfile.template')
    quibble_version_re = re.compile(
        r'^ARG QUIBBLE_VERSION=([\.\d]+)$')

    quibble_version = None
    with open(base_dockerfile) as f:
        for line in f.readlines():
            match = re.match(quibble_version_re, line)
            if match:
                quibble_version = match.group(1)
                break

    if not quibble_version:
        raise AssertionError(
            'Could not find Quibble version looking at pip install command '
            'line in the Quibble base image')

    changelog_files = [
        os.path.join(d, 'changelog')
        for d in IMAGES_DIR
        if 'quibble' in d]
    for chg_file in changelog_files:
        with open(chg_file) as f:
            image_main_version = Changelog(f).get_version().upstream_version
            assert quibble_version == image_main_version, \
                'Expect Quibble image version %s, got %s in %s' % (
                    quibble_version, image_main_version, chg_file)
