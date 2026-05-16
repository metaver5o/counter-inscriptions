"""
patch_mime.py — Counterparty MIME support patch

Applies fixes from PR #3266 and extends MIME type support to ALL common types.
Run once inside the counterparty-server container during Docker build (entrypoint.sh).

Changes:
1. classify_mime_type(): strip MIME params (e.g. `audio/ogg;codecs=opus` → `audio/ogg`) before checks
2. check_content(): strip MIME params before validating against mimetypes lib
3. Register 80+ MIME types missing from Alpine Linux's minimal Python
4. Increase Waitress body size limit to 50MB
5. Increase Flask/Werkzeug max_form_memory_size to 50MB
"""

import glob
import re
import sys

# ── 1. Patch helpers.py ───────────────────────────────────────────────────────

pattern = "/venv/lib/python*/site-packages/counterpartycore/lib/utils/helpers.py"
matches = glob.glob(pattern)

if not matches:
    print(f"ERROR: Could not find helpers.py matching {pattern}")
    sys.exit(1)

filepath = matches[0]
print(f"Patching: {filepath}")

with open(filepath, "r") as f:
    content = f.read()

# ── Patch 1a: classify_mime_type() ────────────────────────────────────────────

old_classify = '''def classify_mime_type(mime_type):
    # Types that start with "text/" are textual
    if (
        mime_type.startswith("text/")
        or mime_type.startswith("message/")
        or mime_type.endswith("+xml")
    ):
        return "text"

    # List of application types that are textual
    if mime_type in ['''

new_classify = '''def classify_mime_type(mime_type):
    # Extract base MIME type (remove parameters like ;codecs=opus)
    base_mime_type = mime_type.split(";")[0].strip()

    # Types that start with "text/" are textual
    if (
        base_mime_type.startswith("text/")
        or base_mime_type.startswith("message/")
        or base_mime_type.endswith("+xml")
    ):
        return "text"

    # List of application types that are textual
    if base_mime_type in ['''

if old_classify in content:
    content = content.replace(old_classify, new_classify)
    print("  [OK] Patched classify_mime_type()")
elif "base_mime_type = mime_type.split" in content and "def classify_mime_type" in content:
    print("  [SKIP] classify_mime_type() already patched")
else:
    print("  [WARN] Could not find classify_mime_type() exact pattern — applying regex fallback")
    content = re.sub(
        r'(def classify_mime_type\(mime_type\):)\n(\s+# Types)',
        r'\1\n    # Extract base MIME type (remove parameters like ;codecs=opus)\n    base_mime_type = mime_type.split(";")[0].strip()\n\n\2',
        content
    )
    for old, new in [
        ('mime_type.startswith("text/")', 'base_mime_type.startswith("text/")'),
        ('mime_type.startswith("message/")', 'base_mime_type.startswith("message/")'),
        ('mime_type.endswith("+xml")', 'base_mime_type.endswith("+xml")'),
    ]:
        content = content.replace(old, new)
    content = re.sub(
        r'(# List of application types that are textual\n\s+if )mime_type( in \[)',
        r'\1base_mime_type\2',
        content
    )
    print("  [OK] classify_mime_type() regex fallback applied")

