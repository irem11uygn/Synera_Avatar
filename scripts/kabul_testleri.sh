#!/bin/sh
# Kabul testleri (AT-01…AT-15, T-23): sistemi AYRI bir kopyada sıfırdan kurar, testleri çalışan sisteme
# karşı koşar, kopyayı siler. Geliştirme veritabanına ve açık sisteme dokunmaz.
# Kullanım (depo kökünden): sh scripts/kabul_testleri.sh        — kopyayı bırakmak için: KOPYAYI_BIRAK=1 sh ...
# Portlar: KABUL_API_PORT (18200), KABUL_WEB_PORT (18280).
set -e
cd "$(dirname "$0")/.."
PROJECT=avatar-kabul
export API_PORT="${KABUL_API_PORT:-18200}" WEB_PORT="${KABUL_WEB_PORT:-18280}" SEED_PROFILE=demo
# Git Bash'te Docker'a Windows biçiminde yol verilir (pwd -W); Linux/macOS'ta düz pwd.
TESTS_DIR="$( (pwd -W 2>/dev/null || pwd) )/tests"

echo "1/3 Sistem sıfırdan kuruluyor (proje: $PROJECT, API portu $API_PORT)…"
docker compose -p "$PROJECT" down -v >/dev/null 2>&1 || true
docker compose -p "$PROJECT" up -d --build db api >/dev/null

echo "2/3 Kabul testleri çalışıyor…"
status=0
MSYS_NO_PATHCONV=1 docker compose -p "$PROJECT" run --rm --no-deps \
  -v "$TESTS_DIR:/kabul:ro" -w /kabul -e AVATAR_API_URL=http://api:8000/api/v1 \
  api pytest -q -rA -s /kabul || status=$?

if [ -z "$KOPYAYI_BIRAK" ]; then
  echo "3/3 Kopya siliniyor…"
  docker compose -p "$PROJECT" down -v >/dev/null 2>&1 || true
else
  echo "3/3 Kopya bırakıldı: http://localhost:$API_PORT/docs"
fi
exit $status
