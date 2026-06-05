#!/usr/bin/env bash
# MinIO dev-mode için bucket setup.
# Kullanım: docker compose up -d minio && bash scripts/minio/seed_dev.sh
set -euo pipefail

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://127.0.0.1:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-sapb1-agent}"

if ! command -v mc >/dev/null 2>&1; then
  echo "[minio-seed] mc (MinIO client) bulunamadı, docker üzerinden çalıştırılıyor."
  MC="docker run --rm --network host minio/mc:latest"
else
  MC="mc"
fi

echo "[minio-seed] MinIO hazır mı kontrol ediliyor ($MINIO_ENDPOINT) ..."
for i in {1..30}; do
  if curl -fsS "${MINIO_ENDPOINT}/minio/health/ready" >/dev/null 2>&1; then
    break
  fi
  echo "  ... bekleniyor ($i/30)"
  sleep 1
done

echo "[minio-seed] Alias konfigüre ediliyor ..."
$MC alias set local "$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null

echo "[minio-seed] Bucket oluşturuluyor: $MINIO_BUCKET"
if $MC ls "local/$MINIO_BUCKET" >/dev/null 2>&1; then
  echo "  ... zaten var"
else
  $MC mb "local/$MINIO_BUCKET"
fi

echo "[minio-seed] Lifecycle: 365 gün sonra intake/ altındakileri sil (KVKK retention)"
cat <<'EOF' > /tmp/minio-lifecycle.json
{
  "Rules": [
    {
      "ID": "intake-retention-365",
      "Status": "Enabled",
      "Filter": {"Prefix": "intake/"},
      "Expiration": {"Days": 365}
    }
  ]
}
EOF
$MC ilm import "local/$MINIO_BUCKET" < /tmp/minio-lifecycle.json || echo "  (lifecycle import opsiyonel — atlandı)"
rm -f /tmp/minio-lifecycle.json

echo "[minio-seed] Tamam. Console: http://127.0.0.1:9001  User: $MINIO_ROOT_USER"
