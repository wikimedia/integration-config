set -eu +x

if [ "$ZUUL_PIPELINE" != 'gate-and-submit' ] && [ "$ZUUL_PIPELINE" != 'postmerge' ]; then
    echo "Only saving cache for gate-and-submit or postmerge pipelines"
    exit 0
fi

SSH_OPTS=(
    "-a" # Disable agent forwarding
    "-T" # Disable pseudo-tty allocation
    "-o" "ConnectTimeout=6"
    "-o" "UserKnownHostsFile=/dev/null"
    "-o" "StrictHostKeyChecking=no"
)

# shellcheck disable=SC2206
ssh_config=($TRIGGERED_SSH_CONNECTION)
REMOTE_INSTANCE="${ssh_config[2]}"

cache_dir='/cache'
remote_cache_dir="${TRIGGERED_WORKSPACE}${cache_dir}"

if /usr/bin/ssh "${SSH_OPTS[@]}" jenkins-deploy@"${REMOTE_INSTANCE}" -- test -d "${remote_cache_dir}" &>/dev/null; then
    echo "Remote cache '${REMOTE_INSTANCE}:${remote_cache_dir}' directory exists"
else
    if (( $? == 1 )); then
        echo "Remote cache directory does not exist (T282893#10165729)"
        exit 0
    else
        echo "Remote cache directory check failed"
        exit 0
    fi
fi

# Destination in the central cache
DEST="/srv/castor/${CASTOR_NAMESPACE}"

# Generation guard against interleaved saves (T295351).
#
# You may only save to the exact cache you previously loaded. Concurrent
# builds each load the same central cache, then each save it back; rsync's
# size+mtime quick check can leave index and content files from different builds
# mixed together, corrupting the npm cacache. So we bump a "generation" counter
# on every save and only save if the generation we loaded still matches the
# central one. A mismatch means another build has already saved over the cache
# we loaded, so we skip (first finisher wins).
#
# Read-then-rsync is safe only because saves run serially on this job's single
# executor. Do NOT add executors (or parallelise saves) without adding
# per-namespace locking here.
GEN_FILE=".castor-generation"
central_gen=$(cat "${DEST}/${GEN_FILE}" 2>/dev/null || true)
if [ -n "${central_gen}" ]; then
    agent_gen=$(/usr/bin/ssh "${SSH_OPTS[@]}" jenkins-deploy@"${REMOTE_INSTANCE}" -- \
        cat "${remote_cache_dir}/${GEN_FILE}" 2>/dev/null || true)
    if [ "${agent_gen}" != "${central_gen}" ]; then
        echo "Central cache generation changed since this build loaded it;"
        echo "skipping save to avoid mixing caches from concurrent builds (T295351)"
        exit 0
    fi
fi

echo "Creating directory holding cache:"
mkdir -v -p "${DEST}"

# Claim the next generation BEFORE touching the cache content, so the ordering
# is crash-safe. If we bumped afterwards and the job died between the rsync and
# the bump (node going offline, Jenkins restart, OOM, manual abort), the central
# content would already be ours while the generation still matched what our
# siblings loaded -- and a sibling would then rsync over our content and remix
# the caches (the T295351 bug). Bumping first means any interrupted save leaves
# a generation our siblings no longer match, so they skip; a later build that
# loads this generation heals the content with its own full sync.
echo "$(( ${central_gen:-0} + 1 ))" > "${DEST}/${GEN_FILE}"

echo -e "Syncing cache\nFrom.. ${REMOTE_INSTANCE}:${remote_cache_dir}\nTo.... ${DEST}"
set -x
# On the sender, run rsync in a container (--rsync-path) to have it run has
# user 'nobody'.
rsync \
    --archive \
    --rsh="/usr/bin/ssh ${SSH_OPTS[*]}" \
    --rsync-path="docker run --rm -i --volume ${remote_cache_dir}:${cache_dir} --entrypoint=/usr/bin/rsync docker-registry.wikimedia.org/releng/castor:0.4.1" \
    --delete-delay \
    --delay-updates \
    --exclude="/${GEN_FILE}" \
    jenkins-deploy@"${REMOTE_INSTANCE}:${cache_dir}/" "${DEST}"

echo -e "\nDone"
