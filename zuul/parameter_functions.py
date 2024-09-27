"""
Parameter functions for zuul jobs

Combined into one Python function due to T125498
"""

import re
import os
import yaml


# For historical reasons, Parsoid is a 'service' not an 'extension'.
# But practically speaking, Parsoid is (for the moment) an extension.
def remap_parsoid(list_or_string):
    if isinstance(list_or_string, str):
        return 'mediawiki/services/parsoid' \
            if list_or_string == 'mediawiki/extensions/parsoid' \
            else list_or_string
    return [remap_parsoid(item) for item in list_or_string]


def set_parameters(item, job, params):
    """
    :type item: zuul.model.QueueItem
    :type job: zuul.model.Job
    :type params: dict
    """

    mw_deps_jobs_starting_with = (
        'mwext-',
        'mwskin-',
        'mediawiki-quibble',
        'quibble',
        )
    if job.name.startswith(mw_deps_jobs_starting_with):
        set_mw_dependencies(item, job, params)

    # Special jobs for Wikibase - T188717
    if job.name.startswith('wikibase-client'):
        params['EXT_DEPENDENCIES'] = '\\n'.join([
            'mediawiki/extensions/Scribunto',
            'mediawiki/extensions/Capiunto',
            'mediawiki/extensions/cldr',
            'mediawiki/extensions/Echo',
            'mediawiki/extensions/EntitySchema',
            'mediawiki/extensions/Wikibase',
        ])

    if job.name.startswith('wikibase-repo'):
        params['EXT_DEPENDENCIES'] = '\\n'.join([
            'mediawiki/extensions/CirrusSearch',
            'mediawiki/extensions/Elastica',
            'mediawiki/extensions/GeoData',
            'mediawiki/extensions/cldr',
        ])

    # Enable parallel PHPUnit runs for MW ecosystem, except:
    if (
        # ... temporarily exclude MediaWiki core and extensions
        # that have issues with parallel tests
        params["ZUUL_PROJECT"] not in [
            "mediawiki/core",
            "mediawiki/extensions/WikiLambda"
        ]
        # ... exclude on REL_ branches (not yet tested/patched),
        and "ZUUL_BRANCH" in params
        and not params["ZUUL_BRANCH"].startswith("REL1")
        # Exclude fundraising branches
        and not params["ZUUL_BRANCH"].startswith("fundraising")
    ):
        params['QUIBBLE_PHPUNIT_PARALLEL'] = '1'

    # parallel-lint can be slow, so raise the limit for vendor.git
    if params['ZUUL_PROJECT'].startswith('mediawiki/vendor'):
        params['COMPOSER_PROCESS_TIMEOUT'] = 600

    if job.name.startswith('wmf-quibble-'):
        set_gated_extensions(item, job, params)

    if job.name.endswith('-publish') or 'codehealth' in job.name:
        set_doc_variables(item, job, params)

    # Prevent puppeteer from downloading Chromium, we use the Debian package
    # instead.  T179552 T186748
    if params['ZUUL_PROJECT'].startswith('mediawiki/services/chromium-render'):
        params['PUPPETEER_SKIP_CHROMIUM_DOWNLOAD'] = 'true'

    if 'debian-glue' in job.name:

        # XXX
        # When adding new paramters, make sure the env variable is added as an
        # env_keep in the sudo policy:
        # https://horizon.wikimedia.org/project/sudo/
        #

        if 'nocheck' in job.name:
            params['DEB_BUILD_OPTIONS'] = 'nocheck'
        if 'backports' in job.name:  # T173999
            params['BACKPORTS'] = 'yes'
        # Always set the value to be safe (T144094)
        params['BUILD_TIMEOUT'] = 30  # minutes
        # Finely tweak jenkins-debian-glue parameters
        if params['ZUUL_PROJECT'] == 'integration/zuul':
            # Uses dh_virtualenv which needs access to pypy.python.org
            params['PBUILDER_USENETWORK'] = 'yes'
        elif (params['ZUUL_PROJECT'] == 'operations/debs/doxygen'):
            params['DEB_BUILD_OPTIONS'] = 'parallel=2'
        elif (params['ZUUL_PROJECT'] == 'operations/debs/varnish4'):
            # VTC tests take forever
            params['BUILD_TIMEOUT'] = 60  # minutes
            params['DEB_BUILD_OPTIONS'] = 'parallel=12'
        elif (params['ZUUL_PROJECT'] == 'operations/software/atskafka'):
            # needed by go build to access gopkg.in
            params['PBUILDER_USENETWORK'] = 'yes'
        elif (params['ZUUL_PROJECT'] == 'operations/debs/hue'):
            # fetches from pypi/npm
            params['PBUILDER_USENETWORK'] = 'yes'
        elif (params['ZUUL_PROJECT'] == 'operations/debs/trafficserver'):
            # Building ATS takes a while
            params['BUILD_TIMEOUT'] = 60  # minutes
            # Backports needed on stretch for libbrotli-dev and a recent
            # debhelper version (>= 11)
            params['BACKPORTS'] = 'yes'
        elif (params['ZUUL_PROJECT']
              == 'operations/debs/contenttranslation/giella-sme'):
            # Heavy build T143546
            params['BUILD_TIMEOUT'] = 180  # minutes


