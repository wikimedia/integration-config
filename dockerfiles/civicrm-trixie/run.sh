#!/bin/bash

set -eu
set -o pipefail

LOG_DIR=${LOG_DIR:-/log}

if [ ! -d /src/wikimedia/fundraising/crm ]; then
    echo "Civi CRM not found at /src/wikimedia/fundraising/crm"
    echo "You must first clone the git repositories and volume mount"
    echo "them to /src."
    exit 1
fi

set -x
/src/wikimedia/fundraising/crm/bin/ci-populate-dbs.sh
cd /src/wikimedia/fundraising/crm

if [ -x /src/wikimedia/fundraising/crm/bin/ci-run-tests.sh ]; then
    # Runs the tests in parallel with paratest, one copy of the databases per
    # worker. Writes the same junit file - T442953
    /src/wikimedia/fundraising/crm/bin/ci-run-tests.sh
else
    # Branches without the script run the tests one at a time
    export PATH=$PATH:/src/wikimedia/fundraising/crm/civicrm-buildkit/bin
    /src/wikimedia/fundraising/crm/vendor/bin/phpunit --log-junit "${LOG_DIR}/junit-phpunit.xml"
fi
