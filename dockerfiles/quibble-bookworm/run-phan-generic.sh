#!/usr/bin/env bash

set -euxo pipefail

umask 002

SOURCE_ROOT="$1"
shift

cd "$SOURCE_ROOT"

# Bypass expensive Symfony\Component\Console\Terminal::getWidth() (T219114#5084302)
export COLUMNS=80

if [ ! -f ".phan/config.php" ]; then
    echo ".phan/config.php not found, skipping"
    exit 0
fi

exec vendor/bin/phan -d . --long-progress-bar "$@" --require-config-exists
