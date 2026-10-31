#!/bin/sh
# Canlı güvenlik denemesi (scripts/guvenlik_denemesi.py): çalışan sisteme, Docker ağının içinden web
# kapsayıcısı (nginx) üzerinden saldırı istekleri atar. Kaba kuvvet kilidi denemenin kapsayıcısına
# düşer; tarayıcınızdaki girişi etkilemez. Sistem açık olmalı (docker compose up -d).
# Kullanım (depo kökünden): sh scripts/guvenlik_denemesi.sh        Başka proje adı: PROJE=avatar-yeni sh ...
set -e
cd "$(dirname "$0")/.."
PROJE="${PROJE:-avatar}"
# Git Bash'te Docker'a Windows biçiminde yol verilir (pwd -W); Linux/macOS'ta düz pwd.
BETIK_DIR="$( (pwd -W 2>/dev/null || pwd) )/scripts"
MSYS_NO_PATHCONV=1 docker compose -p "$PROJE" run --rm --no-deps -v "$BETIK_DIR:/betik:ro" \
  api python /betik/guvenlik_denemesi.py http://web
