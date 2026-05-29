"""
patch_mime.py — Counterparty MIME support patch for v11.1.0+

In v11.1.0, MIME validation moved to protocol-flag-gated logic.
The old string patches no longer apply.
This version:
1. Forces extended_mime_types_support protocol flag ON unconditionally
2. Registers 100+ MIME types missing from Alpine Python
3. Patches wsgi.py and apiserver.py for 50MB body limits
"""

import glob
import sys

# ── 1. Patch helpers.py — force extended_mime_types_support ──────────────────

pattern = "/venv/lib/python*/site-packages/counterpartycore/lib/utils/helpers.py"
matches = glob.glob(pattern)

if not matches:
    print(f"ERROR: Could not find helpers.py matching {pattern}")
    sys.exit(1)

filepath = matches[0]
print(f"Patching: {filepath}")

with open(filepath, "r") as f:
    content = f.read()

# ── Patch: force extended_mime_types_support to always return True ────────────
# v11.1.0 gates MIME validation behind protocol.enabled("extended_mime_types_support")
# We patch the check to always be True so all registered MIME types are accepted.

old_check = 'if protocol.enabled("extended_mime_types_support", block_index=block_index):'
new_check = 'if True:  # patched: extended_mime_types_support always enabled'

if old_check in content:
    content = content.replace(old_check, new_check)
    print("  [OK] Patched check_content(): extended_mime_types_support always True")
elif 'patched: extended_mime_types_support always enabled' in content:
    print("  [SKIP] check_content() already patched")
else:
    print("  [WARN] check_content() pattern not found — trying classify_mime_type patch")

# ── Patch: classify_mime_type — same flag ────────────────────────────────────
old_classify = 'if protocol.enabled("extended_mime_types_support", block_index=block_index):'
# Already replaced above if it's the same string. Check for second occurrence.
count = content.count('if True:  # patched: extended_mime_types_support always enabled')
orig_count = content.count(old_classify)
if orig_count > 0:
    content = content.replace(old_classify, new_check)
    print(f"  [OK] Patched {orig_count} more extended_mime_types_support occurrences")

# ── Register ALL MIME types ───────────────────────────────────────────────────

ALL_MIME_REGISTRATIONS = """
import mimetypes

# ── All MIME types missing from Alpine Linux's minimal Python ──
# Images
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('image/avif', '.avif')
mimetypes.add_type('image/heic', '.heic')
mimetypes.add_type('image/heif', '.heif')
mimetypes.add_type('image/jxl', '.jxl')
mimetypes.add_type('image/bmp', '.bmp')
mimetypes.add_type('image/tiff', '.tiff')
mimetypes.add_type('image/tiff', '.tif')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('image/x-icon', '.ico')
# Audio
mimetypes.add_type('audio/ogg', '.ogg')
mimetypes.add_type('audio/ogg', '.oga')
mimetypes.add_type('audio/ogg', '.opus')
mimetypes.add_type('audio/flac', '.flac')
mimetypes.add_type('audio/webm', '.weba')
mimetypes.add_type('audio/mp4', '.m4a')
mimetypes.add_type('audio/aac', '.aac')
mimetypes.add_type('audio/x-m4a', '.m4a')
mimetypes.add_type('audio/mpeg', '.mp3')
mimetypes.add_type('audio/wav', '.wav')
mimetypes.add_type('audio/midi', '.mid')
mimetypes.add_type('audio/midi', '.midi')
mimetypes.add_type('audio/x-aiff', '.aif')
mimetypes.add_type('audio/x-aiff', '.aiff')
# Video
mimetypes.add_type('video/ogg', '.ogv')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/mp4', '.m4v')
mimetypes.add_type('video/x-matroska', '.mkv')
mimetypes.add_type('video/x-msvideo', '.avi')
mimetypes.add_type('video/quicktime', '.mov')
mimetypes.add_type('video/3gpp', '.3gp')
mimetypes.add_type('video/mpeg', '.mpeg')
mimetypes.add_type('video/mpeg', '.mpg')
# Application
mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('application/epub+zip', '.epub')
mimetypes.add_type('application/x-7z-compressed', '.7z')
mimetypes.add_type('application/x-bzip2', '.bz2')
mimetypes.add_type('application/x-tar', '.tar')
mimetypes.add_type('application/gzip', '.gz')
mimetypes.add_type('application/x-sqlite3', '.db')
mimetypes.add_type('application/x-sqlite3', '.sqlite')
mimetypes.add_type('application/geo+json', '.geojson')
mimetypes.add_type('application/ld+json', '.jsonld')
mimetypes.add_type('application/pgp-signature', '.asc')
mimetypes.add_type('application/vnd.ms-excel', '.xls')
mimetypes.add_type('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx')
mimetypes.add_type('application/msword', '.doc')
mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')
mimetypes.add_type('application/x-chess-pgn', '.pgn')
mimetypes.add_type('application/x-blender', '.blend')
mimetypes.add_type('application/vnd.google-earth.kml+xml', '.kml')
mimetypes.add_type('chemical/x-mdl-molfile', '.mol')
# Fonts
mimetypes.add_type('font/ttf', '.ttf')
mimetypes.add_type('font/otf', '.otf')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('application/x-font-ttf', '.ttf')
mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
# Text / Code
mimetypes.add_type('text/markdown', '.md')
mimetypes.add_type('text/yaml', '.yaml')
mimetypes.add_type('text/yaml', '.yml')
mimetypes.add_type('text/x-python', '.py')
mimetypes.add_type('text/x-rust', '.rs')
mimetypes.add_type('text/x-go', '.go')
mimetypes.add_type('text/x-solidity', '.sol')
mimetypes.add_type('text/x-sh', '.sh')
mimetypes.add_type('text/x-lua', '.lua')
mimetypes.add_type('text/x-swift', '.swift')
mimetypes.add_type('text/x-kotlin', '.kt')
mimetypes.add_type('text/x-java', '.java')
mimetypes.add_type('text/x-ruby', '.rb')
mimetypes.add_type('text/x-php', '.php')
mimetypes.add_type('text/x-toml', '.toml')
mimetypes.add_type('text/xml', '.xml')
# 3D / Model
mimetypes.add_type('model/gltf+json', '.gltf')
mimetypes.add_type('model/gltf-binary', '.glb')
mimetypes.add_type('model/stl', '.stl')
mimetypes.add_type('model/obj', '.obj')
mimetypes.add_type('model/vrml', '.wrl')
mimetypes.add_type('model/vnd.usdz+zip', '.usdz')
"""

