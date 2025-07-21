#!/usr/bin/env bash

set -euxo pipefail

SOURCE_ROOT=/mediawiki
if [ "${GITLAB_CI:-}" ]; then
    SOURCE_ROOT=/src
fi

/run-phan-generic.sh "$SOURCE_ROOT/$THING_SUBNAME" "$@"
