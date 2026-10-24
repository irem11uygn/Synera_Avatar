#!/bin/sh
# API konteynerinin açılışı: veritabanını bekle, şema göçlerini uygula,
# veritabanı boşsa örnek kayıtları yükle, sunucuyu başlat.
set -e
python -c "from app.db import wait_for_database; wait_for_database()"
alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
