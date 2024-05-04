"""
Parameter functions for zuul jobs

Combined into one Python function due to T125498
"""

import re


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
    if job.name == 'wikibase-client':
        params['EXT_DEPENDENCIES'] = '\\n'.join([
            'mediawiki/extensions/Scribunto',
            'mediawiki/extensions/Capiunto',
            'mediawiki/extensions/cldr',
            'mediawiki/extensions/Echo',
        ])

    if job.name == 'wikibase-repo':
        params['EXT_DEPENDENCIES'] = '\\n'.join([
            'mediawiki/extensions/CirrusSearch',
            'mediawiki/extensions/Elastica',
            'mediawiki/extensions/GeoData',
            'mediawiki/extensions/cldr',
        ])

    # parallel-lint can be slow
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
        elif (params['ZUUL_PROJECT']
              == 'operations/debs/contenttranslation/giella-sme'):
            # Heavy build T143546
            params['BUILD_TIMEOUT'] = 180  # minutes


# This hash is used to inject dependencies for MediaWiki jobs.
#
# Values are assumed to be MediaWiki extensions. Skins have to be prefixed with
# 'skins/'.  The has is used by the set_mw_dependencies() parameter function
# below.
# Note! This list is not used by Phan. Scroll down farther for that list.
dependencies = {
    # Skins are listed first to highlight the skin dependencies
    'skins/BlueSpiceCalumma': ['BlueSpiceFoundation'],
    'skins/BlueSpiceDiscovery': ['BlueSpiceFoundation', 'MenuEditor'],
    'skins/Cosmos': ['AdminLinks', 'CookieWarning', 'CreateRedirect',
                     'DismissableSiteNotice', 'Echo', 'SocialProfile',
                     'Video', 'VisualEditor'],
    'skins/Empty': ['PhpTags'],
    'skins/MinervaNeue': ['MobileFrontend'],
    'skins/Refreshed': ['SocialProfile'],
    'skins/TuleapSkin': ['TuleapIntegration', 'TuleapWikiFarm'],

    # Extensions
    # One can add a skin by using: 'skin/XXXXX'
    '3D': ['MultimediaViewer'],
    'AbuseFilter': ['AntiSpoof', 'CentralAuth', 'CodeEditor',
                    'CheckUser', 'Echo', 'Renameuser', 'Scribunto',
                    'EventLogging', 'UserMerge'],
    'AchievementBadges': ['BetaFeatures', 'Echo'],
    'AdvancedSearch': ['Translate'],
    'ApiFeatureUsage': ['Elastica'],
    'Arrays': ['Loops', 'ParserFunctions'],
    'ArticlePlaceholder': ['Wikibase', 'Scribunto'],
    'AtMentions': ['OOJSPlus', 'VisualEditor'],
    'BlogPage': ['Comments', 'SocialProfile', 'VoteNY'],
    'BlueSpiceAbout': ['BlueSpiceFoundation'],
    'BlueSpiceArticleInfo': ['BlueSpiceFoundation'],
    'BlueSpiceArticlePreviewCapture': ['BlueSpiceFoundation'],
    'BlueSpiceAuthors': ['BlueSpiceFoundation'],
    'BlueSpiceAvatars': ['BlueSpiceFoundation'],
    'BlueSpiceBookshelf': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector',
        'ContentDroplets',
        'MenuEditor'
    ],
    'BlueSpiceCategoryCheck': ['BlueSpiceFoundation'],
    'BlueSpiceCategoryManager': ['BlueSpiceFoundation'],
    'BlueSpiceChecklist': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceConfigManager': ['BlueSpiceFoundation'],
    'BlueSpiceContextMenu': ['BlueSpiceFoundation'],
    'BlueSpiceCountThings': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceCustomMenu': ['BlueSpiceFoundation', 'MenuEditor'],
    'BlueSpiceDashboards': ['BlueSpiceFoundation'],
    'BlueSpiceDistributionConnector': [
        'BlueSpiceFoundation',
        'BlueSpiceSMWConnector',
        'ContentDroplets',
        'Echo',
        'OOJSPlus',
        'UserMerge',
        'Workflows'
    ],
    'BlueSpiceEchoConnector': ['BlueSpiceFoundation', 'Echo'],
    'BlueSpiceEmoticons': ['BlueSpiceFoundation'],
    'BlueSpiceExpiry': ['BlueSpiceFoundation', 'BlueSpiceReminder'],
    'BlueSpiceExportTables': [
        'BlueSpiceFoundation',
        'BlueSpiceUEModuleTable2Excel',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceExtendedFilelist': ['BlueSpiceFoundation'],
    'BlueSpiceExtendedSearch': [
        'BlueSpiceDistributionConnector',
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceExtendedStatistics': ['BlueSpiceFoundation',
                                    'BlueSpiceExtendedSearch'],
    'BlueSpiceFilterableTables': ['BlueSpiceFoundation'],
    'BlueSpiceFlaggedRevsConnector': ['BlueSpiceFoundation', 'FlaggedRevs'],
    'BlueSpiceGroupManager': ['BlueSpiceFoundation'],
    'BlueSpiceHideTitle': ['BlueSpiceFoundation'],
    'BlueSpiceInsertCategory': ['BlueSpiceFoundation'],
    'BlueSpiceInsertFile': ['BlueSpiceFoundation'],
    'BlueSpiceInsertLink': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceInsertMagic': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceFoundation': ['ExtJSBase', 'OOJSPlus'],
    'BlueSpiceInsertTemplate': ['BlueSpiceFoundation'],
    'BlueSpiceInstanceStatus': ['BlueSpiceFoundation'],
    'BlueSpiceInterWikiLinks': ['BlueSpiceFoundation'],
    'BlueSpiceInterwikiSearch': ['BlueSpiceFoundation'],
    'BlueSpiceMultiUpload': ['BlueSpiceFoundation'],
    'BlueSpiceNamespaceCSS': ['BlueSpiceFoundation'],
    'BlueSpiceNamespaceManager': ['BlueSpiceFoundation'],
    'BlueSpiceNSFileRepoConnector': ['BlueSpiceFoundation', 'NSFileRepo'],
    'BlueSpicePageAccess': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpicePageAssignments': ['BlueSpiceFoundation'],
    'BlueSpicePageFormsConnector': ['BlueSpiceFoundation', 'PageForms'],
    'BlueSpicePageTemplates': [
        'BlueSpiceFoundation',
        'BlueSpiceDistributionConnector',
        'ContentDroplets'
    ],
    'BlueSpicePageVersion': ['BlueSpiceFoundation'],
    'BlueSpicePagesVisited': [
        'BlueSpiceDistributionConnector',
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector',
        'BlueSpiceWhoIsOnline',
    ],
    'BlueSpicePlayer': ['BlueSpiceFoundation'],
    'BlueSpicePermissionManager': ['BlueSpiceFoundation'],
    'BlueSpicePrivacy': ['BlueSpiceFoundation'],
    'BlueSpiceProDistributionConnector': [
        'BlueSpiceFoundation',
        'BlueSpiceUEModulePDF',
        'BlueSpiceUniversalExport',
        'BlueSpiceVisualEditorConnector',
        'Math',
    ],
    'BlueSpiceQrCode': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceRating': ['BlueSpiceFoundation'],
    'BlueSpiceRSSFeeder': ['BlueSpiceFoundation'],
    'BlueSpiceReaders': ['BlueSpiceFoundation'],
    'BlueSpiceReadConfirmation': [
        'BlueSpiceFoundation',
        'BlueSpicePageAssignments'
    ],
    'BlueSpiceReminder': ['BlueSpiceFoundation', 'Workflows'],
    'BlueSpiceSMWConnector': ['BlueSpiceFoundation', 'BlueSpiceSmartList'],
    'BlueSpiceSocial': ['BlueSpiceFoundation', 'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialArticleActions': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                                      'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialBlog': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                            'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialComments': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                                'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialMicroBlog': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                                 'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialProfile': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                               'BlueSpiceExtendedSearch', 'BlueSpiceAvatars'],
    'BlueSpiceSocialRating': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                              'BlueSpiceExtendedSearch', 'BlueSpiceRating'],
    'BlueSpiceSocialResolve': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                               'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialTags': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                            'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialTimelineUpdate': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                                      'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialTopics': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                              'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialWatch': ['BlueSpiceFoundation', 'BlueSpiceSocial',
                             'BlueSpiceExtendedSearch'],
    'BlueSpiceSocialWikiPage': [
        'BlueSpiceFoundation',
        'BlueSpiceSocial',
        'BlueSpiceExtendedSearch',
        'BlueSpiceMultiUpload',
        'BlueSpiceEchoConnector'
    ],
    'BlueSpiceSaferEdit': ['BlueSpiceFoundation'],
    'BlueSpiceSignHere': ['BlueSpiceFoundation'],
    'BlueSpiceSmartList': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceSubPageTree': ['BlueSpiceFoundation'],
    'BlueSpiceTagCloud': ['BlueSpiceFoundation'],
    'BlueSpiceUEModuleBookPDF': ['BlueSpiceFoundation',
                                 'BlueSpiceUniversalExport',
                                 'BlueSpiceBookshelf',
                                 'BlueSpiceUEModulePDF'],
    'BlueSpiceUEModuleDOCX': [
        'BlueSpiceFoundation',
        'BlueSpiceUniversalExport',
    ],
    'BlueSpiceUEModulePDF': [
        'BlueSpiceFoundation',
        'BlueSpiceUniversalExport',
    ],
    'BlueSpiceUEModulePDFRecursive': [
        'BlueSpiceFoundation',
        'BlueSpiceUniversalExport',
    ],
    'BlueSpiceUEModulePDFSubpages': [
        'BlueSpiceFoundation',
        'BlueSpiceUniversalExport',
    ],
    'BlueSpiceUEModuleHTML': [
        'BlueSpiceFoundation',
        'BlueSpiceUniversalExport',
    ],
    'BlueSpiceUEModuleTable2Excel': ['BlueSpiceFoundation',
                                     'BlueSpiceUniversalExport'],
    'BlueSpiceUniversalExport': [
        'BlueSpiceFoundation',
        'BlueSpiceVisualEditorConnector'
    ],
    'BlueSpiceUsageTracker': ['BlueSpiceFoundation'],
    'BlueSpiceUserInfo': ['BlueSpiceFoundation'],
    'BlueSpiceUserManager': ['BlueSpiceFoundation'],
    'BlueSpiceUserSidebar': ['BlueSpiceFoundation', 'MenuEditor'],
    'BlueSpiceVisualDiff': ['BlueSpiceFoundation'],
    'BlueSpiceVisualEditorConnector': [
        'BlueSpiceFoundation',
        'OOJSPlus',
        'VisualEditor',
        'VisualEditorPlus'
    ],
    'BlueSpiceWatchList': ['BlueSpiceFoundation'],
    'BlueSpiceWhoIsOnline': ['BlueSpiceFoundation'],
    'BlueSpiceWikiExplorer': ['BlueSpiceFoundation'],
    'BounceHandler': ['Echo', 'CentralAuth'],
    'CampaignEvents': ['WikimediaCampaignEvents'],
    'Campaigns': ['EventLogging'],
    'Capiunto': ['Scribunto'],
    'CentralAuth': ['AbuseFilter', 'AntiSpoof', 'SecurePoll'],
    'CentralNotice': ['EventLogging'],
    'Challenge': ['SocialProfile'],
    'Checklists': ['VisualEditor'],
    'CheckUser': ['CentralAuth', 'FlaggedRevs', 'GuidedTour', 'Renameuser',
                  'TorBlock', 'UserMerge'],
    'Cite': ['Gadgets', 'ParserFunctions', 'Popups', 'VisualEditor',
             'WikiEditor'],
    'Citoid': ['Cite', 'VisualEditor'],
    'CirrusSearch': ['TimedMediaHandler', 'PdfHandler', 'Cite', 'Elastica',
                     'GeoData', 'BetaFeatures', 'SiteMatrix',
                     'WikibaseCirrusSearch', 'EventBus'],
    'CodeEditor': ['WikiEditor'],
    'CodeMirror': ['WikiEditor', 'VisualEditor'],
    'CognitiveProcessDesigner': ['PageForms',
                                 'BlueSpiceVisualEditorConnector'],
    'CollaborationKit': ['EventLogging', 'VisualEditor'],
    'ConfigManager': ['BlueSpiceFoundation'],
    'ContactManager': ['PageProperties'],
    'ContainerFilter': ['VisualEditor'],
    'ContentDroplets': ['VisualEditor'],
    'ContentStabilization': ['BlueSpiceBookshelf', 'BlueSpiceFoundation',
                             'BlueSpiceSMWConnector', 'OOJSPlus', 'Workflows'],
    'ContentTranslation': ['AbuseFilter', 'Echo', 'EventLogging',
                           'UniversalLanguageSelector', 'VisualEditor'],
    'ContributorsAddon': ['Contributors'],
    'CookieWarning': ['MobileFrontend'],
    'CreateAPage': ['WikiEditor'],
    'CustomPage': ['skins/CustomPage'],
    'Dashiki': ['JsonConfig'],
    'DateTimeTools': ['VisualEditor'],
    'Disambiguator': ['VisualEditor'],
    'DiscordRCFeed': ['Flow'],
    'DiscussionTools': ['VisualEditor', 'Linter', 'Echo', 'Thanks'],
    'DrawioEditor': ['VisualEditor'],
    'Echo': ['CentralAuth', 'EventLogging', 'MobileFrontend'],
    'EditNotify': ['Echo'],
    'ElectronPdfService': ['Collection'],
    'EmailAuthorization': ['PluggableAuth'],
    'EncryptedUploads': ['UploadWizard'],
    'EnhancedStandardUIs': ['OOJSPlus'],
    'EnhancedUpload': ['OOJSPlus', 'VisualEditor'],
    'EntitySchema': ['Wikibase'],
    'EventBus': ['EventStreamConfig'],
    'EventLogging': ['EventStreamConfig', 'EventBus'],
    'ExternalGuidance': ['MobileFrontend', 'UniversalLanguageSelector'],
    'FacetedCategory': ['CategoryTree'],
    'FanBoxes': ['SocialProfile'],
    'FileAnnotations': ['EventLogging'],
    'FileImporter': ['CentralAuth', 'WikiEditor'],
    'FlaggedRevs': ['Scribunto'],
    'FlexiSkin': ['BlueSpiceFoundation', 'OOJSPlus', 'CodeEditor'],
    'Flow': ['AbuseFilter', 'BetaFeatures', 'Echo', 'VisualEditor'],
    'Forms': ['OOJSPlus'],
    'FundraiserLandingPage': ['EventLogging'],
    'FundraisingTranslateWorkflow': ['Translate'],
    'GeoData': ['CirrusSearch'],
    'GettingStarted': ['CentralAuth', 'EventLogging', 'GuidedTour'],
    'GlobalBlocking': ['CentralAuth'],
    'GlobalContribs': ['Editcount'],
    'Graph': ['CodeEditor', 'JsonConfig', 'VisualEditor'],
    'GrowthExperiments': ['skins/MinervaNeue', 'PageViewInfo', 'PageImages',
                          'EventLogging', 'Flow', 'MobileFrontend', 'Echo',
                          'CirrusSearch', 'VisualEditor', 'Thanks',
                          'CommunityConfiguration'],
    'GuidedTour': ['EventLogging'],
    'HierarchyBuilder': ['PageForms'],
    'ImageMetrics': ['EventLogging'],
    'ImageRating': ['VoteNY'],
    'ImageSuggestions': ['Echo', 'CirrusSearch', 'Elastica'],
    'IPInfo': ['BetaFeatures'],
    'JsonConfig': ['Scribunto', 'Kartographer'],
    'JWTAuth': ['PluggableAuth'],
    'Kartographer': ['FlaggedRevs', 'JsonConfig', 'ParserFunctions',
                     'VisualEditor', 'WikimediaMessages'],
    'LanguageTool': ['VisualEditor'],
    'LDAPAuthentication2': ['LDAPProvider', 'PluggableAuth'],
    'LDAPAuthorization': ['LDAPProvider', 'PluggableAuth'],
    'LDAPGroups': ['LDAPProvider'],
    'LDAPSyncAll': ['LDAPGroups', 'LDAPProvider', 'LDAPUserInfo'],
    'LDAPUserInfo': ['LDAPProvider'],
    'LightweightRDFa': ['WikiEditor'],
    'LoginNotify': ['CentralAuth', 'CheckUser', 'Echo'],
    'MagicLinkAuthentication': ['PluggableAuth'],
    'MassMessage': ['CentralAuth', 'Flow', 'LiquidThreads'],
    'MassMessageEmail': ['MassMessage'],
    'Math': ['VisualEditor', 'Wikibase'],
    'MathSearch': ['Math'],
    'MediaSearch': ['CirrusSearch', 'WikibaseCirrusSearch'],
    'MediaUploader': ['AbuseFilter', 'SpamBlacklist'],
    'MenuEditor': ['skins/BlueSpiceDiscovery', 'OOJSPlus'],
    'MobileApp': ['Echo', 'MobileFrontend', 'VisualEditor', 'AbuseFilter'],
    'MobileFrontend': ['Echo', 'VisualEditor', 'MobileApp',
                       'skins/MinervaNeue'],
    'MobileFrontendContentProvider': ['MobileFrontend'],
    'Monstranto': ['Scribunto'],
    'MultimediaViewer': ['BetaFeatures'],
    'NamespacePopups': ['PagePopups'],
    'NavigationTiming': ['EventLogging'],
    'NaylorAMS': ['PluggableAuth'],
    'NSFileRepo': ['EnhancedUpload', 'Lockdown'],
    'Newsletter': ['Echo'],
    'OATHAuth': ['CheckUser', 'Echo', 'WebAuthn'],
    'OAuth': ['AbuseFilter', 'Echo'],
    'OAuthRateLimiter': ['OAuth'],
    'OpenIDConnect': ['PluggableAuth'],
    'OpenStackManager': ['LdapAuthentication', 'Echo', 'TitleBlacklist'],
    'PageCheckout': ['Workflows'],
    'PageTriage': ['WikiLove', 'ORES', 'Echo'],
    'PageViewInfo': ['Graph'],
    'PageViewInfoGA': ['PageViewInfo'],
    'ParserFunctions': ['Scribunto'],
    'parsoid': ['TimedMediaHandler', 'ParserFunctions'],
    'Phonos': ['TimedMediaHandler'],
    'PhpTagsFunctions': ['PhpTags'],
    'PhpTagsSPARQL': ['PhpTags'],
    'PhpTagsSMW': ['PhpTags'],
    'PhpTagsStorage': ['PhpTags', 'PhpTagsFunctions', 'PhpTagsWiki',
                       'PhpTagsWidgets'],
    'PhpTagsWidgets': ['PhpTags', 'PhpTagsFunctions', 'PhpTagsWiki'],
    'PhpTagsWiki': ['PhpTags', 'PhpTagsFunctions'],
    'PictureGame': ['SocialProfile'],
    'PollNY': ['SocialProfile'],
    'Popups': ['TextExtracts', 'PageImages', 'EventLogging',
               'Cite'],
    'Premoderation': ['skins/Vector'],
    'PronunciationRecording': ['UploadWizard'],
    'ProofreadPage': ['LabeledSectionTransclusion', 'Scribunto',
                      'VisualEditor', 'BetaFeatures'],
    'PropertySuggester': ['Wikibase', 'EventLogging'],
    'QuickSurveys': ['EventLogging'],
    'QuizGame': ['Renameuser', 'SocialProfile'],
    'RandomGameUnit': ['SocialProfile', 'PictureGame', 'PollNY', 'QuizGame'],
    'RegexFun': ['ParserFunctions', 'Arrays'],
    'RelatedArticles': ['BetaFeatures', 'MobileFrontend'],
    'ReplaceText': ['AdminLinks'],
    'ReportIncident': ['DiscussionTools'],
    'RevisionSlider': ['MobileFrontend'],
    'Score': ['VisualEditor', 'TimedMediaHandler', 'Wikibase'],
    'Scribunto': ['SyntaxHighlight_GeSHi'],
    'SearchVue': ['WikimediaMessages'],
    'Shibboleth': ['PluggableAuth'],
    'SimilarEditors': ['QuickSurveys'],
    'SiteMetrics': ['SocialProfile'],
    'SiteScout': ['Comments', 'SocialProfile', 'VoteNY'],
    'SimpleSAMLphp': ['PluggableAuth'],
    'SimpleSurvey': ['PrefSwitch'],
    'SimpleTasks': ['Checklists', 'AtMentions', 'DateTimeTools'],
    'SocialProfile': ['WikiEditor'],
    'Sofa': ['Scribunto'],
    'SoftRedirector': ['VisualEditor'],
    'SpamBlacklist': ['AbuseFilter', 'CheckUser', 'EventLogging'],
    'SpamDiffTool': ['SpamBlacklist'],
    'SpellingDictionary': ['UniversalLanguageSelector'],
    'SportsTeams': ['SocialProfile', 'UserStatus', 'BlogPage'],
    'StandardDialogs': ['OOJSPlus'],
    'StickyTOC': ['skins/chameleon'],
    'StopForumSpam': ['AbuseFilter'],
    'SyntaxHighlight_GeSHi': ['VisualEditor'],
    'TEI': ['CodeMirror', 'Math', 'VisualEditor'],
    'TemplateWizard': ['TemplateData', 'WikiEditor'],
    'TitleBlacklist': ['AntiSpoof', 'Scribunto'],
    'TheWikipediaLibrary': ['Echo', 'CentralAuth', 'GlobalPreferences'],
    'Thanks': ['Echo', 'Flow', 'MobileFrontend'],
    'Translate': ['UniversalLanguageSelector', 'EventLogging', 'cldr',
                  'VisualEditor'],
    'TranslateSvg': ['Translate'],
    'TranslationNotifications': ['MassMessage', 'Translate'],
    'Toolhub': ['Scribunto'],
    'TopTenPages': ['HitCounters'],
    'TorBlock': ['AbuseFilter'],
    'TuleapIntegration': ['TuleapWikiFarm'],
    'TuleapWikiFarm': ['TuleapIntegration'],
    'TwitterCards': ['TextExtracts'],
    'TwnMainPage': ['Translate'],
    'TwoColConflict': ['BetaFeatures', 'EventLogging', 'WikiEditor'],
    'UniversalLanguageSelector': ['EventLogging'],
    'UnlinkedWikibase': ['Scribunto'],
    'UploadWizard': ['WikimediaMessages', 'EventLogging', 'AbuseFilter',
                     'SpamBlacklist'],
    'UserStatus': ['SocialProfile', 'SportsTeams', 'BlogPage'],
    'VECancelButton': ['VisualEditor'],
    'VEForAll': ['VisualEditor'],
    'VikiSemanticTitle': ['VIKI'],
    'VikiTitleIcon': ['VIKI'],
    'VisualEditor': ['Cite', 'TemplateData', 'FlaggedRevs', 'ConfirmEdit',
                     'DiscussionTools'],
    'WebAuthn': ['OATHAuth'],
    'WebDAVClientIntegration': ['WebDAV'],
    'WebDAVMinorSave': ['WebDAV'],
    'WhoIsWatching': ['Echo'],
    'Wikibase': [
        'ArticlePlaceholder',
        'CirrusSearch',
        'cldr',
        'Elastica',
        'GeoData',
        # temporarily dropped due to excessive slowness (T231198)
        # 'Scribunto',
        # 'Capiunto',
        'Echo',
        'PropertySuggester',
        'WikibaseQualityConstraints',
        'WikimediaBadges',
        'WikibaseMediaInfo',
        'WikibaseLexeme',
        'skins/MinervaNeue',
        'MobileFrontend',
    ],
    'WikibaseCirrusSearch': ['Wikibase', 'CirrusSearch'],
    'WikibaseLexeme': ['Wikibase', 'WikibaseLexemeCirrusSearch'],
    'WikibaseLexemeCirrusSearch': ['Wikibase', 'WikibaseLexeme',
                                   'CirrusSearch',
                                   'WikibaseCirrusSearch'],
    'WikibaseManifest': ['Wikibase', 'OAuth'],
    'WikibaseMediaInfo': ['Wikibase', 'UniversalLanguageSelector',
                          'WikibaseCirrusSearch'],
    'WikibaseQualityConstraints': ['Wikibase', 'WikibaseLexeme'],
    'Wikidata.org': ['Wikibase'],
    'WikidataPageBanner': ['Wikibase'],
    'WikiEditor': ['EventLogging', 'WikimediaEvents'],
    'WikiLambda': ['WikimediaMessages'],
    'WikimediaBadges': ['Wikibase'],
    'WikimediaCampaignEvents': ['CampaignEvents'],
    'WikimediaEvents': ['EventLogging'],
    'WikiSEO': ['PageImages', 'Scribunto'],
    'Wikisource': ['Wikibase', 'ProofreadPage'],
    'Wikistories': ['BetaFeatures', 'EventLogging', 'MobileFrontend',
                    'skins/MinervaNeue', 'Echo'],
    'WikiToLDAP': ['LDAPAuthentication2', 'Renameuser', 'UserMerge'],
    'wikihiero': ['VisualEditor'],
    'Workflows': ['Forms', 'OOJSPlus'],
    'WSOAuth': ['PluggableAuth'],
}

