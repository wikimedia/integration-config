#!/bin/bash

set -euxo pipefail

cd /src

# Run against all scripts with a /bin/bash or /bin/sh shebang
grep -l -RE '#!/bin/(ba)?sh' -- ** | xargs -n1 -exec shellcheck
