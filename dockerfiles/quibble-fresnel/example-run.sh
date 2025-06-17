#!/bin/bash

install --mode 777 --directory log

docker run --rm --entrypoint /usr/local/bin/fresnel \
    docker-registry.wikimedia.org/releng/quibble-fresnel:latest \
    version

# Based on https://integration.wikimedia.org/ci/job/mediawiki-fresnel-patch-docker/
docker run \
    --env JENKINS_URL=1 \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r \
    --env ZUUL_PROJECT=mediawiki/core \
    --env ZUUL_COMMIT=master \
    --env ZUUL_REF=master \
    --volume /"$PWD"/log:/workspace/log \
    --rm \
    docker-registry.wikimedia.org/releng/quibble-fresnel:latest \
    --packages-source vendor --db mysql --db-dir /workspace/db --skip-deps --commands mediawiki-fresnel-patch