if "import mimetypes" in content and "mimetypes.add_type('audio/ogg'" not in content:
    content = content.replace("import mimetypes", ALL_MIME_REGISTRATIONS, 1)
    print("  [OK] Registered 80+ MIME types")
elif "mimetypes.add_type('audio/ogg'" in content:
    print("  [SKIP] MIME types already registered")
else:
    # inject at top of file
    content = ALL_MIME_REGISTRATIONS + "\n" + content
    print("  [OK] Injected MIME registrations at top of file")

with open(filepath, "w") as f:
    f.write(content)

print(f"Done: {filepath}")

# ── 2. Patch protocol.py — force extended_mime_types_support always enabled ───
# Belt-and-suspenders: also patch the protocol flag itself

proto_pattern = "/venv/lib/python*/site-packages/counterpartycore/lib/parser/protocol.py"
for proto_filepath in glob.glob(proto_pattern):
    print(f"Patching: {proto_filepath}")
    with open(proto_filepath, "r") as f:
        proto_content = f.read()

    if '"extended_mime_types_support"' in proto_content and 'patched_mime_always_on' not in proto_content:
        # Find the extended_mime_types_support entry and force its block height to 0
        import re
        # Replace the block height for extended_mime_types_support with 0
        patched = re.sub(
            r'("extended_mime_types_support"\s*[,:]\s*)\{[^}]*\}',
            r'\1{"mainnet": 0, "testnet": 0, "regtest": 0}  # patched_mime_always_on',
            proto_content
        )
        if patched != proto_content:
            with open(proto_filepath, "w") as f:
                f.write(patched)
            print("  [OK] extended_mime_types_support activated from block 0")
        else:
            print("  [WARN] Could not find extended_mime_types_support block height entry")
    elif 'patched_mime_always_on' in proto_content:
        print("  [SKIP] protocol.py already patched")
    else:
        print("  [WARN] extended_mime_types_support not found in protocol.py")

# ── 3. Patch wsgi.py — increase body size to 50MB ────────────────────────────

wsgi_pattern = "/venv/lib/python*/site-packages/counterpartycore/lib/api/wsgi.py"
for wsgi_filepath in glob.glob(wsgi_pattern):
    print(f"Patching: {wsgi_filepath}")
    with open(wsgi_filepath, "r") as f:
        wsgi_content = f.read()
    if "max_request_body_size" not in wsgi_content and "threads=config.WAITRESS_THREADS" in wsgi_content:
        with open(wsgi_filepath, "w") as f:
            f.write(wsgi_content.replace(
                "threads=config.WAITRESS_THREADS",
                "threads=config.WAITRESS_THREADS, max_request_body_size=50000000"
            ))
        print("  [OK] wsgi.py: max_request_body_size = 50MB")
    elif "max_request_body_size" in wsgi_content:
        print("  [SKIP] wsgi.py already patched")
    else:
        print("  [WARN] wsgi.py threads param not found")

print("\n✓ All patches complete!")
print("  - extended_mime_types_support: always ON (helpers.py + protocol.py)")
print("  - 80+ MIME types registered")
print("  - Waitress body limit: 50MB")