set -eu

# These log files are enabled by mediawiki:includes/DevelopmentSettings.php,
# as included by Quibble's local_settings.php file.
#
# For example:
#
#  $wgDBerrorLog = "$logDir/mw-dberror.log";
#  $wgDebugLogGroups['exception'] = "$logDir/mw-error.log";
#  $wgDebugLogGroups['error'] = "$logDir/mw-error.log";
#

pushd "$WORKSPACE/log"
# Set patterns to expand to a null string when there is no match
shopt -s nullglob
ERROR_FILES=( mw-dberror*.log mw-error*.log )
shopt -u nullglob
popd

echo "Asserting empty files: ${ERROR_FILES[*]}"
if [ ! -v ERROR_FILES ]; then
    echo "No error files created by MediaWiki. GOOD"
    exit 0
fi
echo "Dumping file(s) ${ERROR_FILES[*]}"
set +e
    # Use `grep . file list` to ensure that file names appear next
    # to log messages
    (
        cd "$WORKSPACE/log"
        grep --color=always . "${ERROR_FILES[@]}" 2> /dev/null
    )
set -e
echo -e "MediaWiki emitted some errors. Check output above."
exit 1
