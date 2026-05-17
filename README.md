# Counter-Inscriptions

Mint **any MIME type** as Ordinals via the Counterparty protocol.  
Taproot inscriptions · UniSat + Xverse wallet support · Batch / airdrop minting · Auto-chunking for large files.

---

## Architecture

```
┌─────────────────────────────────────┐
│  Browser (port 3000)                │
│  React SPA — nginx-served           │
│  - UniSat / Xverse wallet connect   │
│  - Single mint + Batch/airdrop UI   │
│  - Testnet / Mainnet toggle         │
│  - File pre-flight + chunk preview  │
│  - Progress bar + TXID results      │
└──────────────┬──────────────────────┘
               │ /api/* proxied by nginx → backend:3001
┌──────────────▼──────────────────────┐
│  Backend API (port 3001)            │
│  Node.js / Express                  │
│  - POST /api/mint        (single)   │
│  - POST /api/mint-batch  (airdrop)  │
│  - POST /api/upload      (preflight)│
│  - GET  /api/balance/:addr          │
│  - GET  /api/mime-types             │
│  - GET  /api/health                 │
│  - GET  /swagger-ui.html            │
│  Max file: 50MB                     │
│  Chunk size: 350KB binary           │
└──────────────┬──────────────────────┘
               │ HTTP — service DNS: counterparty-server:4000
┌──────────────▼──────────────────────┐
│  Counterparty API (port 4000)       │
│  counterparty-core + patch_mime.py  │
│  - 100+ MIME types registered       │
│  - 50MB body limit                  │
│  - API-only mode (no Bitcoin node)  │
└─────────────────────────────────────┘
```

The nginx config inside the frontend container proxies all `/api/` traffic to `backend:3001`, so the browser only ever talks to one origin (port 3000).

---

## Repository Structure

```
.
├── backend/
│   ├── Dockerfile
│   ├── index.js                  # Express API server
│   ├── openapi-spec.yaml         # OpenAPI 3.0 spec (served at /swagger-ui.html)
│   ├── frontend-build-fallback/
│   │   └── index.html            # Minimal fallback if React build is missing
│   └── package.json
├── config/
│   ├── server.conf               # Active Counterparty config
│   └── server.conf.example       # Template — copy and edit
├── data/                         # Gitignored runtime data
│   ├── counterparty/             # counterparty.db, state.db
│   └── counterparty-cache/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf                # Serves SPA + proxies /api/ to backend
│   ├── src/App.js                # Full React UI
│   └── package.json
├── patch_mime.py                 # Patches counterparty-core MIME registry at build time
├── entrypoint.sh                 # Counterparty startup script (api-only mode)
├── xcp-api-mime-Dockerfile       # Builds the patched Counterparty image
├── docker-compose.yml
└── Makefile
```

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd counterinscriptions
cp config/server.conf.example config/server.conf
# Edit config/server.conf as needed
```

### 2. Start all services

```bash
make          # runs docker compose up --build
# or directly:
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API + Swagger | http://localhost:3001/swagger-ui.html |
| Counterparty API | http://localhost:4000/v2/ |

### 3. Expose publicly (for mobile wallet testing)

```bash
docker compose --profile tunnel up
# URL appears in the container logs:
docker logs counterinscriptions-tunnel
```

---

## Makefile

```bash
make          # docker compose up --build
make down     # docker compose down
make clean    # delete counterparty.db and state.db from data/
make reset    # down + clean + up
```

---

## Minting Flow

### Single Mint (with auto-chunking)

Files larger than **350KB binary** are automatically split into multiple Counterparty
issuances. The frontend signs each chunk sequentially.

```
File → detect MIME → chunk(350KB) → per-chunk POST /api/mint
     → composeIssuance() → sign PSBT in wallet → broadcast
```

Chunks are named `ASSET_1`, `ASSET_2`, etc. Reassembly is handled at the application/viewer layer.

### Batch Mint (airdrop)

One file minted to many destination wallets. File must be **≤350KB** (single chunk).
Use single mint with chunking for larger files.

```
File → hex → loop(wallets) → POST /api/mint-batch
     → unsigned txs returned → sign + broadcast per wallet
```

---

## API Reference

Full interactive docs at `http://localhost:3001/swagger-ui.html`.

### `POST /api/mint`
Single file → one wallet. Accepts `multipart/form-data`.

| Field | Required | Description |
|-------|----------|-------------|
| `file` | yes | File to inscribe (max 50MB) |
| `asset` | yes | Asset name e.g. `MYTOKEN` or `A17...` |
| `walletAddress` | yes | Connected wallet (fee payer) |
| `destinationWallet` | no | Recipient address (defaults to `walletAddress`) |
| `mime_type` | no | Override auto-detected MIME type |
| `sat_per_vbyte` | no | Fee rate (default: `2.01`) |
| `encoding` | no | `taproot` (default) |

Returns chunk-by-chunk transaction data for wallet signing.

