#!/bin/bash

set -euo pipefail

mkdir -m 777 -p cache log src
(
cd src
git init --quiet
git fetch --quiet --depth 1 https://gerrit.wikimedia.org/r/data-values/value-view
git checkout --quiet FETCH_HEAD
)

docker run \
    --rm --tty \
    --volume /"$PWD"/log://var/lib/jenkins/log \
    --volume /"$PWD"/cache://cache \
    --volume /"$PWD"/log://log \
    --volume /"$PWD"/src://src \
    docker-registry.wikimedia.org/releng/node22-test-browser:latest