# This hash is used to inject dependencies for MediaWiki jobs.
#
# Note! This list is not used by Phan. Edit the other file for that list.
# ZUUL_DIR = os.path.dirname(os.path.abspath(__file__))
# HACK: This is horrible, but __file__ isn't defined.
if os.path.exists("/etc/zuul/wikimedia/zuul"):
    # For actual running of CI
    ZUUL_DIR = "/etc/zuul/wikimedia/zuul"
elif os.path.exists("/src/zuul"):
    # For most of the test cases for testing CI
    ZUUL_DIR = "/src/zuul"
elif os.path.exists("/src/integration/config/zuul"):
    # For the rest of the test cases for testing CI
    ZUUL_DIR = "/src/integration/config/zuul"
else:
    raise Exception(
        "ZUUL_DIR could not be set, environment not recognised; I'm in: '"
        + os.getcwd() + "'"
    )


with open(os.path.join(ZUUL_DIR, "dependencies.yaml")) as stream:
    try:
        dependencies = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        print(error)

# This hash is used to inject dependencies for MediaWiki phan jobs.
#
# This list is *not* recursively processed.
#
# Note! This list is only used by Phan. Edit the other file for PHPUnit etc.
with open(os.path.join(ZUUL_DIR, "phan_dependencies.yaml")) as stream:
    try:
        phan_dependencies = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        print(error)


# Export with a literal \n character and have bash expand it later via
# 'echo -e $XXX_DEPENDENCIES'.
def glue_deps(prefix, deps):
    return '\\n'.join(remap_parsoid(
        prefix + d for d in sorted(list(set(deps)))
    ))


