const express = require('express');
const axios = require('axios');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const yaml = require('js-yaml');
const mime = require('mime-types');

// ─── Config ──────────────────────────────────────────────────────────────────
// In Docker: counterparty runs at counterparty-server:4000
// Locally:   set COUNTERPARTY_URL=http://localhost:4000
const COUNTERPARTY_URL = process.env.COUNTERPARTY_URL || 'http://counterparty-server:4000';
const MAX_FILE_SIZE_MB = 50;

// Counterparty has ~380KB hex payload limit per issuance description field.
// We chunk at 350KB binary → ~700KB hex (well under limit after URL encoding overhead).
const MAX_CHUNK_BYTES = 350 * 1024;

const app = express();
app.use(cors());
app.use('/api/', express.json({ limit: '100mb' }));

// ─── Multer ───────────────────────────────────────────────────────────────────
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: MAX_FILE_SIZE_MB * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    const baseMime = (file.mimetype || '').split(';')[0].trim();
    if (!baseMime) return cb(new Error('No MIME type detected'), false);
    const ok = ['text/', 'image/', 'audio/', 'video/', 'application/', 'font/', 'model/'].some(p => baseMime.startsWith(p));
    cb(null, ok);
  },
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

function bufToHex(buf) {
  return buf.toString('hex');
}

function chunkBuffer(buf, maxBytes) {
  const chunks = [];
  let offset = 0;
  while (offset < buf.length) {
    chunks.push(buf.slice(offset, offset + maxBytes));
    offset += maxBytes;
  }
  return chunks.length === 0 ? [buf] : chunks;
}

function detectMime(file) {
  const fromName = file.originalname ? mime.lookup(file.originalname) : null;
  const fromMulter = file.mimetype ? file.mimetype.split(';')[0].trim() : null;
  return fromName || fromMulter || 'application/octet-stream';
}

/**
 * POST one issuance to Counterparty exactly as mint_collection.sh does:
 *   asset=...&quantity=1&...&description=<hex>
 * We build the body as a raw Buffer to avoid any re-encoding of the hex payload.
 */
async function composeIssuance({ walletAddress, asset, mimeType, hexData, satPerVbyte = 2.01, encoding = 'taproot', quantity = 1 }) {
  const prefix = [
    `asset=${encodeURIComponent(asset)}`,
    `quantity=${quantity}`,
    `divisible=false`,
    `encoding=${encoding}`,
    `inscription=true`,
    `mime_type=${encodeURIComponent(mimeType)}`,
    `sat_per_vbyte=${satPerVbyte}`,
    `return_psbt=true`,   // return PSBT format so wallets can sign directly
    `description=`,
  ].join('&');

  const body = Buffer.concat([
    Buffer.from(prefix, 'utf8'),
    Buffer.from(hexData, 'utf8'), // hex is pure ASCII — safe
  ]);

  const response = await axios.post(
    `${COUNTERPARTY_URL}/v2/addresses/${walletAddress}/compose/issuance`,
    body,
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
      maxBodyLength: Infinity,
      maxContentLength: Infinity,
      timeout: 180_000,
    }
  );

  const data = response.data;

  // Enrich PSBT with witness UTXO data so wallets (UniSat/Xverse) can sign.
  if (data?.result?.psbt) {
    try {
      data.result.psbt = await enrichPsbt(data.result.psbt);
      // Debug: log full PSBT hex for inspection
      const { Psbt } = require('bitcoinjs-lib');
      const p = Psbt.fromBase64(enriched);
      console.log('[PSBT] Input count:', p.data.inputs.length);
      p.data.inputs.forEach((inp, i) => {
        console.log(`[PSBT] Input ${i}:`, JSON.stringify({
          hasWitnessUtxo: !!inp.witnessUtxo,
          witnessUtxoValue: inp.witnessUtxo?.value,
          witnessUtxoScript: inp.witnessUtxo?.script?.toString('hex'),
          hasTapInternalKey: !!inp.tapInternalKey,
          tapInternalKey: inp.tapInternalKey?.toString('hex'),
          hasNonWitnessUtxo: !!inp.nonWitnessUtxo,
        }));
      });
    } catch (e) {
      console.warn('[PSBT] Could not enrich PSBT:', e.message);
    }
  }

  return data;
}

/**
 * Fetch witness UTXO for each input and inject into the PSBT.
 * Uses mempool.space API to get the previous tx output details.
 */
