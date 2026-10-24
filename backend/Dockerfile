# Derleme bağlamı depo köküdür (docker-compose.yml): ileride ml/ ve data/ da kopyalanacak.
FROM python:3.12-slim

# Kod dizini çalışma kullanıcısı için salt okunur kalır; araç önbellekleri /tmp'ye yazılır.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RUFF_CACHE_DIR=/tmp/ruff-cache \
    PYTEST_ADDOPTS="-p no:cacheprovider"

WORKDIR /app

# Test araçları da kurulur: testler konteynerde çalıştırılır (docker compose run --rm api pytest).
COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY backend/ ./
COPY data/seed /data/seed
ENV SEED_DIR=/data/seed

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
CMD ["sh", "start.sh"]
