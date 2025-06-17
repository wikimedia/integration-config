#!/bin/bash

set -eux -o pipefail

mkdir -m 2777 -p src
mkdir -m 2777 -p cache

docker run \
    --rm --tty \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=operations/software/ecs \
    --env ZUUL_BRANCH=master \
    --env ZUUL_REF=master \
    --volume "/$PWD/src://src" \
        docker-registry.wikimedia.org/releng/ci-src-setup-simple:latest

docker run \
    --rm --tty \
    --volume /"$PWD"/cache://cache \
    --volume /"$PWD"/src://src \
    --entrypoint=make \
    docker-registry.wikimedia.org/releng/ecs:latest
