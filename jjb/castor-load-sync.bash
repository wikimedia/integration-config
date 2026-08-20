# castor-load
# Load cache from central repository
set -u

# For containers we mount $WORKSPACE/cache from the host to /cache in the
# container. It is also the value of XDG_CACHE_HOME
DEST="/cache"
# cache might persist between builds on the Docker agents
rsync_delete='--delete-delay'

CASTOR_HOST="${CASTOR_HOST:-integration-castor05.integration.eqiad.wmflabs}"

echo ">>> Start: castor-load rsync"
start=$(date +%s%3N)
outcome='Finish'
rsync \
    --archive \
    ${rsync_delete:-} \
    --delay-updates \
    --contimeout 3 \
    --stats \
    rsync://"$CASTOR_HOST":/caches/"$CASTOR_NAMESPACE"/ "$DEST" \
    || { echo "castor-load rsync failed (exit code $?); cache is cold"; outcome='Failed'; }
ms=$(( $(date +%s%3N) - start ))
printf '<<< Finish: %s: castor-load rsync, in %d.%03d s\n' "$outcome" "$(( ms / 1000 ))" "$(( ms % 1000 ))"
