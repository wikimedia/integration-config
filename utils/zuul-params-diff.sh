#!/usr/bin/env bash

set -eu
set -o pipefail

_dir="$(dirname "$0")"
repodir="$(realpath "$_dir/..")"

"$repodir"/utils/zuul-mw-jobs-runner.py --dump > current.txt

previous_env=$(mktemp -d "$repodir"/zuul/zuul-params-diff_XXXX)
trap 'rm -fR "$previous_env"' EXIT

FILES=(zuul/dependencies.yaml zuul/layout.yaml zuul/parameter_functions.py zuul/phan_dependencies.yaml utils/zuul-mw-jobs-runner.py)

# Determine the previous commit to diff against
if [ -n "$(git -C "$repodir" status --porcelain -- "${FILES[@]}")" ]; then
    # When there are changes in the working copy or changes have been staged,
    # compare with the latest commit.
    layout_prev_commit=HEAD
    echo "Zuul config files modified locally, will compare with HEAD"
elif [ -z "$(git -C "$repodir" show --name-only -m --first-parent --format=format: -- "${FILES[@]}")" ]; then
    echo "HEAD does not change Zuul config files. No need for a diff."
    exit 0
else
    # Compare with the previous change that affected zuul/layout.yaml
    layout_prev_commit=$(git -C "$repodir" log --skip=1 -n1 --format='%H' "${FILES[@]}")
    echo "Zuul config files previous commit: $layout_prev_commit"
fi

for file in "${FILES[@]}"; do
    _base_file=$(basename "$file")
    git show "$layout_prev_commit":"$file" > "$previous_env"/"$_base_file"
done

chmod +x "$previous_env"/zuul-mw-jobs-runner.py
"$previous_env"/zuul-mw-jobs-runner.py --dump -- \
    "$previous_env"/layout.yaml \
    "$previous_env"/parameter_functions.py \
    > before.txt

echo "Looking for differences"
diff --color=always -U 0 before.txt current.txt
