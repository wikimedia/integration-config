# castor-load
# Load cache from central repository
set -u

[[ $JOB_NAME == *'docker'* ]] && is_docker=1 || is_docker=''

if [ "$is_docker" ]; then
    # For containers we mount $WORKSPACE/cache from the host to /cache in the
    # container. It is also the value of XDG_CACHE_HOME
    DEST="/cache"
    # cache might persist between builds on the Docker agents
    rsync_delete='--delete-delay'
else
    DEST="$HOME"
    # On Nodepool it is guaranteed to be empty. Deleting would wipe
    # /home/jenkins/workspace!
fi

CASTOR_HOST="${CASTOR_HOST:-integration-castor03.integration.eqiad.wmflabs}"

echo "Syncing..."
rsync \
    --archive \
    ${rsync_delete:-} \
    --delay-updates \
    --contimeout 3 \
    rsync://"$CASTOR_HOST":/caches/"$CASTOR_NAMESPACE"/ "$DEST" \
    || :
echo -e "\nDone"
