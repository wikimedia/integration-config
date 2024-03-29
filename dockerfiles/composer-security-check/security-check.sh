#!/usr/bin/env bash

umask 002

set -euxo pipefail

cd /src

# If there's no lock file, then generate one
if [ ! -f "composer.lock" ]; then
    composer install --no-progress --prefer-dist --ignore-platform-reqs
fi

curl -i -H "Accept: text/plain" https://php-security-checker.toolforge.org/ -F lock=@composer.lock -o results.check
cat results.check && grep -iF "X-Alerts: 0" results.check
