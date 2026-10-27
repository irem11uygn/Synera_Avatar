#!/bin/sh
# API çalışırken OpenAPI tanımını docs/openapi.json'a yazar ve web tiplerini yeniden üretir.
# Yalnız Node.js gerekir (web tipleri için zaten gerekli).
# Kullanım (depo kökünden): sh scripts/api_tipleri_yenile.sh   — port farklıysa: API_PORT=18000 sh scripts/...
set -e
cd "$(dirname "$0")/.."
API="${API_URL:-http://localhost:${API_PORT:-8000}}"
node -e "
const url = process.argv[1] + '/openapi.json'
fetch(url)
  .then((response) => {
    if (!response.ok) throw new Error(url + ' HTTP ' + response.status)
    return response.json()
  })
  .then((spec) => {
    require('fs').writeFileSync('docs/openapi.json', JSON.stringify(spec, null, 2) + '\n')
    console.log(Object.keys(spec.paths).length + ' uç yolu docs/openapi.json dosyasına yazıldı')
  })
  .catch((error) => {
    console.error('API tanımı alınamadı (API çalışıyor mu?): ' + error.message)
    process.exit(1)
  })
" "$API"
cd web && npm run -s api:types
