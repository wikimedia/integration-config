#!/bin/bash

set -eux -o pipefail

mkdir -m 2777 -p log
mkdir -m 2777 -p src
mkdir -m 2777 -p cache

docker run \
    --rm --tty \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=operations/puppet \
    --env ZUUL_COMMIT=production \
    --env ZUUL_REF=production \
    --volume "/$PWD/src://src" \
        docker-registry.wikimedia.org/releng/ci-src-setup-simple:latest

docker run \
    --rm --tty \
    --volume /"$PWD"/log://log \
    --volume /"$PWD"/cache://cache \
    --volume /"$PWD"/src://src \
    --workdir=/src/modules/profile/files/logstash \
    --entrypoint=make \
    docker-registry.wikimedia.org/releng/logstash-filter-verifier:latest
