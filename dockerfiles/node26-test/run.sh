#!/usr/bin/env bash

umask 002

set -euxo pipefail

set +x
if [ ! -f "package.json" ]; then
    echo "package.json not found, skipping"
    exit 0
fi
set -x

node --version
npm --version

if [ -e 'package-lock.json' ] || [ -e 'npm-shrinkwrap.json' ]; then
    npm ci
else
    # Use whatever version matched in package.json devDependencies
    echo 'No package-lock.json or npm-shrinkwrap.json detected, doing full install'
    rm -rf node_modules
    npm install --no-progress
fi

npm run-script "${@:-test}"
