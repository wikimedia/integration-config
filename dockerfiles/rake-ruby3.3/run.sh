#!/bin/bash

set -euxo pipefail

umask 002

/utils/ci-src-setup.sh

bundle config set --local path "${XDG_CACHE_HOME}/bundle"
bundle config set --local clean true
bundle install
exec bundle exec rake "${@:-test}"
