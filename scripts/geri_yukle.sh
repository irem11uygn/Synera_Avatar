#!/bin/sh
# Yedekten geri yükleme. DİKKAT: hedef veritabanındaki her şey yedekteki hâliyle DEĞİŞTİRİLİR.
# Kullanım (depo kökünden):
#   sh scripts/geri_yukle.sh yedekler/avatar_20261031_120000.sql.gz                 — çalışan sistem (onay ister)
#   sh scripts/geri_yukle.sh yedekler/avatar_20261031_120000.sql.gz avatar_deneme  — ayrı veritabanına (deneme)
# Çalışan sistemin veritabanına yüklerken sunucu (api) durdurulur, yükleme bitince yeniden başlatılır.
# Telefonlar bir sonraki eşitlemede veri kümesi değiştiğini görür ve yerel kopyalarını baştan kurar
# (docs/senkronizasyon.md). Onay sorusunu atlamak için: ONAY=EVET
set -eu
cd "$(dirname "$0")/.."
PROJE="${PROJE:-avatar}"
yedek="${1:?Kullanım: sh scripts/geri_yukle.sh <yedek.sql.gz> [hedef_veritabani]}"
hedef="${2:-avatar}"

case "$hedef" in
  "" | *[!A-Za-z0-9_]*) echo "Geçersiz veritabanı adı: $hedef" >&2; exit 2 ;;
esac
[ -f "$yedek" ] || { echo "Yedek dosyası yok: $yedek" >&2; exit 2; }
gzip -t "$yedek"
if ! gzip -dc "$yedek" | tail -n 1 | grep -q '^-- Dump completed'; then
  echo "Yedek eksik (döküm yarım kalmış); geri yükleme yapılmadı." >&2
  exit 1
fi

canli=0
[ "$hedef" = avatar ] && canli=1
if [ "$canli" = 1 ] && [ "${ONAY:-}" != EVET ]; then
  printf 'Çalışan sistemin veritabanı (%s) yedekteki hâliyle DEĞİŞTİRİLECEK. Devam için EVET yazın: ' "$hedef"
  read -r cevap
  [ "$cevap" = EVET ] || { echo "Vazgeçildi; hiçbir şey değişmedi."; exit 1; }
fi

[ "$canli" = 1 ] && docker compose -p "$PROJE" stop api >/dev/null
docker compose -p "$PROJE" exec -T -e HEDEF="$hedef" db sh -c \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "DROP DATABASE IF EXISTS \`$HEDEF\`; CREATE DATABASE \`$HEDEF\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"'
gzip -dc "$yedek" | docker compose -p "$PROJE" exec -T -e HEDEF="$hedef" db sh -c \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot "$HEDEF"'
[ "$canli" = 1 ] && docker compose -p "$PROJE" start api >/dev/null
echo "Geri yüklendi: $yedek → $hedef"
