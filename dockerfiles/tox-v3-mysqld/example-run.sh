#!/bin/bash

install --mode 777 --directory log cache src

# CI is set for wikimedia/fundraising/tools test suite
docker run \
    --rm --tty \
    --env CI=1 \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=labs/tools/wikinity \
    --env ZUUL_COMMIT=master \
    --env ZUUL_REF=master \
    --volume /"$PWD"/src://src \
    --volume /"$PWD"/log://log \
    --volume /"$PWD"/cache://cache \
    docker-registry.wikimedia.org/releng/tox-v3-mysqld:latest
