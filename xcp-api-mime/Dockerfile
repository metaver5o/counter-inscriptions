version: '3.8'

services:

  counterparty-bootstrap:
    image: alpine:3.19
    container_name: counterinscriptions-bootstrap
    profiles: [bootstrap]
    volumes:
      - ./data:/data
    command: >
      sh -c "
        apk add --no-cache zstd &&
        if [ -f /data/counterparty/counterparty.db ]; then
          echo 'DB already extracted, skipping.';
        else
          mkdir -p /data/counterparty &&
          zstd -df /data/counterparty.db.latest.zst -o /data/counterparty/counterparty.db &&
          zstd -df /data/state.db.latest.zst -o /data/counterparty/state.db &&
          echo 'Done.';
        fi
      "

  counterparty-server:
    build:
      context: .
      dockerfile: xcp-api-mime-Dockerfile
    container_name: counterinscriptions-counterparty
    restart: unless-stopped
    platform: linux/amd64
    ports:
      - "4000:4000"
    volumes:
      - ./data/counterparty:/root/.local/share/counterparty
      - ./data/counterparty-cache:/root/.cache/counterparty
      - ./config/server.conf:/root/.config/counterparty/server.conf
    environment:
      - FORCE=${FORCE:-0}
      - ENABLE_ALL_PROTOCOL_CHANGES=${ENABLE_ALL_PROTOCOL_CHANGES:-1}
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:4000/v2/"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 120s

  backend:
    build: ./backend
    container_name: counterinscriptions-backend
    restart: unless-stopped
    ports:
      - "3001:3001"
    depends_on:
      counterparty-server:
        condition: service_healthy
    environment:
      - COUNTERPARTY_URL=http://counterparty-server:4000
      - PORT=3001

  frontend:
    build: ./frontend
    container_name: counterinscriptions-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - REACT_APP_API_URL=http://localhost:3001/api

  cloudflared-quick:
    image: cloudflare/cloudflared:latest
    container_name: counterinscriptions-tunnel-quick
    profiles: [quicktunnel]
    restart: unless-stopped
    command: tunnel --no-autoupdate --url http://frontend:80
    depends_on:
      - frontend

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: counterinscriptions-tunnel
    profiles: [tunnel]
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}
    depends_on:
      - frontend
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN:-}