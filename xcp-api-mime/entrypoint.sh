#!/bin/sh
# Counterparty entrypoint — api-only mode, no Bitcoin Core needed for inscription composing

ARGS="start --api-host=0.0.0.0 --api-port=4000 --rpc-host=0.0.0.0 --api-only"

[ -n "$BACKEND_CONNECT" ]         && ARGS="$ARGS --backend-connect=$BACKEND_CONNECT"
[ -n "$BACKEND_PORT" ]            && ARGS="$ARGS --backend-port=$BACKEND_PORT"
[ -n "$BACKEND_USER" ]            && ARGS="$ARGS --backend-user=$BACKEND_USER"
[ -n "$BACKEND_PASSWORD" ]        && ARGS="$ARGS --backend-password=$BACKEND_PASSWORD"
[ "$BACKEND_SSL" = "1" ]          && ARGS="$ARGS --backend-ssl"
[ "$BACKEND_SSL_NO_VERIFY" = "1" ] && ARGS="$ARGS --backend-ssl-no-verify"
[ "$FORCE" = "1" ]                && ARGS="$ARGS --force"
[ "$ENABLE_ALL_PROTOCOL_CHANGES" = "1" ] && ARGS="$ARGS --enable-all-protocol-changes"

if [ "$1" = "start" ] || [ $# -eq 0 ]; then
    echo "Starting: counterparty-server $ARGS"
    exec /venv/bin/counterparty-server $ARGS
else
    exec /venv/bin/counterparty-server "$@"
fi
