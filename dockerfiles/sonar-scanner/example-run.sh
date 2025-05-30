#!/bin/bash

docker run \
    --rm --tty \
    --env ZUUL_URL=https://gerrit.wikimedia.org/r/p \
    --env ZUUL_PROJECT=mediawiki/extensions/GrowthExperiments \
    --env ZUUL_COMMIT=master \
    --env ZUUL_REF=master \
    --env SONAR_API_KEY=yourkey \
    --volume /"$PWD"://src \
    docker-registry.wikimedia.org/releng/sonar-scanner \
        -Dsonar.host.url=https://sonarcloud.io
