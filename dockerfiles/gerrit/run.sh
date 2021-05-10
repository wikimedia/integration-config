#!/usr/bin/env bash

umask 002

set -euxo pipefail

cd /src

bazelisk version

bazelisk info
bazelisk build "${@:-release}"
