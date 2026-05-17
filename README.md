# Counter-Inscriptions

Mint **any MIME type** as Ordinals via the Counterparty protocol.  
Taproot inscriptions · UniSat + Xverse wallet support · Batch / airdrop minting · Auto-chunking for large files.

---

## Architecture

```
┌─────────────────────────────────┐
│  Browser (port 3000)            │
│  React frontend                 │
│  - UniSat / Xverse wallet       │
│  - Single + Batch mint UI       │
│  - Testnet / Mainnet toggle     │
└──────────────┬──────────────────┘
               │ HTTP
┌──────────────▼──────────────────┐
│  Backend API (port 3001)        │
│  Node.js / Express              │
│  - /api/mint         (single)   │
│  - /api/mint-batch   (airdrop)  │
│  - /api/upload       (preflight)│
│  - /api/balance/:addr           │
│  - /api/mime-types              │
│  - /api/health                  │
│  Auto-chunks files >350KB       │
└──────────────┬──────────────────┘
               │ HTTP (service DNS: counterparty-server)
┌──────────────▼──────────────────┐
│  Counterparty API (port 4000)   │
│  counterparty-core (patched)    │
│  patch_mime.py applied:         │
│  - All 100+ MIME types          │
│  - 50MB body limit              │
│  - MIME param stripping         │
└─────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd counterinscriptions
cp .env.example .env   # or edit .env directly
```

### 2. Start all services

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000  
- Backend API: http://localhost:3001  
- Counterparty: http://localhost:4000/v2/

### 3. Expose publicly (for testing with mobile wallets)

**Quick tunnel (no account needed — temporary URL):**
```bash
docker-compose --profile quicktunnel up
# Look for "trycloudflare.com" URL in cloudflared logs
docker logs counterinscriptions-quick-tunnel
```

**Persistent tunnel (Cloudflare account):**
```bash
# 1. Get token at https://dash.cloudflare.com/tunnels
# 2. Set in .env: TUNNEL_TOKEN=your_token_here
docker-compose --profile tunnel up
```

---

## Minting Flow

### Single Mint (with auto-chunking)

Files larger than **350KB** are automatically split into multiple Counterparty
issuances named `ASSET_1`, `ASSET_2`, etc. The frontend handles signing each chunk.

```
File → hex → chunk(350KB) → issuance per chunk → sign in wallet → broadcast
```

### Batch Mint (airdrop)

One file → many destination wallets. Limited to **350KB** (single chunk).
For larger files, use single mint per wallet.

```
File → hex → loop(wallets) → issuance per wallet → unsigned txs returned
```

---

## Supported MIME Types

All common types are registered. See `GET /api/mime-types` for the full list.

### Images

| MIME Type | Notes |
|-----------|-------|
| `image/png` | |
| `image/jpeg` | |
| `image/gif` | |
| `image/webp` | |
| `image/svg+xml` | |
| `image/bmp` | |
| `image/avif` | |
| `image/tiff` | **NEW** |
| `image/heic` | **NEW** |
| `image/jxl` | JPEG XL — **NEW** |
| `image/x-icon` | **NEW** |

### Audio

| MIME Type | Notes |
|-----------|-------|
| `audio/mpeg` | MP3 |
| `audio/ogg` | |
| `audio/ogg;codecs=opus` | |
| `audio/wav` | |
| `audio/flac` | |
| `audio/aac` | |
| `audio/mp4` | |
| `audio/webm` | **NEW** |
| `audio/midi` | **NEW** |
| `audio/x-aiff` | **NEW** |
| `audio/x-m4a` | **NEW** |

### Video

| MIME Type | Notes |
|-----------|-------|
| `video/mp4` | |
| `video/webm` | |
| `video/ogg` | |
| `video/quicktime` | MOV |
| `video/x-matroska` | MKV — **NEW** |
| `video/x-msvideo` | AVI — **NEW** |
| `video/mpeg` | **NEW** |
| `video/3gpp` | **NEW** |
| `video/x-flv` | **NEW** |

### Text / Code

| MIME Type | Notes |
|-----------|-------|
| `text/plain` | |
| `text/html` | |
| `text/css` | |
| `text/javascript` | |
| `text/markdown` | |
| `text/csv` | |
| `text/xml` | **NEW** |
| `text/yaml` | **NEW** |
| `text/x-python` | **NEW** |
| `text/x-rust` | **NEW** |
| `text/x-go` | **NEW** |
| `text/x-solidity` | **NEW** |
| `text/x-sh` | Shell scripts — **NEW** |
| `text/x-lua` | **NEW** |
| `text/x-swift` | **NEW** |
| `text/x-kotlin` | **NEW** |
| `text/x-java` | **NEW** |
| `text/x-ruby` | **NEW** |
| `text/x-php` | **NEW** |
| `text/x-toml` | **NEW** |

### App / Data

