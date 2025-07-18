#!/bin/sh

# If we have explicitly enabled Xdebug, don't spam warnings about it
export COMPOSER_DISABLE_XDEBUG_WARN=1

exec /usr/bin/composer "$@"
