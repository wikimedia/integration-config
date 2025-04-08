#!/bin/bash

set -euxo pipefail

RAKE_TARGET=${RAKE_TARGET:-test}
RAKE_PID=""

LOG_DIR="/srv/workspace/log"
export LOG_DIR

capture_logs() {
    # Save logs
    mv --backup=t "${PUPPET_DIR}"/.tox/*/log/*.log "${LOG_DIR}/" || /bin/true
    mv --backup=t "${PUPPET_DIR}"/.tox/log/* "${LOG_DIR}/" || /bin/true
}

kill_rake() {
    if [ "$RAKE_PID" != "" ]; then
        kill -SIGTERM "$RAKE_PID"
    fi
}

execute() {
    # To force color output on non tty
    export TOX_TESTENV_PASSENV='PY_COLORS'
    export PY_COLORS=1
    export SPEC_OPTS='--tty'

    # Run tests, allow trapping signals
    bundle exec rake "${RAKE_TARGET}" "$@" &
    RAKE_PID=$!
    trap kill_rake SIGINT SIGTERM SIGHUP
    wait "$RAKE_PID"
}

execute_ci() {
    trap capture_logs EXIT
    cd "$PUPPET_DIR"
    # Prepare patch set from zuul merger
    git remote add zuul "${ZUUL_URL}/${ZUUL_PROJECT}"
    git pull --quiet zuul production
    git fetch --quiet zuul "$ZUUL_REF"
    git checkout --quiet FETCH_HEAD
    local docker_head
    docker_head=$(git show-ref -s docker-head)
    bundle_update "$docker_head"
    execute | tee "${LOG_DIR}/rake.log"
}

execute_local() {
    set +x
    cd "$PUPPET_DIR"
    bundle_update "$CONT_DOCKER_HEAD"
    execute -j 1
}

# If there is a diff between the supplied git ref and the repo's Gemfile, run
# bundler update
bundle_update() {
    local docker_head=$1
    # Update bundle if gemfile changed
    if git diff --name-only "$docker_head" Gemfile | grep -q 'Gemfile'; then
        bundle update
    fi
}

if [ -n "$ZUUL_REF" ]; then
    execute_ci
else
    # Local copy. Output to stdout and don't capture logs
    execute_local
fi
