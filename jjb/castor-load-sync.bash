# castor-load
# Load cache from central repository
set -u

# For containers we mount $WORKSPACE/cache from the host to /cache in the
# container. It is also the value of XDG_CACHE_HOME
DEST="/cache"
# cache might persist between builds on the Docker agents
rsync_delete='--delete-delay'

CASTOR_HOST="${CASTOR_HOST:-integration-castor05.integration.eqiad.wmflabs}"

echo "Syncing..."
rsync \
    --archive \
    ${rsync_delete:-} \
    --delay-updates \
    --contimeout 3 \
    rsync://"$CASTOR_HOST":/caches/"$CASTOR_NAMESPACE"/ "$DEST" \
    || :
echo -e "\nDone"
