#!/bin/bash

set -eu -o pipefail

# Convenience symlink to make php-fpm.conf version agnostic
ln -s /etc/php/"$PHP_VERSION" /etc/php/current

mv /php-fpm/php-fpm.conf /etc/php/"$PHP_VERSION"/fpm/php-fpm.conf
mv /php-fpm/www.conf /etc/php/"$PHP_VERSION"/fpm/pool.d/www.conf
mv /php-fpm/php.ini /etc/php/"$PHP_VERSION"/fpm/php.ini

rmdir /php-fpm
