#!/bin/bash

set -eux -o pipefail

mkdir -m 777 -p cache
mkdir -m 777 -p log
mkdir -m 777 -p src
(
cd src
git init --quiet
git fetch --quiet --depth 1 "https://gerrit.wikimedia.org/r/utfnormal" "master"
git checkout --quiet FETCH_HEAD
)

mkdir -p log
docker run \
    --rm --tty \
    --volume "/$PWD/cache://cache" \
    --volume "/$PWD/log://var/lib/jenkins/log" \
    --volume "/$PWD/src://src" \
    docker-registry.wikimedia.org/releng/composer-package-php74:latest
