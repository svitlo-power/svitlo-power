#!/bin/sh
set -eu

envsubst '${VERSION}' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

case "${DISABLE_PUBLIC_FRONTEND:-false}" in
  true|false) disable_public_frontend="${DISABLE_PUBLIC_FRONTEND:-false}" ;;
  *)
    echo "DISABLE_PUBLIC_FRONTEND must be true or false" >&2
    exit 1
    ;;
esac

printf 'globalThis.__SVITLO_CONFIG__ = {"disablePublicFrontend": %s};\n' \
  "$disable_public_frontend" \
  > /var/www/front-end/runtime-config.js
