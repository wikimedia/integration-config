#!/bin/bash
set -eu -o pipefail

tox -e jenkins-jobs --notest

base_dir=$(realpath "$(dirname "$0")"/../)

JJB_BIN=.tox/jenkins-jobs/bin/jenkins-jobs
JJB_CONF=tests/fixtures/jjb-disable-query-plugins.conf
JJB_TEST="$JJB_BIN --conf $JJB_CONF -l warning test"

test_dir=$(mktemp -d --tmpdir jjbshellcheck.XXXX)
trap 'echo Deleting "$test_dir"; rm -R "$test_dir"' EXIT

mkdir -p "$test_dir"

echo "Generating config for proposed patchset..."
(cd "$base_dir"
 $JJB_BIN --version
 $JJB_TEST ./jjb --config-xml -o "$test_dir")

echo "Extracting shell scripts..."
find "$test_dir" -type f -name \*.xml -exec ./utils/extract-shell-scripts.py '{}' ';'

echo "Running shellcheck..."
# Use xargs, instead of -exec, to propagate shellcheck return code
find "$test_dir" -type f -name \*.sh -print0 | xargs -0 shellcheck --severity=error -W 0