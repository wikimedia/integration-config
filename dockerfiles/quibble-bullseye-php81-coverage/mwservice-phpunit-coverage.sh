#!/bin/bash
#
# Generate coverage for a MediaWiki service
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

SERVICE_NAME=$(basename "$ZUUL_PROJECT")

# Edit suite.xml to use the proper coverage paths
phpunit-suite-edit "$MW_INSTALL_PATH/tests/phpunit/suite.xml" --cover-service "$SERVICE_NAME"

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
php -d extension=pcov.so -d pcov.enabled=1 -d pcov.directory="$MW_INSTALL_PATH/services/$SERVICE_NAME" -d pcov.exclude='@(tests|vendor)@' \
    "$MW_INSTALL_PATH/services/$SERVICE_NAME/vendor/bin/phpunit" \
    --coverage-clover "$LOG_DIR"/clover.xml \
    --coverage-html "$WORKSPACE"/cover \
    --log-junit "$LOG_DIR"/junit.xml &
cover_pid=$!
relay_signals SIGINT SIGTERM
wait "$cover_pid"
set -e

if [ -f "$LOG_DIR/junit.xml" ]; then
    phpunit-junit-edit "$LOG_DIR/junit.xml"
fi

# Check to see if the HTML coverage report was generated. If it was not, exit
# with a failure.
test -f "$WORKSPACE"/cover/index.html

if [ -s "$LOG_DIR"/clover.xml ]; then
    cp "$LOG_DIR"/clover.xml "$WORKSPACE"/cover/clover.xml
fi
