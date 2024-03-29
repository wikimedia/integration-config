#!/bin/bash
#
# Generate coverage for a MediaWiki skin
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
# - clover.xml and junit.xml in $LOG_DIR
# - HTML report in $WORKSPACE/cover

set -eux -o pipefail

SKIN_NAME=$(basename "$ZUUL_PROJECT")

# Edit suite.xml to use the proper coverage paths
phpunit-suite-edit "$MW_INSTALL_PATH/tests/phpunit/suite.xml" --cover-skin "$SKIN_NAME"

mkdir -p "$WORKSPACE"/cover
find "$WORKSPACE"/cover -mindepth 1 -delete

function relay_signals() {
    for signal ; do
        trap 'kill -$signal $cover_pid; wait $cover_pid' "$signal"
    done
}

# Some tests might fail, we still want to be able to publish the coverage
# report for those that passed.
set +e
if [[ ! -v CODEHEALTH ]]; then
    php -d extension=pcov.so -d pcov.enabled=1 -d pcov.directory="$MW_INSTALL_PATH/skins/$SKIN_NAME" -d pcov.exclude='@(tests|vendor)@' \
        "$MW_INSTALL_PATH"/tests/phpunit/phpunit.php \
        --testsuite skins \
        --coverage-clover "$LOG_DIR"/clover.xml \
        --coverage-html "$WORKSPACE"/cover \
        --log-junit "$LOG_DIR"/junit.xml \
        "$MW_INSTALL_PATH/skins/$SKIN_NAME" &
else
    # This runs unit tests for all skins in the file system. We are doing this because:
    # 1. in the CODEHEALTH env context only the skin we care about should be cloned
    # 2. the phpunit-suite-edit ensures that coverage reports will only be for our skin
    # 3. the unit tests take just a few seconds to run
    # 4. Passing in the tests/phpunit/unit directory when it doesn't exist results in exit
    #    code 1.
    php -d extension=pcov.so -d pcov.enabled=1 -d pcov.directory="$MW_INSTALL_PATH/skins/$SKIN_NAME" -d pcov.exclude='@(tests|vendor)@' \
        vendor/bin/phpunit \
        --testsuite skins:unit \
        --exclude-group Dump,Broken,ParserFuzz,Stub \
        --coverage-clover "$LOG_DIR"/clover.xml \
        --log-junit "$LOG_DIR"/junit.xml &
fi
cover_pid=$!
relay_signals SIGINT SIGTERM
wait "$cover_pid"
set -e

if [ -f "$LOG_DIR/junit.xml" ]; then
    phpunit-junit-edit "$LOG_DIR/junit.xml"
fi

# If we're not operating the in the codehealth pipeline context, check to see
# if the HTML coverage report was generated. If it was not, exit with a failure.
if [[ ! -v CODEHEALTH ]]; then
    test -f "$WORKSPACE"/cover/index.html
fi

if [ -s "$LOG_DIR"/clover.xml ]; then
    cp "$LOG_DIR"/clover.xml "$WORKSPACE"/cover/clover.xml
fi
