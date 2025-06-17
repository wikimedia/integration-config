#!/usr/bin/env bash

set -euxo pipefail

umask 002

cd /src

composer remove --dev --no-update "mediawiki/mediawiki-phan-config"
# Some black magic: add mw-phan in the merge-plugin section
sed -i 's!\(\"include\":\s*\[\)!\1 \"./mediawiki/tools/phan/composer.json\",!' composer.json

# Some blacker magic: re-point phan config in the merge-plugin section
sed -i 's#vendor/mediawiki/mediawiki-phan-config/#mediawiki/tools/phan/#' .phan/config.php

MW_VENDOR_PATH=$PWD
export MW_VENDOR_PATH

export PHP_ARGS='-dextension=ast_101.so'

composer update --ansi --no-progress --prefer-dist --profile

# Bypass expensive Symfony\Component\Console\Terminal::getWidth() (T219114#5084302)
export COLUMNS=80

exec vendor/bin/phan --long-progress-bar --require-config-exists "${@:-}"
