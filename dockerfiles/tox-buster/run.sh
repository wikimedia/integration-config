#!/bin/bash

set -euxo pipefail

umask 002

LOG_DIR=/log
export LOG_DIR

capture_tox_logs() {
    # XXX unlike `mv`, `cp` does not preserve permissions and hence the
    # destination files will inherit the group thanks to log having setgid.
    cp --recursive /src/.tox/*/log/*.log "${LOG_DIR}" || /bin/true
    cp --recursive /src/.tox/log "${LOG_DIR}" || /bin/true
}

/utils/ci-src-setup.sh

trap capture_tox_logs EXIT

function relay_signals() {
    for signal ; do
        trap 'kill -$signal $tox_pid; wait $tox_pid' "$signal"
    done
}

# Run tests.
#
# tox v4 does not pass environment variable beside a built-in list, they have
# to be passed or set via TOX_OVERRIDE.
#
# Pass XDG_CACHE_HOME and set PY_COLORS=1 to force ANSI coloring in some
# software (eg pytest)
#
# tox is backgrounded in bash job control to let bash handles traps (eg
# SIGTERM) immediately. That is merely to capture the testenv log files.
TOX_OVERRIDE=testenv.pass_env=XDG_CACHE_HOME,testenv.set_env=PY_COLORS=1 tox "${@}" &
tox_pid=$!
relay_signals SIGINT SIGTERM
wait "$tox_pid"
