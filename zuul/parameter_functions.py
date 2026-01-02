"""
Parameter functions for zuul jobs

Combined into one Python function due to T125498
"""

import inspect
import os
import re

import yaml


# Find the configuration directory to load the dependencies YAML files
#
# This code is read() by Zuul and executed using something such as:
#
#  fn = os.path.realpath("parameters_functions.py")
#  with open(fn) as _f:
#      code = compile(_f.read(), fn, 'exec')
#      # Execute with no globals set
#      exec(code, {})
#
# Since the execution is done with no globals, __file__ is not set and we can't
# use it to retrieve the directory holding the dependencies YAML files. Given
# the code was compiled with the fullname for context, it can be retrieved
# using inspect() and thus retrieve directory holding the Zuul config files.
def getZuulConfigDir():
    return os.path.dirname(
        inspect.getfile(inspect.currentframe())
        )


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
        'quibble',
        )
    if (
        job.name.startswith(mw_deps_jobs_starting_with)
        and job.name != 'quibble-requires-only-non-voting'
    ):
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
        # ... temporarily exclude extensions that have issues
        # with parallel tests
        params["ZUUL_PROJECT"] not in [
            # DonationInterface uses a different branching model. Its master
            # branch is tested with mediawiki/core fundraising/REL1_43 branch
            # which does not have the parallel work.
            "mediawiki/extensions/DonationInterface",

            # MediaWiki core PhpUnitXmlManager.php assumes test classes and
            # file names match. MediaWikiFarm prefixes classes names while the
            # files names use the shorthand.
            #
            # For example \MediaWikiFarmHooksTest is in HooksTest.php and it
            # thus can't be found by the PHPUnit tests splitter: T398023.
            #
            # The extension classes should have the prefix dropped in favor of
            # using PHP namespaces. Meanwhile disable parallel testing.
            "mediawiki/extensions/MediaWikiFarm",
        ]
        # ... exclude on pre-1.44 REL_ branches (not yet tested/patched),
        and "ZUUL_BRANCH" in params
        and not (
            params["ZUUL_BRANCH"].startswith("REL1_43")
        )
        # Exclude fundraising branches and specific jobs
        and not params["ZUUL_BRANCH"].startswith("fundraising")
        and not job.name.startswith("quibble-fundraising")
    ):
        params['QUIBBLE_PHPUNIT_PARALLEL'] = '1'
        params['MW_RESULTS_CACHE_SERVER_BASE_URL'] = \
            'https://phpunit-results-cache.toolforge.org/results'

    if job.name.startswith('integration-quibble-fullrun-opensearch'):
        params['QUIBBLE_OPENSEARCH'] = 'true'

    # Enable Open Search for Wikibase API tests. T386691
    if (
        params['ZUUL_PROJECT'] == 'mediawiki/extensions/Wikibase'
        and params['ZUUL_BRANCH'] == 'master'
        and job.name.startswith('quibble-apitests-only')
    ):
        params['QUIBBLE_OPENSEARCH'] = 'true'

    # parallel-lint can be slow, so raise the limit for vendor.git
    if params['ZUUL_PROJECT'].startswith('mediawiki/vendor'):
        params['COMPOSER_PROCESS_TIMEOUT'] = 600

    if job.name.startswith('quibble-with-gated-extensions-'):
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
        elif (params['ZUUL_PROJECT'] == 'operations/debs/nginx-ech'):
            # Nginx support for Encrypted Client Hello (ECH) also needs a
            # specific libssl version - T205378
            params['COMPONENT'] = 'component/nginx-ech'
        elif (params['ZUUL_PROJECT']
              == 'operations/debs/contenttranslation/giella-sme'):
            # Heavy build T143546
            params['BUILD_TIMEOUT'] = 180  # minutes


ZUUL_CONFIG_DIR = getZuulConfigDir()

# This hash is used to inject dependencies for MediaWiki jobs.
#
# Note! This list is not used by Phan. Edit the other file for that list.

with open(os.path.join(ZUUL_CONFIG_DIR, "dependencies.yaml")) as stream:
    try:
        dependencies = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        print(error)

# This hash is used to inject dependencies for MediaWiki phan jobs.
#
# This list is *not* recursively processed.
#
# Note! This list is only used by Phan. Edit the other file for PHPUnit etc.
with open(os.path.join(ZUUL_CONFIG_DIR, "phan_dependencies.yaml")) as stream:
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
        # 'Vector' skin name is set as EXT_NAME (T402398)
        params['EXT_NAME'] = split[-1]

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
        params['MW_ZUUL_RECURSE'] = dependencies.get(dep_key, {}).get('recurse')

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

    def resolve_deps(ext, recurse=True):
        resolved.add(ext)
        deps = set()

        if ext in mapping:
            if 'recurse' in mapping[ext]:
                # Format to have some extensions opt out recursive processing,
                # example:
                #
                #   Foo:
                #     recurse: False
                #     dependencies:
                #      - Bar
                recurse = mapping[ext]['recurse']
                mapping_deps = mapping[ext]['dependencies']
            else:
                # Legacy format, the mapping has the list of dependencies since
                # for Phan we never processed them recursively.
                #
                #   Foo:
                #    - Bar
                #
                mapping_deps = mapping[ext]

            for dep in mapping_deps:
                deps.add(dep)

                if recurse and dep not in resolved:
                    deps = deps.union(resolve_deps(dep, recurse))

        return deps

    return resolve_deps(key, recurse)


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
    'CampaignEvents',
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
    'WikimediaCampaignEvents',
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
        # 'Vector' skin name is set as EXT_NAME (T402398)
        params['EXT_NAME'] = split[-1]


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
