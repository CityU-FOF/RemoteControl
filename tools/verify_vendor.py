"""Verify the checked-in PDF.js files against their recorded SHA-256 hashes."""
import hashlib, json
from pathlib import Path
base=Path(__file__).resolve().parents[1]
lock=json.loads((base/'pdfjs-vendor.lock.json').read_text())
for name,digest in lock['files'].items():
    actual=hashlib.sha256((base/'assistant/static/pdfjs'/name).read_bytes()).hexdigest()
    if actual!=digest:raise SystemExit(f'Vendor integrity failure: {name}')
print(f"Verified {len(lock['files'])} PDF.js {lock['version']} vendor files")
