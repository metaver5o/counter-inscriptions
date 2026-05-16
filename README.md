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
│  - All 70+ MIME types           │
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

| Category | Examples |
|----------|---------|
| Images | `image/png`, `image/jpeg`, `image/webp`, `image/avif`, `image/svg+xml` |
| Audio | `audio/mpeg`, `audio/ogg;codecs=opus`, `audio/flac`, `audio/wav` |
| Video | `video/mp4`, `video/webm`, `video/ogg`, `video/quicktime` |
| Text | `text/plain`, `text/html`, `text/markdown`, `text/javascript` |
| App | `application/json`, `application/pdf`, `application/wasm` |
| 3D | `model/gltf+json`, `model/gltf-binary`, `model/stl` |

---

## Fixes Applied (vs original codebase)

### Backend (`backend/index.js`)
- **FIXED**: `mint-collection` and `mint-any-wallet` were sending raw description string instead of building proper form body with hex encoding
- **FIXED**: `COUNTERPARTY_URL` defaulted to `localhost:4000` which doesn't resolve inside Docker — now correctly defaults to `counterparty-server:4000`
- **NEW**: Auto-chunking: files >350KB are split into multiple issuances automatically
- **NEW**: `/api/upload` pre-flight endpoint for MIME detection and chunk count analysis
- **NEW**: `/api/mime-types` endpoint listing all supported types
- **NEW**: `destinationWallet` field actually used when minting (was collected but ignored)
- **NEW**: `mime-types` npm package for reliable server-side MIME detection

### Frontend (`frontend/src/App.js`)
- **FIXED**: `destinationWallet` state was set but `address` (connected wallet) was always used instead
- **FIXED**: `unisat.sendBitcoin(rawHex)` is wrong for unsigned txs — now uses `signPsbt` + `pushTx`
- **FIXED**: Xverse signing now uses `signPsbt` with `broadcast: true`
- **NEW**: Testnet/Mainnet network toggle (switches UniSat network too)
- **NEW**: File pre-flight shows chunk count before minting
- **NEW**: Progress bar during mint
- **NEW**: Collapsible MIME type reference grid
- **NEW**: Per-chunk transaction results with TXID links to mempool.space

### Docker (`docker-compose.yml`)
- **FIXED**: Backend `COUNTERPARTY_URL` was `http://localhost:4000` — containers can't reach each other via localhost; fixed to `http://counterparty-server:4000`
- **NEW**: Cloudflare tunnel service (two profiles: `tunnel` for persistent, `quicktunnel` for temporary)
- **NEW**: Health check on counterparty-server before backend starts

### Patch (`xcp-api-mime/patch_mime.py`)
- **EXTENDED**: Was only registering ~8 audio/video types — now registers **70+ MIME types** across images, audio, video, text, application, fonts, and 3D models
- **NEW**: Registers `model/gltf+json`, `model/gltf-binary`, `model/stl`, `font/woff2`, `image/avif`, `application/wasm`, 40+ more

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
