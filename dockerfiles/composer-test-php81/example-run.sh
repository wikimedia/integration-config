#!/bin/bash

set -eux -o pipefail

mkdir -m 2777 -p log src cache
(
cd src
git init --quiet
git fetch --quiet --depth 1 "https://gerrit.wikimedia.org/r/integration/jenkins" "master"
git checkout --quiet FETCH_HEAD
)

docker run \
    --rm --tty \
    --volume "/$PWD/cache:/cache" \
    --volume "/$PWD/log:/log" \
    --volume "/$PWD/src:/src" \
    docker-registry.wikimedia.org/releng/composer-test-php73:latest