async function enrichPsbt(psbtBase64) {
  const { Psbt, Transaction } = require('bitcoinjs-lib');

  let psbt;
  try {
    psbt = Psbt.fromBase64(psbtBase64);
  } catch {
    return psbtBase64;
  }

  for (let i = 0; i < psbt.data.inputs.length; i++) {
    const txInput = psbt.txInputs[i];
    if (!txInput) continue;

    const txid = Buffer.from(txInput.hash).reverse().toString('hex');
    const vout = txInput.index;

    try {
      // Fetch the output details directly from mempool UTXO endpoint
      // This gives us the exact scriptpubkey the wallet needs
      const outRes = await axios.get(`https://mempool.space/api/tx/${txid}`, { timeout: 10_000 });
      const txData = outRes.data;
      const output = txData.vout?.[vout];

      if (!output) continue;

      const scriptBuf = Buffer.from(output.scriptpubkey, 'hex');
      const value = output.value;

      console.log(`[PSBT] Input ${i}: ${txid}:${vout} type=${output.scriptpubkey_type} value=${value} script=${output.scriptpubkey}`);

      if (output.scriptpubkey_type === 'v0_p2wpkh' || output.scriptpubkey_type === 'v0_p2wsh') {
        // Native SegWit — use witnessUtxo
        psbt.updateInput(i, { witnessUtxo: { script: scriptBuf, value } });

      } else if (output.scriptpubkey_type === 'p2sh') {
        // P2SH (possibly P2SH-P2WPKH) — need full raw tx as nonWitnessUtxo
        const rawRes = await axios.get(`https://mempool.space/api/tx/${txid}/hex`, { timeout: 10_000 });
        const rawTx = Buffer.from(rawRes.data, 'hex');
        psbt.updateInput(i, { nonWitnessUtxo: rawTx });

      } else if (output.scriptpubkey_type === 'v1_p2tr') {
        // Taproot
        const xOnlyPubkey = scriptBuf.slice(2);
        psbt.updateInput(i, {
          witnessUtxo: { script: scriptBuf, value },
          tapInternalKey: xOnlyPubkey,
        });

      } else {
        // Legacy P2PKH or unknown — use full raw tx
        const rawRes = await axios.get(`https://mempool.space/api/tx/${txid}/hex`, { timeout: 10_000 });
        const rawTx = Buffer.from(rawRes.data, 'hex');
        psbt.updateInput(i, { nonWitnessUtxo: rawTx });
      }

    } catch (e) {
      console.warn(`[PSBT] Could not enrich input ${i} (${txid}:${vout}):`, e.message);
    }
  }

  return psbt.toBase64();
}

function handleXcpError(res, error) {
  const raw = error.response?.data;
  const msg = raw && typeof raw === 'object' ? JSON.stringify(raw) : (raw || error.message || 'Unknown error');
  console.error('[XCP Error]', msg);

  if (String(msg).includes('insufficient funds')) {
    return res.status(402).json({ error: 'Insufficient funds', details: 'Check BTC balance for fees + 0.5 XCP for named asset registration' });
  }
  if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
    return res.status(503).json({ error: 'Counterparty server unreachable', url: COUNTERPARTY_URL });
  }
  if (String(msg).match(/413|too large|Request Entity Too Large/i)) {
    return res.status(413).json({ error: 'Payload too large', hint: 'File will be auto-chunked — retry with /api/mint' });
  }
  if (String(msg).match(/mime|Unrecognized.*MIME/i)) {
    return res.status(422).json({ error: 'Unsupported MIME type', details: msg, hint: 'Ensure patch_mime.py has been applied to the Counterparty server' });
  }
  return res.status(500).json({ error: msg });
}

// ─── Routes ───────────────────────────────────────────────────────────────────

// Swagger UI
app.get('/swagger-ui.html', (req, res) => {
  res.set('Content-Type', 'text/html').send(`<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><title>Counter-Inscription Minter API</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.4/swagger-ui.css">
<style>body{margin:0;padding:20px;background:#0a0a0f}
.swagger-ui{max-width:1400px;margin:0 auto;background:#121216;padding:20px;border-radius:8px}</style>
</head><body><div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5.17.4/swagger-ui-bundle.js"></script>
<script src="https://unpkg.com/swagger-ui-dist@5.17.4/swagger-ui-standalone-preset.js"></script>
<script>
window.onload = function() {
  fetch('/openapi-spec.json').then(function(r) { return r.json(); }).then(function(spec) {
    SwaggerUIBundle({
      spec: spec,
      dom_id: '#swagger-ui',
      deepLinking: true,
      validatorUrl: null,
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
      plugins: [SwaggerUIBundle.plugins.DownloadUrl],
      layout: 'StandaloneLayout'
    });
  });
};
</script>
</body></html>`);
});