| MIME Type | Notes |
|-----------|-------|
| `application/json` | |
| `application/pdf` | |
| `application/wasm` | |
| `application/octet-stream` | Generic binary |
| `application/epub+zip` | **NEW** |
| `application/x-sqlite3` | **NEW** |
| `application/zip` | **NEW** |
| `application/gzip` | **NEW** |
| `application/x-7z-compressed` | **NEW** |
| `application/geo+json` | GeoJSON — **NEW** |
| `application/ld+json` | JSON-LD — **NEW** |
| `application/pgp-signature` | **NEW** |
| `application/vnd.ms-excel` | XLS — **NEW** |
| `application/msword` | DOC — **NEW** |
| `application/x-chess-pgn` | Chess notation — **NEW** |
| `application/vnd.google-earth.kml+xml` | KML — **NEW** |
| `application/x-shockwave-flash` | SWF — **NEW** |
| `chemical/x-mdl-molfile` | Molecular data — **NEW** |

### 3D / Model

| MIME Type | Notes |
|-----------|-------|
| `model/gltf+json` | |
| `model/gltf-binary` | GLB |
| `model/stl` | |
| `model/obj` | **NEW** |
| `model/vrml` | **NEW** |
| `model/vnd.usdz+zip` | USDZ (Apple AR) — **NEW** |
| `application/x-blender` | .blend files — **NEW** |

### Fonts

| MIME Type | Notes |
|-----------|-------|
| `font/ttf` | **NEW** |
| `font/otf` | **NEW** |
| `font/woff` | **NEW** |
| `font/woff2` | **NEW** |

---

## Features

### Backend (`backend/index.js`)
- Correct hex-encoded form body construction for `mint-collection` and `mint-any-wallet`
- Proper Docker service DNS resolution via `counterparty-server:4000`
- Auto-chunking: files >350KB are split into multiple issuances automatically
- `/api/upload` pre-flight endpoint for MIME detection and chunk count analysis
- `/api/mime-types` endpoint listing all supported types
- `destinationWallet` routing — mints go to the intended recipient address
- Server-side MIME detection via the `mime-types` npm package

### Frontend (`frontend/src/App.js`)
- Correct destination wallet used when minting (not always the connected address)
- Proper unsigned tx signing via `signPsbt` + `pushTx` for UniSat
- Xverse signing via `signPsbt` with `broadcast: true`
- Testnet/Mainnet network toggle (switches UniSat network automatically)
- File pre-flight showing chunk count before minting begins
- Progress bar during multi-chunk mint
- Collapsible MIME type reference grid
- Per-chunk transaction results with TXID links to mempool.space

### Docker (`docker-compose.yml`)
- Correct inter-container networking via `http://counterparty-server:4000`
- Cloudflare tunnel service (two profiles: `tunnel` for persistent, `quicktunnel` for temporary)
- Health check on counterparty-server before backend starts

### MIME Patch (`xcp-api-mime/patch_mime.py`)
- **100+ MIME types** registered across images, audio, video, text, application, fonts, and 3D models
- Extended image support: `image/tiff`, `image/heic`, `image/jxl`, `image/x-icon`
- Extended audio: `audio/webm`, `audio/midi`, `audio/x-aiff`, `audio/x-m4a`
- Extended video: `video/x-matroska`, `video/x-msvideo`, `video/mpeg`, `video/3gpp`, `video/x-flv`
- Source code types: `text/x-python`, `text/x-rust`, `text/x-go`, `text/x-solidity`, `text/x-lua`, `text/x-swift`, `text/x-kotlin`, `text/x-java`, `text/x-ruby`, `text/x-php`, `text/x-toml`, `text/x-sh`
- Data/archive formats: `application/epub+zip`, `application/x-sqlite3`, `application/zip`, `application/gzip`, `application/x-7z-compressed`, `application/geo+json`, `application/ld+json`
- Document/misc: `application/pgp-signature`, `application/vnd.ms-excel`, `application/msword`, `application/x-chess-pgn`, `application/vnd.google-earth.kml+xml`, `application/x-shockwave-flash`, `chemical/x-mdl-molfile`
- 3D formats: `model/obj`, `model/vrml`, `model/vnd.usdz+zip`, `application/x-blender`
- Font formats: `font/ttf`, `font/otf`, `font/woff`, `font/woff2`

---

## Local Development (no Docker)

```bash
# Terminal 1: Backend
cd backend
npm install
COUNTERPARTY_URL=http://localhost:4000 node index.js

# Terminal 2: Frontend
cd frontend
npm install
REACT_APP_API_URL=http://localhost:3001/api npm start
```

The Counterparty server still needs to run in Docker:
```bash
docker-compose up counterparty-server
```

---

## Asset Naming

| Type | Format | Cost |
|------|--------|------|
| Free (numeric) | `A96XXXXXXXXX` | 0 XCP |
| Named | `MYTOKEN` (4-12 chars, uppercase) | 0.5 XCP |

Use the **Auto** button in the UI to generate a free numeric asset name.

---

## Limitations

- Counterparty chunking reassembly (multi-chunk files) is handled at the application layer. The inscription viewer must know to combine chunks `ASSET_1` + `ASSET_2` etc.
- Batch mint requires files ≤350KB (one chunk). Large files need single mint with chunking.
- Wallet signing requires UniSat or Xverse browser extension.
