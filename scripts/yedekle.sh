#!/bin/sh
# Veritabanı yedeği: çalışan "db" kapsayıcısında mysqldump (--single-transaction: sistem çalışırken tutarlı
# anlık görüntü; tetikleyiciler dahil), gzip'li dosya yedekler/ klasörüne yazılır. Yarım kalan döküm
# yedek sayılmaz. En yeni YEDEK_SAKLA (14) yedek kalır, daha eski avatar_*.sql.gz dosyaları silinir.
# Şifre komut satırına, ekrana ya da dosyaya yazılmaz: kapsayıcının kendi MYSQL_ROOT_PASSWORD değişkeni kullanılır.
# Kullanım (depo kökünden): sh scripts/yedekle.sh
#   Ortam: PROJE (avatar; docker compose -p adı), YEDEK_KLASORU (yedekler), YEDEK_SAKLA (14)
# Geri yükleme: sh scripts/geri_yukle.sh <dosya> — yedekler/ klasörünü düzenli olarak başka bir diske kopyalayın.
set -eu
cd "$(dirname "$0")/.."
PROJE="${PROJE:-avatar}"
KLASOR="${YEDEK_KLASORU:-yedekler}"
SAKLA="${YEDEK_SAKLA:-14}"

mkdir -p "$KLASOR"
dosya="$KLASOR/avatar_$(date +%Y%m%d_%H%M%S).sql.gz"
gecici="$dosya.yaziliyor"
trap 'rm -f "$gecici"' EXIT

docker compose -p "$PROJE" exec -T db sh -c \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --triggers --routines --events \
   --no-tablespaces --set-gtid-purged=OFF "$MYSQL_DATABASE"' | gzip -9 > "$gecici"

# POSIX sh'ta boru hattının hatası görünmez; mysqldump bitirdiğini son satırda yazar.
if ! gzip -dc "$gecici" | tail -n 1 | grep -q '^-- Dump completed'; then
  echo "Yedek alınamadı (döküm yarım kaldı); eski yedeklere dokunulmadı." >&2
  exit 1
fi
mv "$gecici" "$dosya"
trap - EXIT

ls -1t "$KLASOR"/avatar_*.sql.gz | tail -n +"$((SAKLA + 1))" | while IFS= read -r eski; do
  rm -f "$eski"
done
echo "Yedek alındı: $dosya ($(wc -c < "$dosya" | tr -d ' ') bayt)"
