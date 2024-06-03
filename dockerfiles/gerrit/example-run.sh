#!/bin/bash

set -eux -o pipefail

mkdir -m 2777 -p log
mkdir -m 2777 -p src
mkdir -m 2777 -p cache

GERRIT_WMF_BRANCH=wmf/stable-3.8

# Clone Gerrit without submodules
docker run \
    --rm --tty \
    --env CI=1 \
    --env GIT_NO_SUBMODULES=1 \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=operations/software/gerrit \
    --env ZUUL_BRANCH=$GERRIT_WMF_BRANCH \
    --env ZUUL_REF=$GERRIT_WMF_BRANCH \
    --volume "/$(pwd)/src://src" \
        docker-registry.wikimedia.org/releng/ci-src-setup-simple:latest

docker run \
    --rm --tty \
    --volume /"$(pwd)"/log://log \
    --volume /"$(pwd)"/cache://cache \
    --volume /"$(pwd)"/src://src \
    --entrypoint=/src/wmf-build.py \
    docker-registry.wikimedia.org/releng/gerrit:latest
