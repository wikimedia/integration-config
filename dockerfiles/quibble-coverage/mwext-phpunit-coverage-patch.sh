#!/bin/bash
#
# Verify coverage has improved for a MediaWiki extension patch
# Copyright (C) 2017-2018 Kunal Mehta <legoktm@member.fsf.org>
# Copyright (C) 2018 Antoine Musso <hashar@free.fr>
#
# Requires ZUUL_PROJECT to be set.
#
# Also require environment variables set by Quibble:
# - LOG_DIR
# - MW_INSTALL_PATH
# - WORKSPACE
#
# Outputs:
# - Coverage check reports in $LOG_DIR/coverage.html

set -eux -o pipefail

# Absolute path to the extension, which is the MediaWiki installation path +
# the Gerrit project name stripped from the `mediawiki/` prefix.
EXT_DIR="$MW_INSTALL_PATH/${ZUUL_PROJECT#mediawiki/}"

cd "$EXT_DIR"

# TEST_DIR must be relative. It is passed to `phpunit-patch-coverage` which
# expects --test-dir to be relative to the extension git root repository.
TEST_DIR="tests/phpunit"
if [ ! -d "$TEST_DIR" ]; then
    echo "Folder $TEST_DIR does not exist. Falling back to extension root..."
    # This is for Wikibase, see T288396
    TEST_DIR="."
fi
# We need to pass the config file explicitly to PHPUnit to avoid T395470#11548714
CONFIG_PATH="$MW_INSTALL_PATH/phpunit.xml.dist"

# Edit the PHPUnit configuration to use the proper coverage paths
phpunit-suite-edit "$CONFIG_PATH" \
    --cover-extension "${ZUUL_PROJECT#mediawiki/}"

exec phpunit-patch-coverage check \
    --command "php -d extension=pcov.so -d pcov.enabled=1 -d pcov.directory=$PWD -d pcov.exclude='@(tests|vendor)@' -d pcov.initial.files=3000 \"\$MW_INSTALL_PATH\"/vendor/bin/phpunit -c $CONFIG_PATH" \
    --html "$LOG_DIR"/coverage.html \
    --test-dir "$TEST_DIR"