/**
 * POST /api/mint
 * Single file → one wallet. Auto-chunks large files.
 * Accepts multipart/form-data (file field) OR application/x-www-form-urlencoded with hex in `description`.
 */
app.post('/api/mint', upload.single('file'), async (req, res) => {
  try {
    const {
      asset,
      quantity = 1,
      mime_type,
      encoding = 'taproot',
      sat_per_vbyte = 2.01,
      walletAddress,
      destinationWallet,
    } = req.body;

    const mintTo = destinationWallet?.trim() || walletAddress?.trim();

    if (!asset || !mintTo) {
      return res.status(400).json({ error: 'Missing required: asset, walletAddress (and optionally destinationWallet)' });
    }

    let fileBuffer, resolvedMime;
    if (req.file) {
      fileBuffer = req.file.buffer;
      resolvedMime = mime_type || detectMime(req.file);
    } else if (req.body.description) {
      // Already hex-encoded (from legacy clients)
      fileBuffer = Buffer.from(req.body.description, 'hex');
      resolvedMime = mime_type || 'application/octet-stream';
    } else {
      return res.status(400).json({ error: 'No file or description payload provided' });
    }

    const chunks = chunkBuffer(fileBuffer, MAX_CHUNK_BYTES);
    const transactions = [];

    for (let i = 0; i < chunks.length; i++) {
      const hexData = bufToHex(chunks[i]);
      const chunkAsset = chunks.length > 1 ? `${asset}_${i + 1}` : asset;
      const data = await composeIssuance({
        walletAddress: mintTo,
        asset: chunkAsset,
        mimeType: resolvedMime,
        hexData,
        satPerVbyte: parseFloat(sat_per_vbyte),
        encoding,
        quantity: parseInt(quantity),
      });
      transactions.push({ asset: chunkAsset, chunk: i + 1, total_chunks: chunks.length, data });
    }

    return res.json({
      success: true,
      asset,
      wallet: mintTo,
      total_chunks: chunks.length,
      file_size_bytes: fileBuffer.length,
      mime_type: resolvedMime,
      transactions,
    });
  } catch (error) {
    return handleXcpError(res, error);
  }
});

/**
 * POST /api/mint-batch
 * One file → multiple destination wallets (airdrop / collection drop).
 * File must fit in one chunk (<350KB). For larger files use /api/mint per wallet.
 */
app.post('/api/mint-batch', upload.single('file'), async (req, res) => {
  try {
    const {
      asset,
      mime_type,
      encoding = 'taproot',
      sat_per_vbyte = 2.01,
      walletAddress,
      destinationWallets,
    } = req.body;

    if (!asset || !walletAddress || !destinationWallets) {
      return res.status(400).json({ error: 'Missing required: asset, walletAddress, destinationWallets' });
    }

    const wallets = destinationWallets.split(',').map(w => w.trim()).filter(Boolean);
    if (wallets.length === 0) return res.status(400).json({ error: 'No valid wallet addresses' });

    let fileBuffer, resolvedMime;
    if (req.file) {
      fileBuffer = req.file.buffer;
      resolvedMime = mime_type || detectMime(req.file);
    } else if (req.body.description) {
      fileBuffer = Buffer.from(req.body.description, 'hex');
      resolvedMime = mime_type || 'application/octet-stream';
    } else {
      return res.status(400).json({ error: 'No file or description payload provided' });
    }

    if (fileBuffer.length > MAX_CHUNK_BYTES) {
      return res.status(413).json({
        error: `File too large for batch mint (${(fileBuffer.length / 1024).toFixed(0)}KB > ${MAX_CHUNK_BYTES / 1024}KB).`,
        hint: 'Use /api/mint with chunking support for large files, or reduce file size.',
      });
    }

    const hexData = bufToHex(fileBuffer);
    const results = [];
    for (const dest of wallets) {
      try {
        const data = await composeIssuance({
          walletAddress: dest,
          asset,
          mimeType: resolvedMime,
          hexData,
          satPerVbyte: parseFloat(sat_per_vbyte),
          encoding,
          quantity: 1,
        });
        results.push({ wallet: dest, status: 'success', data });
      } catch (err) {
        const errMsg = err.response?.data || err.message;
        results.push({ wallet: dest, status: 'failed', error: typeof errMsg === 'object' ? JSON.stringify(errMsg) : errMsg });
      }
    }

    const succeeded = results.filter(r => r.status === 'success').length;
    return res.json({ success: true, total: wallets.length, succeeded, failed: wallets.length - succeeded, results });
  } catch (error) {
    return handleXcpError(res, error);
  }
});

/**
 * POST /api/upload
 * Pre-flight file analysis. Returns mime, size, chunk count, hex preview.
 */
