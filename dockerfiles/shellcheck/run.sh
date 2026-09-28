#!/bin/bash

set -euxo pipefail

if [[ -v CI ]]; then
    shellcheck_opts=('--color=always')
fi

cd /src

# Run against all scripts with a /bin/bash or /bin/sh shebang
git grep -l -E '^#!(/bin/(ba)?sh|/usr/bin/env( -[^ ]+)* /bin/(ba)?sh)' | xargs -exec shellcheck "${shellcheck_opts[@]}"
