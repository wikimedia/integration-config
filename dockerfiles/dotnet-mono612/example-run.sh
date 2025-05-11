#!/bin/bash

set -eux -o pipefail

mkdir -m 2777 -p log src cache
(
cd src
git init
git fetch --quiet --depth 1 "https://gerrit.wikimedia.org/r/labs/countervandalism/CVNBot"
git checkout FETCH_HEAD
)

docker run \
    --rm --tty \
    --volume "/$PWD/cache:/cache" \
    --volume "/$PWD/log:/log" \
    --volume "/$PWD/src:/src" \
    --entrypoint /usr/bin/msbuild \
    docker-registry.wikimedia.org/releng/dotnet-mono612:latest \
    src/CVNBot.sln /p:Configuration=Debug