def set_mw_dependencies(item, job, params):
    """
    Inject MediaWiki dependencies based on a built-in hash.

    Reads MediaWiki dependencies for a repository and inject them as
    parameters EXT_DEPENDENCIES or SKIN_DEPENDENCIES. The map is configured via
    the 'dependencies' dictionary above.

    Extensions and skins will be cloned by Zuul-cloner.

    :type item: zuul.model.QueueItem
    :type job: zuul.model.Job
    :type params: dict
    """
    if not params['ZUUL_PROJECT'].startswith((
        'mediawiki/extensions/',
        'mediawiki/skins/',
        'mediawiki/services/parsoid',
    )):
        return

    split = params['ZUUL_PROJECT'].split('/')

    if len(split) != 3:
        return

    # extensions/Foo, skins/Bar
    params['THING_SUBNAME'] = '/'.join(split[1:3])

    if split[1] == 'skins':
        # Lookup key in 'dependencies'. Example: 'skins/Vector'
        dep_key = 'skins' + '/' + split[-1]
        # 'Vector'
        params['SKIN_NAME'] = split[-1]
    elif split[1] == 'services':
        # Lookup key in 'dependencies'. Example: 'parsoid'
        dep_key = split[-1]
        params['SERVICE_NAME'] = split[-1]
    else:
        # Lookup key in 'dependencies. Example: 'Foobar'
        dep_key = split[-1]
        params['EXT_NAME'] = split[-1]

    if '-phan' in job.name:
        mapping = phan_dependencies
        recurse = False
    else:
        mapping = dependencies
        recurse = True

    deps = get_dependencies(dep_key, mapping, recurse)

    # Split extensions and skins
    skin_deps = {d for d in deps if d.startswith('skins/')}
    ext_deps = deps - skin_deps

    params['SKIN_DEPENDENCIES'] = glue_deps('mediawiki/', skin_deps)
    params['EXT_DEPENDENCIES'] = glue_deps('mediawiki/extensions/', ext_deps)


def get_dependencies(key, mapping, recurse=True):
    """
    Get the full set of dependencies required by an extension

    :param key: extension base name or skin as 'skin/BASENAME'
    :param mapping: mapping of repositories to their dependencies
    :param recurse: Whether to recursively process dependencies
    :return: set of dependencies
    """
    resolved = set()

    def resolve_deps(ext):
        resolved.add(ext)
        deps = set()

        if ext in mapping:
            for dep in mapping[ext]:
                deps.add(dep)

                if recurse and dep not in resolved:
                    deps = deps.union(resolve_deps(dep))

        return deps

    return resolve_deps(key)


tarballextensions = [
    'AbuseFilter',

    # Skipped, non-trivial (TODO)
    # 'CategoryTree',

    'Cite',
    'CiteThisPage',
    'CodeEditor',
    'ConfirmEdit',

    # Skipped, non-trivial (TODO)
    # 'DiscussionTools',

    'Echo',
    'Gadgets',
    'ImageMap',
    'InputBox',
    'Interwiki',

    # Skipped, non-trivial (TODO)
    # 'Linter',

    # Skipped, non-trivial (TODO)
    # 'LoginNotify',

    'Math',

    # Skipped, incompatible with other extensions (TODO)
    # 'MultimediaViewer',

    # Skipped, non-trivial (TODO)
    # 'Nuke',

    # Skipped, non-trivial (TODO)
    # 'OATHAuth',

    'PageImages',
    'ParserFunctions',
    'PdfHandler',
    'Poem',

    # Skipped, non-trivial (TODO)
    # 'ReplaceText',

    # Skipped, non-trivial (TODO)
    # 'Scribunto',

    # Skipped, non-trivial (TODO)
    # 'SecureLinkFixer',

    'SpamBlacklist',

    # Skipped, non-trivial (TODO)
    # 'SyntaxHighlight_GeSHi',

    'TemplateData',

    # Skipped, non-trivial (TODO)
    # 'TextExtracts',

    'Thanks',

    # Skipped, non-trivial (TODO)
    # 'TitleBlacklist',

    'VisualEditor',
    'WikiEditor',
]

gatedextensions = [
    'AbuseFilter',
    'AntiSpoof',
    'Babel',
    'BetaFeatures',
    'CheckUser',
    'CirrusSearch',
    'cldr',
    'ContentTranslation',
    'CommunityConfiguration',
    'CommunityConfigurationExample',  # Required by CommunityConfiguration
    'Disambiguator',
    'Echo',
    'Elastica',
    'EventBus',
    'EventLogging',
    'EventStreamConfig',
    'FileImporter',
    'GeoData',
    'GlobalCssJs',
    'GlobalPreferences',
    'Graph',
    'GrowthExperiments',
    'GuidedTour',
    'IPInfo',
    'JsonConfig',
    'Kartographer',
    'Math',
    'MediaModeration',
    'MobileApp',
    'MobileFrontend',
    'NavigationTiming',
    'PageImages',
    'PageTriage',
    'PageViewInfo',
    'ProofreadPage',
    'SandboxLink',
    'Scribunto',
    'SiteMatrix',
    'TemplateData',
    'Thanks',
    'TimedMediaHandler',
    'Translate',
    'UniversalLanguageSelector',
    'VisualEditor',
    'Wikibase',
    'WikibaseCirrusSearch',
    'WikibaseMediaInfo',
    'WikiLove',
    'WikimediaMessages',
]
gatedskins = [
    'MinervaNeue',
    'Vector',
]


