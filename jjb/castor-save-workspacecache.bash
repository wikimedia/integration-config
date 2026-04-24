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

echo "Creating directory holding cache:"
mkdir -v -p "${DEST}"

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
    jenkins-deploy@"${REMOTE_INSTANCE}:${cache_dir}/" "${DEST}"

echo -e "\nDone"