### `POST /api/mint-batch`
One file → many wallets. Same fields as `/api/mint` plus:

| Field | Required | Description |
|-------|----------|-------------|
| `destinationWallets` | yes | Comma-separated wallet addresses |

File must be ≤350KB. Returns per-wallet success/failure results.

### `POST /api/upload`
Pre-flight analysis — no minting. Returns MIME type, size, chunk count, and hex preview. Use this before minting to confirm chunk count.

### `GET /api/balance/:address`
Proxies to Counterparty `/v2/addresses/:address/balances`.

### `GET /api/health`
Returns backend status and whether Counterparty is reachable.

### `GET /api/mime-types`
Full list of supported MIME types, max chunk size, and max file size.

---

## Wallet Signing

### UniSat
Uses `signPsbt` on the unsigned PSBT returned by Counterparty, then `pushTx` to broadcast.

### Xverse
Uses `signPsbt` with `broadcast: true` — Xverse handles broadcasting internally.

Both wallets support Testnet/Mainnet toggle from the UI. Switching networks in the UI also switches the active UniSat network.

---

## Supported MIME Types

See `GET /api/mime-types` for the live list. Summary:

| Category | Examples |
|----------|---------|
| Images | `image/png`, `image/jpeg`, `image/webp`, `image/avif`, `image/heic`, `image/jxl`, `image/svg+xml` |
| Audio | `audio/mpeg`, `audio/flac`, `audio/wav`, `audio/ogg;codecs=opus`, `audio/midi`, `audio/x-aiff` |
| Video | `video/mp4`, `video/webm`, `video/quicktime`, `video/x-matroska`, `video/x-msvideo` |
| Text / Code | `text/plain`, `text/html`, `text/markdown`, `text/x-python`, `text/x-rust`, `text/x-solidity`, `text/x-go` |
| App / Data | `application/json`, `application/pdf`, `application/wasm`, `application/epub+zip`, `application/x-sqlite3` |
| Archives | `application/zip`, `application/gzip`, `application/x-7z-compressed` |
| 3D / Model | `model/gltf+json`, `model/gltf-binary`, `model/stl`, `model/obj`, `model/vnd.usdz+zip` |
| Fonts | `font/ttf`, `font/otf`, `font/woff`, `font/woff2` |
| Misc | `application/pgp-signature`, `application/x-chess-pgn`, `chemical/x-mdl-molfile` |

---

## Asset Naming

| Type | Format | Cost |
|------|--------|------|
| Free (numeric) | `A17<timestamp><random>` | 0 XCP |
| Named | `MYTOKEN` (4–12 chars, uppercase) | 0.5 XCP |

Use the **Auto** button in the UI to generate a free numeric asset name.

---

## Local Development (no Docker)

The Counterparty server must still run in Docker. Everything else can run locally.

```bash
# Terminal 1 — Counterparty only
docker compose up counterparty-server

# Terminal 2 — Backend
cd backend
npm install
COUNTERPARTY_URL=http://localhost:4000 node index.js

# Terminal 3 — Frontend
cd frontend
npm install
REACT_APP_API_URL=http://localhost:3001/api npm start
```

---

## Configuration

### `config/server.conf`

Copy from `server.conf.example` and adjust:

```ini
network=counterinscriptions
port=4000
host=0.0.0.0
enable_all_protocol_changes=true
max_message_size=52428800   # 50MB
api_enabled=true
ordinals_enabled=true
```

### Environment variables

| Variable | Service | Default | Description |
|----------|---------|---------|-------------|
| `COUNTERPARTY_URL` | backend | `http://counterparty-server:4000` | Counterparty API endpoint |
| `PORT` | backend | `3001` | Backend listen port |
| `REACT_APP_API_URL` | frontend | `http://localhost:3001/api` | API base URL seen by the browser |
| `FORCE` | counterparty | `0` | Pass `--force` to counterparty-server |
| `ENABLE_ALL_PROTOCOL_CHANGES` | counterparty | `1` | Enable MIME + taproot support |

---

## How `patch_mime.py` Works

At Docker build time, `patch_mime.py` patches the installed `counterparty-core` Python package to:

1. Register 100+ MIME types in the Counterparty MIME registry
2. Increase the API body size limit to 50MB
3. Strip MIME parameters (e.g. `audio/ogg;codecs=opus` → `audio/ogg`) where required

The patched image is built via `xcp-api-mime-Dockerfile` with the repo root as the build context, then used as the `counterparty-server` service in docker-compose.

---

## Limitations

- **Chunk reassembly** is handled at the application layer — viewers must know to combine `ASSET_1` + `ASSET_2` etc.
- **Batch mint** requires files ≤350KB. Use single mint with auto-chunking for larger files.
- **Wallet signing** requires the UniSat or Xverse browser extension.
- **Counterparty runs in api-only mode** — no Bitcoin Core node is required for composing inscriptions.