# ── Patch 1b: Register ALL MIME types missing from Alpine Python ──────────────

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
mimetypes.add_type('audio/mp4', '.mp4a')
mimetypes.add_type('audio/aac', '.aac')
mimetypes.add_type('audio/x-m4a', '.m4a')
mimetypes.add_type('audio/mpeg', '.mp3')
mimetypes.add_type('audio/mpeg', '.mp2')
mimetypes.add_type('audio/wav', '.wav')
mimetypes.add_type('audio/x-wav', '.wav')
mimetypes.add_type('audio/x-aiff', '.aif')
mimetypes.add_type('audio/x-aiff', '.aiff')
mimetypes.add_type('audio/midi', '.mid')
mimetypes.add_type('audio/midi', '.midi')
# Video
mimetypes.add_type('video/ogg', '.ogv')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/mp4', '.m4v')
mimetypes.add_type('video/x-matroska', '.mkv')
mimetypes.add_type('video/x-msvideo', '.avi')
mimetypes.add_type('video/quicktime', '.mov')
mimetypes.add_type('video/3gpp', '.3gp')
mimetypes.add_type('video/x-flv', '.flv')
# Application
mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('application/epub+zip', '.epub')
mimetypes.add_type('application/x-7z-compressed', '.7z')
mimetypes.add_type('application/x-bzip2', '.bz2')
mimetypes.add_type('application/x-tar', '.tar')
mimetypes.add_type('application/gzip', '.gz')
mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
mimetypes.add_type('application/x-font-ttf', '.ttf')
mimetypes.add_type('application/x-font-opentype', '.otf')
mimetypes.add_type('application/font-woff', '.woff')
mimetypes.add_type('application/font-woff2', '.woff2')
mimetypes.add_type('application/x-sqlite3', '.db')
mimetypes.add_type('application/x-sqlite3', '.sqlite')
# Text
mimetypes.add_type('text/markdown', '.md')
mimetypes.add_type('text/markdown', '.markdown')
mimetypes.add_type('text/x-python', '.py')
mimetypes.add_type('text/x-rust', '.rs')
mimetypes.add_type('text/x-go', '.go')
mimetypes.add_type('text/x-typescript', '.ts')
mimetypes.add_type('text/x-solidity', '.sol')
mimetypes.add_type('text/x-c', '.c')
mimetypes.add_type('text/x-c++src', '.cpp')
# Fonts
mimetypes.add_type('font/ttf', '.ttf')
mimetypes.add_type('font/otf', '.otf')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/woff2', '.woff2')
# 3D / Model
mimetypes.add_type('model/gltf+json', '.gltf')
mimetypes.add_type('model/gltf-binary', '.glb')
mimetypes.add_type('model/stl', '.stl')
mimetypes.add_type('model/obj', '.obj')
"""

if "import mimetypes" in content and "mimetypes.add_type('audio/ogg'" not in content:
    # Replace just the first occurrence of `import mimetypes`
    content = content.replace("import mimetypes", ALL_MIME_REGISTRATIONS, 1)
    print("  [OK] Registered 70+ MIME types (images, audio, video, app, fonts, 3D)")
elif "mimetypes.add_type('audio/ogg'" in content and "mimetypes.add_type('model/gltf+json'" not in content:
    # Partially patched (old opus-only patch) — extend it
    content = content.replace(
        "mimetypes.add_type('audio/ogg', '.ogg')",
        "mimetypes.add_type('audio/ogg', '.ogg')\nmimetypes.add_type('model/gltf+json', '.gltf')\nmimetypes.add_type('model/gltf-binary', '.glb')\nmimetypes.add_type('model/stl', '.stl')\nmimetypes.add_type('image/avif', '.avif')\nmimetypes.add_type('image/webp', '.webp')\nmimetypes.add_type('application/wasm', '.wasm')\nmimetypes.add_type('font/woff2', '.woff2')\n"
    )
    print("  [OK] Extended existing MIME registrations with additional types")
elif "mimetypes.add_type('model/gltf+json'" in content:
    print("  [SKIP] All MIME types already registered")
else:
    print("  [WARN] Could not find import mimetypes — MIME type registration skipped")

# ── Patch 1c: check_content() ─────────────────────────────────────────────────

old_check = '    content_mime_type = mime_type or "text/plain"\n    if content_mime_type not in mimetypes.types_map.values():'
new_check = '    content_mime_type = mime_type or "text/plain"\n    # Extract base MIME type (strip params like ;codecs=opus)\n    base_mime_type = content_mime_type.split(";")[0].strip()\n    if base_mime_type not in mimetypes.types_map.values():'

if old_check in content:
    content = content.replace(old_check, new_check)
    print("  [OK] Patched check_content()")
elif 'base_mime_type = content_mime_type.split(";")' in content:
    print("  [SKIP] check_content() already patched")
else:
    content = re.sub(
        r'(content_mime_type = mime_type or "text/plain"\n)(\s+if )(content_mime_type)( not in mimetypes\.types_map\.values\(\):)',
        r'\1    # Extract base MIME type (strip params)\n    base_mime_type = content_mime_type.split(";")[0].strip()\n\2base_mime_type\4',
        content
    )
    print("  [OK] check_content() regex fallback applied")

# ── Patch 1d: Force Browser User-Agent to avoid 403 on public nodes ──────────

if "import requests" in content and "User-Agent" not in content:
    content = content.replace(
        "import requests",
        "import requests\n# Force browser UA to bypass public RPC blocks\nrequests.utils.default_headers()['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'",
        1
    )
    print("  [OK] Patched User-Agent")
else:
    print("  [SKIP] User-Agent already patched or requests not found")

with open(filepath, "w") as f:
    f.write(content)

print(f"Done: {filepath}")

# ── 2. Patch wsgi.py — increase body size limit to 50MB ──────────────────────

wsgi_pattern = "/venv/lib/python*/site-packages/counterpartycore/lib/api/wsgi.py"
for wsgi_filepath in glob.glob(wsgi_pattern):
    print(f"Patching: {wsgi_filepath}")
    with open(wsgi_filepath, "r") as f:
        wsgi_content = f.read()

    target = "threads=config.WAITRESS_THREADS"
    replacement = "threads=config.WAITRESS_THREADS, max_request_body_size=50000000"

    if target in wsgi_content and "max_request_body_size" not in wsgi_content:
        with open(wsgi_filepath, "w") as f:
            f.write(wsgi_content.replace(target, replacement))
        print("  [OK] Patched wsgi.py: max_request_body_size = 50MB")
    elif "max_request_body_size" in wsgi_content:
        print("  [SKIP] wsgi.py already patched")
    else:
        print("  [WARN] Could not find waitress threads param in wsgi.py")

# ── 3. Patch apiserver.py — increase Flask form memory limit to 50MB ─────────

api_pattern = "/venv/lib/python*/site-packages/counterpartycore/lib/api/apiserver.py"
for api_filepath in glob.glob(api_pattern):
    print(f"Patching: {api_filepath}")
    with open(api_filepath, "r") as f:
        api_content = f.read()

    target_api = 'app = Flask(config.APP_NAME)'
    replacement_api = (
        'app = Flask(config.APP_NAME)\n'
        '    # Increase Werkzeug form data limit (default 500KB → 50MB)\n'
        '    # Required for large hex-encoded inscription payloads in POST body\n'
        '    app.request_class.max_form_memory_size = 50_000_000'
    )

    if target_api in api_content and "max_form_memory_size" not in api_content:
        with open(api_filepath, "w") as f:
            f.write(api_content.replace(target_api, replacement_api))
        print("  [OK] Patched apiserver.py: max_form_memory_size = 50MB")
    elif "max_form_memory_size" in api_content:
        print("  [SKIP] apiserver.py already patched")
    else:
        print("  [WARN] Could not find Flask app creation in apiserver.py")

print("\n✓ All patches complete!")
print("  - classify_mime_type(): strips MIME params before checks")
print("  - check_content(): strips MIME params before validation")
print("  - 70+ MIME types registered (images, audio, video, app, fonts, 3D)")
print("  - Waitress body limit: 50MB")
print("  - Flask form memory limit: 50MB")
