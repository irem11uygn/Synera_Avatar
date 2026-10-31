#!/bin/sh
# Geri yükleme denemesi (çalışan sisteme dokunmaz): yedek alır, ayrı bir veritabanına (avatar_geri_deneme)
# geri yükler, o veritabanının dökümünü yedekle satır satır karşılaştırır, tablo ve satır sayılarını
# yazar, deneme veritabanını siler. Yedek, geri yüklenebildiği gösterilmedikçe yedek sayılmaz.
# Kullanım (depo kökünden): sh scripts/yedek_denemesi.sh        Ortam: PROJE (avatar), YEDEK_KLASORU (yedekler)
set -eu
cd "$(dirname "$0")/.."
PROJE="${PROJE:-avatar}"
DENEME=avatar_geri_deneme
export PROJE

mysql_root() {
  docker compose -p "$PROJE" exec -T -e HEDEF="$DENEME" db sh -c "MYSQL_PWD=\"\$MYSQL_ROOT_PASSWORD\" $1"
}
temizle() {
  mysql_root 'mysql -uroot -e "DROP DATABASE IF EXISTS \`$HEDEF\`"' || true
}
trap temizle EXIT

echo "1/4 Yedek alınıyor…"
sonuc=$(sh scripts/yedekle.sh)
echo "$sonuc"
yedek=${sonuc#Yedek alındı: }
yedek=${yedek% (*}

echo "2/4 Ayrı veritabanına geri yükleniyor ($DENEME)…"
sh scripts/geri_yukle.sh "$yedek" "$DENEME"

echo "3/4 Geri yüklenen veritabanı yedekle karşılaştırılıyor…"
# Yorum satırları (tarih, veritabanı adı) dışında iki döküm aynı olmalı.
fark=$(mysql_root 'mysqldump -uroot --single-transaction --triggers --routines --events --no-tablespaces \
  --set-gtid-purged=OFF "$HEDEF"' | grep -v '^--' | cksum)
asil=$(gzip -dc "$yedek" | grep -v '^--' | cksum)
if [ "$fark" != "$asil" ]; then
  echo "BAŞARISIZ: geri yüklenen veri yedekle aynı değil." >&2
  exit 1
fi
echo "Aynı: tablolar, satırlar ve tetikleyiciler yedekle bire bir eşleşti."

echo "4/4 Geri yüklenen veritabanında tablo ve satır sayıları:"
mysql_root 'mysql -uroot -N "$HEDEF" -e "
  SELECT CONCAT(COUNT(*), \" tablo\") FROM information_schema.tables WHERE table_schema = DATABASE();
  SELECT CONCAT(COUNT(*), \" tetikleyici\") FROM information_schema.triggers WHERE trigger_schema = DATABASE();
  SELECT CONCAT(\"users: \", COUNT(*)) FROM users;
  SELECT CONCAT(\"lots: \", COUNT(*)) FROM lots;
  SELECT CONCAT(\"stock_movements: \", COUNT(*)) FROM stock_movements;
  SELECT CONCAT(\"sales: \", COUNT(*)) FROM sales;"'
echo "Deneme veritabanı siliniyor; çalışan sistem değişmedi."
