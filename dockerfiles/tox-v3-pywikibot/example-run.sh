#!/bin/bash

install --mode 777 --directory log cache

docker run \
    --rm --tty \
    --env JENKINS_URL=1 \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=pywikibot/core \
    --env ZUUL_COMMIT=master \
    --env ZUUL_REF=master \
    --volume /"$PWD"/log://log \
    --volume /"$PWD"/cache://cache \
    docker-registry.wikimedia.org/releng/tox-pywikibot:latest -e fasttest-py39
