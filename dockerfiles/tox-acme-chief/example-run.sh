#!/bin/bash

mkdir -m 777 -p cache
mkdir -m 777 -p log

docker run \
    --rm --tty \
    --env JENKINS_URL=1 \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=operations/software/acme-chief \
    --env ZUUL_COMMIT=master \
    --env ZUUL_REF=master \
    --volume /"$(pwd)"/log://log \
    --volume /"$(pwd)"/cache://cache \
    docker-registry.wikimedia.org/releng/tox-acme-chief:latest
