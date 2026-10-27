#!/bin/sh
# API çalışırken OpenAPI tanımını docs/openapi.json'a yazar ve web tiplerini yeniden üretir.
# Kullanım (depo kökünden): sh scripts/api_tipleri_yenile.sh   — port farklıysa: API_PORT=18000 sh scripts/...
set -e
cd "$(dirname "$0")/.."
API="${API_URL:-http://localhost:${API_PORT:-8000}}"
PY="$(command -v python3 || command -v python)"
"$PY" -c "
import json, sys, urllib.request
spec = json.load(urllib.request.urlopen(sys.argv[1] + '/openapi.json'))
with open('docs/openapi.json', 'w', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
print(len(spec['paths']), 'uç yolu docs/openapi.json dosyasına yazıldı')
" "$API"
cd web && npm run -s api:types
