#!/bin/bash
set -euxo pipefail

if [ ! -d /src/wikimedia/fundraising/crm ]; then
    echo "Civi CRM not found at /src/wikimedia/fundraising/crm"
    echo "You must first clone the git repositories and volume mount"
    echo "them to /src."
    exit 1
fi

/src/wikimedia/fundraising/crm/bin/ci-create-dbs.sh

MYSQL_SOCKET=/var/run/mysqld/mysqld.sock

mysqld="/usr/sbin/mysqld
    --verbose
    --datadir=/tmp/mysqld/datadir
    --log-error=/tmp/mysqld/error.log
    --pid-file=/tmp/mysqld/mysqld.pid
    --socket=${MYSQL_SOCKET}"
$mysqld &

function terminate_mysql() {
    kill "$(pidof mysqld)"
}
trap terminate_mysql SIGINT
trap terminate_mysql SIGTERM
trap terminate_mysql EXIT

while [ "$(pidof mysqld)" ] && [ ! -e "$MYSQL_SOCKET" ]; do
    echo "Waiting for $MYSQL_SOCKET"
    sleep 1
done;

/run.sh "${@}" &

run_pid=$!
wait $run_pid
