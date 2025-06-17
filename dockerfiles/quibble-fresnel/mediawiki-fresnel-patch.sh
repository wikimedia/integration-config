#!/bin/bash
#
# Create a Fresnel recording for the before and after state,
# and then print a comparison table in ASCII to stdout.
#
# <https://wikitech.wikimedia.org/wiki/Performance/Fresnel>

set -eux -o pipefail

export FRESNEL_DIR="$LOG_DIR/fresnel_records"

fresnel record "after"

git checkout --quiet HEAD~1

fresnel record "before"

fresnel compare "before" "after"