app.post('/api/upload', upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded' });
  const resolvedMime = detectMime(req.file);
  const chunks = chunkBuffer(req.file.buffer, MAX_CHUNK_BYTES);
  return res.json({
    success: true,
    originalName: req.file.originalname,
    mimeType: resolvedMime,
    sizeBytes: req.file.size,
    sizeKB: (req.file.size / 1024).toFixed(1),
    totalChunks: chunks.length,
    needsChunking: chunks.length > 1,
    hexPreview: bufToHex(req.file.buffer.slice(0, 256)),
  });
});

/** GET /api/balance/:address */
app.get('/api/balance/:address', async (req, res) => {
  try {
    const r = await axios.get(`${COUNTERPARTY_URL}/v2/addresses/${req.params.address}/balances`, { timeout: 10_000 });
    return res.json(r.data);
  } catch (error) {
    return res.status(500).json({ error: 'Failed to fetch balance', details: error.message });
  }
});

/** GET /api/health */
app.get('/api/health', async (req, res) => {
  try {
    const r = await axios.get(`${COUNTERPARTY_URL}/v2/`, { timeout: 5_000 });
    return res.json({ status: 'ok', counterparty: 'reachable', counterparty_url: COUNTERPARTY_URL, version: r.data?.version });
  } catch (error) {
    return res.json({ status: 'degraded', counterparty: 'unreachable', counterparty_url: COUNTERPARTY_URL, error: error.message });
  }
});

/** GET /api/mime-types — full supported MIME type list */
app.get('/api/mime-types', (req, res) => {
  return res.json({
    supported: {
      image: ['image/png','image/jpeg','image/gif','image/webp','image/svg+xml','image/bmp','image/avif','image/tiff','image/heic','image/jxl','image/x-icon'],
      audio: ['audio/mpeg','audio/ogg','audio/ogg;codecs=opus','audio/wav','audio/flac','audio/aac','audio/mp4','audio/webm','audio/midi','audio/x-aiff','audio/x-m4a'],
      video: ['video/mp4','video/webm','video/ogg','video/quicktime','video/x-matroska','video/x-msvideo','video/mpeg','video/3gpp','video/x-flv'],
      text: ['text/plain','text/html','text/css','text/javascript','text/markdown','text/csv','text/xml','text/yaml','text/x-python','text/x-rust','text/x-go','text/x-solidity','text/x-sh','text/x-lua','text/x-swift','text/x-kotlin','text/x-java','text/x-ruby','text/x-php','text/x-toml'],
      application: ['application/json','application/pdf','application/wasm','application/octet-stream','application/epub+zip','application/x-sqlite3','application/zip','application/gzip','application/x-7z-compressed','application/geo+json','application/ld+json','application/pgp-signature','application/vnd.ms-excel','application/msword','application/x-chess-pgn','application/vnd.google-earth.kml+xml','application/x-shockwave-flash','chemical/x-mdl-molfile'],
      model: ['model/gltf+json','model/gltf-binary','model/stl','model/obj','model/vrml','model/vnd.usdz+zip','application/x-blender'],
      font: ['font/ttf','font/otf','font/woff','font/woff2'],
    },
    max_chunk_kb: MAX_CHUNK_BYTES / 1024,
    max_file_mb: MAX_FILE_SIZE_MB,
  });
});

// OpenAPI spec
const serveSpec = (req, res) => {
  try {
    const jsonSpec = yaml.load(fs.readFileSync(path.join(__dirname, 'openapi-spec.yaml'), 'utf8'));
    res.set('Content-Type', 'application/json').json(jsonSpec);
  } catch (e) { res.status(500).json({ error: 'Cannot serve spec' }); }
};
['openapi-spec.json', 'api/openapi-spec.json', 'swagger-spec.json'].forEach(p => app.get('/' + p, serveSpec));

app.get('/openapi-spec.yaml', (req, res) => {
  try { res.set('Content-Type', 'text/x-yaml').send(fs.readFileSync(path.join(__dirname, 'openapi-spec.yaml'), 'utf8')); }
  catch (e) { res.status(500).json({ error: 'Cannot serve spec' }); }
});

app.get('/', (req, res) => res.redirect('/swagger-ui.html'));

// ─── Start ────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`✓ Backend running on http://0.0.0.0:${PORT}`);
  console.log(`✓ Swagger UI: http://localhost:${PORT}/swagger-ui.html`);
  console.log(`✓ Counterparty URL: ${COUNTERPARTY_URL}`);
  console.log(`✓ Max file size: ${MAX_FILE_SIZE_MB}MB | Chunk size: ${MAX_CHUNK_BYTES / 1024}KB`);
});

module.exports = app;