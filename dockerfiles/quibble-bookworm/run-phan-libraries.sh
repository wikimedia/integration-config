#!/usr/bin/env bash

set -euxo pipefail

/run-phan-generic.sh "/src" "$@"
