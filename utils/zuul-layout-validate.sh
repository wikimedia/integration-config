#!/usr/bin/env bash
#
# Asks Zuul server to validate its layout with the list of Jenkins jobs
# deployed. This is intended to be used before merge to ensure that all
# jobs referenced have been deployed.
#
# When run outside of a tox virtualenv, the script would install the
# zuul_tests environment and uses the zuul-server command it provides.
#

set -eu
set -o pipefail

_dir="$(dirname "$0")"
repodir="$(realpath "$_dir/..")"

jobslist=$(mktemp --tmpdir zuul-layout-validate_jobslist.XXXX)
trap 'rm "$jobslist"' EXIT

if [ -v CI ]; then
    echo "CI> Creating jenkins_jobs.ini"
    cat > "$repodir"/jenkins_jobs.ini << EOF
[jenkins]
query_plugins_info = False
url = https://integration.wikimedia.org/ci/
EOF
fi

echo "Getting list of jobs from Jenkins."
"$repodir"/jjb-list > "$jobslist"
echo "There are $(wc -l "$jobslist"|cut -d\  -f1) jobs defined."

# shellcheck source=/dev/null
source "$_dir"/setup-zuul-server.inc.sh

"$ZUUL_SERVER_BIN" --version
"$ZUUL_SERVER_BIN" \
    -c "$repodir"/tests/fixtures/zuul-dummy.conf \
    -t "$jobslist" \
    -l "$repodir"/zuul/layout.yaml 2>&1|(grep -E -v '^(DEBUG|INFO):zuul' || :)
# note grep status is ignored, we don't care wether we had a match or not.
