#!/bin/bash

set -eux -o pipefail

mkdir -m 2777 -p src

docker run \
    --rm --tty \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=integration/pipelinelib \
    --env ZUUL_COMMIT=master \
    --env ZUUL_REF=master \
    --volume "/$PWD/src://src" \
        docker-registry.wikimedia.org/releng/ci-src-setup-simple:latest

docker run \
    --rm --tty \
    --workdir=/src \
    --volume /"$PWD"/src://src \
    docker-registry.wikimedia.org/releng/gradle:latest \
    groovydoc
