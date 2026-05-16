#!/bin/sh
# Custom entrypoint: reads env vars and passes them as CLI flags to counterparty-server

# Build backend connection string from environment variables
# Supports both BITCOIN_RPC_* (preferred) and BACKEND_* (legacy) formats
BACKEND_CONNECT=""
BACKEND_PORT=""
BACKEND_USER=""
BACKEND_PASSWORD=""

# Only set backend-connect if a non-localhost host is provided (requires actual Bitcoin Core node)
[ -n "$BITCOIN_RPC_HOST" ] && [ "$BITCOIN_RPC_HOST" != "localhost" ] && BACKEND_CONNECT="$BITCOIN_RPC_HOST"
[ -z "$BACKEND_CONNECT" ] && [ -n "$BACKEND_HOST" ] && BACKEND_CONNECT="$BACKEND_HOST"

# Port (optional)
[ -n "$BITCOIN_RPC_PORT" ] && BACKEND_PORT=":$BITCOIN_RPC_PORT"
[ -z "$BACKEND_PORT" ] && [ -n "$BACKEND_PORT" ] && BACKEND_PORT=$BACKEND_PORT
[ -z "$BACKEND_CONNECT" ] && [ -n "$BACKEND_PORT" ] && BACKEND_CONNECT="http://localhost$BACKEND_PORT"

# Username (optional)
[ -n "$BITCOIN_RPC_USER" ] && BACKEND_USER="$BITCOIN_RPC_USER"
[ -z "$BACKEND_USER" ] && [ -n "$BACKEND_USER" ] && BACKEND_USER=$BACKEND_USER

# Password (optional)
[ -n "$BITCOIN_RPC_PASSWORD" ] && BACKEND_PASSWORD="$BITCOIN_RPC_PASSWORD"
[ -z "$BACKEND_PASSWORD" ] && [ -n "$BACKEND_PASSWORD" ] && BACKEND_PASSWORD=$BACKEND_PASSWORD

# SSL options (optional)
[ "$BACKEND_SSL" = "1" ] || [ -n "$BACKEND_SSL" ] && ARGS="$ARGS --backend-ssl"
[ "$BACKEND_SSL_NO_VERIFY" = "1" ] && ARGS="$ARGS --backend-ssl-no-verify"

# Build CLI args from environment variables (minimal args without backend by default)
ARGS="start --api-host=0.0.0.0 --api-port=4000 --rpc-host=0.0.0.0"

[ -n "$BACKEND_CONNECT" ]        && ARGS="$ARGS --backend-connect=$BACKEND_CONNECT"
[ -n "$BACKEND_PORT" ]           && ARGS="$ARGS --backend-port=$BACKEND_PORT"
[ -n "$BACKEND_USER" ]           && ARGS="$ARGS --backend-user=$BACKEND_USER"
[ -n "$BACKEND_PASSWORD" ]       && ARGS="$ARGS --backend-password=$BACKEND_PASSWORD"
[ "$FORCE" = "1" ]               && ARGS="$ARGS --force"
[ "$ENABLE_ALL_PROTOCOL_CHANGES" = "1" ] && ARGS="$ARGS --enable-all-protocol-changes"

if [ "$1" = "start" ] || [ $# -eq 0 ]; then
    echo "Starting: counterparty-server $ARGS"
    exec /venv/bin/counterparty-server $ARGS
else
    echo "Starting custom command: counterparty-server $@"
    exec /venv/bin/counterparty-server "$@"
fi
