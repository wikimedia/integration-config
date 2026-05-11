#!/usr/bin/env bash

set -euxo pipefail

umask 002

cd src/
pie --version
PACKAGE=$(php -r "echo json_decode(file_get_contents('composer.json'))->name;")
if [[ -z "$PACKAGE" ]]; then
    echo "Error: could not read package name from composer.json" >&2
    exit 1
fi
pie --no-interaction repository:add path .
pie build --no-interaction "${PACKAGE}:*@dev" \
    --with-php-config /usr/bin/php-config8.4 \
    --with-phpize-path /usr/bin/phpize8.4