def set_gated_extensions(item, job, params):
    deps = []
    skin_deps = []
    # When triggered from the experimental pipeline, add the project to the
    # list of dependencies. Used to inject an extension which is not yet
    # participating.
    if(params['ZUUL_PIPELINE'] == 'experimental'):
        if params['ZUUL_PROJECT'].startswith('mediawiki/extensions/'):
            deps.append(params['ZUUL_PROJECT'].split('/')[-1])
        if params['ZUUL_PROJECT'] == 'mediawiki/services/parsoid':
            deps.append(params['ZUUL_PROJECT'].split('/')[-1])
        if params['ZUUL_PROJECT'].startswith('mediawiki/skins/'):
            skin_deps.append(params['ZUUL_PROJECT'].split('/')[-1])

    deps.extend(tarballextensions)

    # Only run gate extensions on non REL1_XX branches
    if not params['ZUUL_BRANCH'].startswith('REL1_'):
        deps.extend(gatedextensions)
        skin_deps.extend(gatedskins)

    params['EXT_DEPENDENCIES'] = glue_deps('mediawiki/extensions/', deps)
    params['SKIN_DEPENDENCIES'] = glue_deps('mediawiki/skins/', skin_deps)

    # So we can cd $EXT_NAME && composer test - T161895
    split = params['ZUUL_PROJECT'].split('/')
    if len(split) == 3 and split[1] == 'extensions':
        params['EXT_NAME'] = split[-1]
    if len(split) == 3 and split[1] == 'services':
        params['SERVICE_NAME'] = split[-1]
    if len(split) == 3 and split[1] == 'skins':
        params['SKIN_NAME'] = split[-1]


# Map from ZUUL_PROJECT to DOC_PROJECT
# The default is determined in set_doc_variables
doc_destination = {
    'performance/fresnel': 'fresnel',
    'VisualEditor/VisualEditor': 'visualeditor-standalone',
    'oojs/core': 'oojs',
    'mediawiki/libs/node-cssjanus': 'cssjanus',
    'design/codex': 'codex'
}


def set_doc_variables(item, job, params):
    change = item.change
    doc_subpath = ''

    # ref-updated
    if hasattr(change, 'ref'):
        tag = re.match(r'^refs/tags/(.*)', change.ref)
        if tag:
            # For jobs from Zuul "publish" pipeline,
            # using the "zuul-post" trigger in their Jenkins job.
            # Example value 'refs/tags/v1.2.3' -> 'v1.2.3'
            doc_subpath = tag.group(1)
        else:
            # Branch: 'master'
            doc_subpath = change.ref
    # Changes
    elif hasattr(change, 'refspec'):
        doc_subpath = change.branch

    if doc_subpath:
        params['DOC_SUBPATH'] = doc_subpath

    if 'ZUUL_PROJECT' in params:
        dest = ''
        repo_name = params['ZUUL_PROJECT']
        if repo_name in doc_destination:
            # custom names
            dest = doc_destination[repo_name]
        elif repo_name.startswith('mediawiki/extensions/'):
            # For MediaWiki extension repositories we use the basename
            dest = repo_name.split('/')[-1]
        else:
            dest = repo_name

        # Normalize the project name by removing /'s
        params['DOC_PROJECT'] = dest.replace('/', '-')