# Dependencies used in phan jobs.
# This list is *not* recursively processed.
phan_dependencies = {
    'skins/Cosmos': ['AdminLinks', 'CookieWarning', 'SocialProfile'],
    'skins/Metrolook': ['SocialProfile'],
    'skins/MinervaNeue': ['Echo', 'MobileFrontend'],
    'skins/Nimbus': ['Echo', 'RandomGameUnit', 'SocialProfile', 'Video'],
    'skins/Refreshed': ['SocialProfile'],
    'skins/Vector': ['CentralAuth'],
    'AbuseFilter': ['CheckUser', 'CentralAuth', 'Echo', 'Renameuser',
                    'AntiSpoof', 'Scribunto', 'EventLogging', 'UserMerge',
                    'ConfirmEdit'],
    'AntiSpoof': ['UserMerge'],
    'ApiFeatureUsage': ['Elastica'],
    'ArticleFeedbackv5': ['AbuseFilter', 'Echo', 'SpamBlacklist', 'SpamRegex'],
    'ArticlePlaceholder': ['Scribunto', 'Wikibase'],
    'BlogPage': ['Comments', 'RandomGameUnit', 'SocialProfile', 'Video',
                 'VoteNY'],
    'BlueSpiceAvatars': ['BlueSpiceFoundation', 'BlueSpicePrivacy'],
    'BounceHandler': ['CentralAuth', 'Echo'],
    'CampaignEvents': ['Echo', 'Translate'],
    'Campaigns': ['EventLogging', 'MobileFrontend'],
    'Capiunto': ['Scribunto'],
    'CentralAuth': ['AbuseFilter', 'AntiSpoof', 'ConfirmEdit', 'Echo',
                    'EventLogging', 'MassMessage', 'MobileFrontend',
                    'Renameuser', 'SecurePoll', 'TitleBlacklist'],
    'CentralNotice': ['CentralAuth', 'MobileFrontend', 'Translate', 'cldr',
                      'UserMerge'],
    'Challenge': ['Echo', 'SocialProfile'],
    'CheckUser': ['CentralAuth', 'EventLogging', 'GuidedTour', 'Renameuser',
                  'FlaggedRevs', 'GlobalBlocking', 'TorBlock', 'UserMerge'],
    'CirrusSearch': ['BetaFeatures', 'Elastica', 'SiteMatrix', 'GeoData',
                     'EventBus'],
    'Cite': ['Gadgets'],
    'Citoid': ['Cite', 'VisualEditor'],
    'CleanChanges': ['cldr'],
    'CodeReview': ['Renameuser'],
    'CognitiveProcessDesigner': ['PageForms', 'BlueSpiceFoundation',
                                 'BlueSpiceUEModulePDF'],
    'CollaborationKit': ['EventLogging', 'PageImages', 'VisualEditor', 'Flow'],
    'CommentStreams': ['Echo', 'SocialProfile'],
    'ConfirmEdit': ['Math'],
    'ContactPage': ['ConfirmEdit'],
    'ContentTranslation': ['AbuseFilter', 'BetaFeatures', 'CentralAuth',
                           'Echo', 'EventLogging', 'GlobalPreferences'],
    'CreateAPage': ['ConfirmEdit'],
    'Dashiki': ['JsonConfig'],
    'Disambiguator': ['VisualEditor'],
    'DiscussionTools': ['VisualEditor', 'Linter', 'Echo', 'EventLogging',
                        'Gadgets', 'BetaFeatures', 'Thanks'],
    'DonationInterface': ['cldr', 'CodeEditor', 'FundraisingEmailUnsubscribe',
                          'ParserFunctions', 'SyntaxHighlight_GeSHi',
                          'WikiEditor'],
    'Echo': ['CentralAuth', 'EventLogging', 'UserMerge'],
    'EntitySchema': ['Wikibase'],
    'EventBus': ['CentralNotice', 'EventStreamConfig'],
    'FacetedCategory': ['CategoryTree'],
    'FanBoxes': ['SocialProfile'],
    'FileImporter': ['GlobalBlocking', 'VisualEditor'],
    'FlaggedRevs': ['Scribunto', 'Echo', 'GoogleNewsSitemap', 'MobileFrontend',
                    'skins/Vector'],
    'Flow': ['AbuseFilter', 'BetaFeatures', 'CentralAuth', 'CheckUser',
             'CirrusSearch', 'ConfirmEdit', 'Echo', 'Elastica', 'GuidedTour',
             'LiquidThreads', 'SpamBlacklist', 'VisualEditor'],
    'FundraisingTranslateWorkflow': ['Translate'],
    'Gadgets': ['CodeEditor'],
    'GettingStarted': ['CentralAuth', 'CirrusSearch', 'MobileFrontend',
                       'VisualEditor'],
    'GeoData': ['CirrusSearch', 'Elastica'],
    'GlobalBlocking': ['CentralAuth', 'Renameuser', 'UserMerge'],
    'GlobalPreferences': ['BetaFeatures', 'skins/Vector'],
    'GrowthExperiments': ['EventLogging', 'PageImages', 'PageViewInfo',
                          'skins/MinervaNeue', 'Flow', 'MobileFrontend',
                          'Echo', 'CirrusSearch', 'CentralAuth',
                          'TimedMediaHandler', 'VisualEditor', 'EventBus',
                          'Thanks', 'CommunityConfiguration'],
    'HAWelcome': ['SocialProfile'],
    'ImageRating': ['SocialProfile', 'VoteNY'],
    'ImageSuggestions': ['Echo', 'CirrusSearch', 'Elastica'],
    'IPInfo': ['EventLogging'],
    'intersection': ['PageImages'],
    'JsonConfig': ['CodeEditor', 'Kartographer', 'Scribunto'],
    'JWTAuth': ['PluggableAuth'],
    'Kartographer': ['FlaggedRevs', 'GeoData', 'JsonConfig'],
    'LiquidThreads': ['Renameuser'],
    'LinkFilter': ['Comments', 'Echo', 'RandomGameUnit', 'Renameuser',
                   'SocialProfile'],
    'LoginNotify': ['CentralAuth', 'Echo'],
    'MassMessage': ['CentralAuth'],
    'MassMessageEmail': ['MassMessage'],
    'Math': ['VisualEditor', 'Wikibase', 'Popups'],
    'MediaSearch': ['CirrusSearch', 'WikibaseCirrusSearch'],
    'MiniInvite': ['BlogPage'],
    'MobileApp': ['AbuseFilter'],
    'MobileFrontend': ['AbuseFilter', 'CentralAuth', 'LiquidThreads',
                       'PageImages', 'Wikibase', 'XAnalytics'],
    'MobileFrontendContentProvider': ['MobileFrontend'],
    'Monstranto': ['Scribunto'],
    'MultimediaViewer': ['MobileFrontend'],
    'Newsletter': ['Echo'],
    'NewSignupPage': ['SocialProfile'],
    'OATHAuth': ['CheckUser', 'Echo', 'WebAuthn'],
    'OAuth': ['AbuseFilter', 'Echo'],
    'OAuthRateLimiter': ['OAuth'],
    'OpenStackManager': ['LdapAuthentication', 'Echo', 'TitleBlacklist'],
    'PageForms': ['AdminLinks', 'Cargo', 'PageSchemas'],
    'PageImages': ['MobileFrontend'],
    'PageTriage': ['Echo', 'ORES'],
    'PageViewInfoGA': ['PageViewInfo'],
    'ParserFunctions': ['Scribunto'],
    'Petition': ['CheckUser', 'cldr'],
    'Phonos': ['TimedMediaHandler'],
    'PictureGame': ['SocialProfile'],
    'PollNY': ['SocialProfile'],
    'Popups': ['EventLogging', 'Gadgets'],
    'ProofreadPage': ['Scribunto', 'BetaFeatures'],
    'PropertySuggester': ['Wikibase', 'EventLogging'],
    'QuizGame': ['Renameuser', 'SocialProfile'],
    # technically speaking PictureGame, PollNY & QuizGame are all dependencies,
    # but PollNY's the only PHP-level hard dependency needed to pass phan
    'RandomGameUnit': ['PollNY'],
    'ReadingLists': ['SiteMatrix'],
    'RelatedArticles': ['Disambiguator'],
    'ReplaceText': ['AdminLinks'],
    'ReportIncident': ['DiscussionTools'],
    'Sanctions': ['Echo', 'Flow', 'Renameuser'],
    'Score': ['TimedMediaHandler', 'Wikibase'],
    'Scribunto': ['SyntaxHighlight_GeSHi', 'CodeEditor'],
    'SecurePoll': ['CentralAuth', 'Flow'],
    'SocialProfile': ['Echo'],
    'Sofa': ['Scribunto'],
    'SoftRedirector': ['VisualEditor'],
    'SpamBlacklist': ['CheckUser', 'EventLogging'],
    'SportsTeams': ['SocialProfile', 'UserStatus', 'BlogPage'],
    'StopForumSpam': ['AbuseFilter'],
    'TEI': ['Math'],
    'TemplateStyles': ['CodeEditor'],
    'Thanks': ['CheckUser', 'Echo', 'Flow', 'MobileFrontend'],
    'TheWikipediaLibrary': ['Echo', 'CentralAuth', 'GlobalPreferences'],
    'TimedMediaHandler': ['BetaFeatures'],
    'TitleBlacklist': ['AntiSpoof', 'Scribunto'],
    'Toolhub': ['Scribunto'],
    'TorBlock': ['AbuseFilter'],
    'Translate': ['AbuseFilter', 'AdminLinks', 'cldr', 'Elastica',
                  'TranslationNotifications'],
    'TranslationNotifications': ['CentralAuth', 'MassMessage', 'SiteMatrix',
                                 'Translate'],
    'TwoColConflict': ['BetaFeatures', 'EventLogging', 'WikiEditor'],
    'UniversalLanguageSelector': ['Babel', 'BetaFeatures', 'MobileFrontend',
                                  'cldr'],
    'UnlinkedWikibase': ['Scribunto'],
    'UserStatus': ['SocialProfile', 'SportsTeams', 'BlogPage'],
    'UploadWizard': ['EventLogging', 'CodeEditor'],
    'VisualEditor': ['BetaFeatures'],
    'VoteNY': ['SocialProfile'],
    'WebAuthn': ['OATHAuth'],
    'WikiEditor': ['BetaFeatures', 'ConfirmEdit', 'EventLogging',
                   'MobileFrontend', 'WikimediaEvents'],
    'WikiLambda': ['EventLogging'],
    'WikiLove': ['Flow', 'LiquidThreads', 'UserMerge'],
    'WikiForum': ['ConfirmEdit', 'SocialProfile'],
    'Wikibase': ['Babel', 'CirrusSearch', 'Echo', 'GeoData',
                 'Math', 'MobileFrontend', 'PageImages', 'Scribunto'],
    'WikibaseCirrusSearch': ['Elastica', 'CirrusSearch', 'Scribunto',
                             'Wikibase'],
    'WikibaseLexeme': ['Wikibase', 'Scribunto'],
    'WikibaseLexemeCirrusSearch': ['CirrusSearch', 'Scribunto', 'Wikibase',
                                   'WikibaseCirrusSearch', 'WikibaseLexeme'],
    'WikibaseManifest': ['Wikibase', 'OAuth', 'Scribunto'],
    'WikibaseMediaInfo': ['Wikibase', 'CirrusSearch', 'Elastica',
                          'WikibaseCirrusSearch'],
    'WikibaseQualityConstraints': ['Wikibase'],
    'Wikidata.org': ['Wikibase'],
    'WikidataPageBanner': ['PageImages', 'Wikibase'],
    'WikimediaBadges': ['Wikibase'],
    'WikimediaCampaignEvents': ['CampaignEvents'],
    'WikimediaEvents': ['AbuseFilter', 'BetaFeatures', 'CentralAuth',
                        'EventBus', 'EventLogging', 'GrowthExperiments',
                        'MobileFrontend'],
    'WikimediaMaintenance': ['AbuseFilter', 'CentralAuth', 'CirrusSearch',
                             'cldr', 'Cognate', 'MassMessage', 'Wikibase'],
    'WikimediaMessages': ['CampaignEvents', 'GuidedTour', 'ORES',
                          'skins/MinervaNeue'],
    'WikiSEO': ['PageImages', 'Scribunto'],
    'Wikistories': ['Echo', 'BetaFeatures', 'MobileFrontend'],
    'WikiToLDAP': ['LDAPAuthentication2', 'LDAPProvider', 'PluggableAuth',
                   'Renameuser', 'UserMerge'],
    'Wikisource': ['Wikibase', 'ProofreadPage']
}


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
    # 'AbuseFilter',
    # 'CategoryTree',

    'Cite',
    'CiteThisPage',
    'CodeEditor',
    'ConfirmEdit',

    # 'DiscussionTools',
    # 'Echo',

    'Gadgets',
    'ImageMap',
    'InputBox',
    'Interwiki',

    # 'Linter',
    # 'LoginNotify',

    'Math',

    # Skipped, incompatible with other extensions (TODO)
    # 'MultimediaViewer',

    # Skipped, non-trivial (TODO)
    # 'Nuke',

    # Skipped, non-trivial (TODO)
    # 'OATHAuth',

    # 'PageImages',

    'ParserFunctions',
    'PdfHandler',
    'Poem',

    # Skipped, non-trivial (TODO)
    # 'ReplaceText',
    # 'Scribunto',
    # 'SecureLinkFixer',

    'SpamBlacklist',

    # 'SyntaxHighlight_GeSHi',

    'TemplateData',

    # 'TextExtracts',
    # 'Thanks',

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
    'JsonConfig',
    'Kartographer',
    'Math',
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
