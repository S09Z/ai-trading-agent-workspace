#!/bin/sh
set -e

if [ "${APP_ENV}" = "production" ]; then
    # Replace ${DOMAIN} only — leave nginx variables ($host, $scheme, etc.) untouched
    envsubst '${DOMAIN}' < /etc/nginx/templates/nginx-ssl.conf > /etc/nginx/conf.d/default.conf
else
    cp /etc/nginx/templates/nginx.conf /etc/nginx/conf.d/default.conf
fi

exec nginx -g "daemon off;"
