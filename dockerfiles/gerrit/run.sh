#!/usr/bin/env bash

umask 002

set -euxo pipefail

cd /src

bazelisk version

# Setting home dir for Gerrit tools/download_file.py which uses ~ for caching
# downloaded artifacts
export GERRIT_CACHE_HOME="$XDG_CACHE_HOME"/gerrit

bazelisk info
bazelisk build --action_env=GERRIT_CACHE_HOME "${@:-release}"
