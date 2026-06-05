#!/usr/bin/env bash
# Vault dev-mode için tohum secret'lar.
# Kullanım: docker compose up -d vault && bash scripts/vault/seed_dev.sh
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-token}"

vault_curl() {
  curl -fsS \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -H "Content-Type: application/json" \
    "$@"
}

echo "[vault-seed] Vault hazır mı kontrol ediliyor ($VAULT_ADDR) ..."
for i in {1..30}; do
  if curl -fsS "${VAULT_ADDR}/v1/sys/health" >/dev/null 2>&1; then
    break
  fi
  echo "  ... bekleniyor ($i/30)"
  sleep 1
done

# KV v2 engine aktif mi? Dev modda default `secret/` mount'lu, biz `kv/` istiyoruz.
if ! vault_curl "${VAULT_ADDR}/v1/sys/mounts" | grep -q '"kv/"'; then
  echo "[vault-seed] kv/ engine etkinleştiriliyor ..."
  vault_curl -X POST -d '{"type":"kv","options":{"version":"2"}}' \
    "${VAULT_ADDR}/v1/sys/mounts/kv" >/dev/null
fi

echo "[vault-seed] Elekon SAP credential seed ediliyor ..."
vault_curl -X POST \
  -d '{"data":{"username":"manager","password":"NyNl.2021","company_db":"2026_Test","sl_base_url":"https://10.11.10.46:50000/b1s/v1"}}' \
  "${VAULT_ADDR}/v1/kv/data/tenants/elekon/sap" >/dev/null

echo "[vault-seed] Global OpenRouter key seed ediliyor (boş, manuel doldur) ..."
vault_curl -X POST \
  -d '{"data":{"api_key":"REPLACE_ME"}}' \
  "${VAULT_ADDR}/v1/kv/data/global/openrouter" >/dev/null

echo "[vault-seed] Doğrulama:"
vault_curl "${VAULT_ADDR}/v1/kv/data/tenants/elekon/sap" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  sap user:', d['data']['data'].get('username'))"

echo "[vault-seed] Tamam. UI: ${VAULT_ADDR}/ui  Token: ${VAULT_TOKEN}"
