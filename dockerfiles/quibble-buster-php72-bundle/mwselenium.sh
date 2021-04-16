#!/bin/bash

set -eu -o pipefail

EXT_NAME=${EXT_NAME:-}
SKIN_NAME=${SKIN_NAME:-}

if [ "${ZUUL_PROJECT:-}" == 'mediawiki/selenium' ]; then
    # Used for mediawiki/selenium integration job
    tests_dir=mediawiki/selenium
elif [ -z "$EXT_NAME" ] && [ -z "$SKIN_NAME" ]; then
    echo "Neither \$EXT_NAME or \$SKIN_NAME is set"
    if [ -z "${ZUUL_PROJECT:-}" ]; then
        echo "Please set EXT_NAME, SKIN_NAME or ZUUL_PROJECT env variable"
        exit 1
    fi
    repo_path=$(dirname "$ZUUL_PROJECT")
    name=$(basename "$ZUUL_PROJECT")
    kind=$(basename "$repo_path")
    printf "Kind: %s\n" "$kind"
    printf "Name: %s\n" "$name"
elif [ -n "$EXT_NAME" ]; then
    name="$EXT_NAME"
    kind=extensions
elif [ -n "$SKIN_NAME" ]; then
    name="$SKIN_NAME"
    kind=skins
fi

if [ -z "${tests_dir:-}" ]; then
    base_dir="${kind}/${name}"
    printf "Base directory: %s\n" "$base_dir"
    tests_dir="$base_dir/tests/browser"

    if [ -f "$base_dir/tests/browser/LocalSettings.php" ]; then
        echo "Injecting tests/browser/LocalSettings.php"
        echo '?>' >> LocalSettings.php
        cat "$base_dir/tests/browser/LocalSettings.php" >> LocalSettings.php
    fi
fi

printf "Tests directory: %s\n" "$tests_dir"

set -x

# Disable Chromium sandboxing while in Docker
if [ -f '/.dockerenv' ] && [[ ${CHROMIUM_FLAGS:-} != *--no-sandbox* ]]; then
    CHROMIUM_FLAGS="${CHROMIUM_FLAGS:-} --no-sandbox"
    export CHROMIUM_FLAGS
fi

export HEADLESS=${HEADLESS:-true}
# Should get it from DISPLAY=:94
export HEADLESS_DISPLAY=94
export HEADLESS_CAPTURE_PATH="$LOG_DIR"

export MEDIAWIKI_ENVIRONMENT=integration
# Copied from Quibble
export MEDIAWIKI_URL=http://127.0.0.1:9412/index.php/
export MEDIAWIKI_API_URL=http://127.0.0.1:9412/api.php

export SCREENSHOT_FAILURES=true
export SCREENSHOT_FAILURES_PATH="$LOG_DIR"

cd "$tests_dir"

export BUNDLE_DISABLE_SHARED_GEMS=1

bundle install --clean --path "${base_dir:-bundle}"
exec bundle exec cucumber \
    --color \
    --tags @integration \
    --tags ~@skip \
    --format pretty \
    --format junit --out "$LOG_DIR/junit"
