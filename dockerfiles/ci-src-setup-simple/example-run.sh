#!/bin/bash

set -euo pipefail

install --mode 777 --directory log
docker run \
    --rm --tty \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=integration/jenkins \
    --env ZUUL_COMMIT=7a4ee7963a15dbdc5d5afb363600d63574bb31a0 \
    --env ZUUL_BRANCH=master \
    --env ZUUL_REF=refs/changes/31/316231/4 \
    --volume "/$PWD/log"://var/lib/jenkins/log \
    docker-registry.wikimedia.org/releng/ci-src-setup-simple:latest
