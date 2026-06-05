#!/usr/bin/env bash
# İlk kurulum scripti — yerel makinada projeyi ayağa kaldırır.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "→ .env dosyaları kopyalanıyor (zaten varsa atlanır)..."
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env

echo "→ Backend Python venv kurulumu..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
deactivate
cd "$ROOT"

echo "→ Frontend bağımlılıkları..."
cd frontend
npm install --legacy-peer-deps
cd "$ROOT"

echo "✓ Kurulum tamam."
echo "  Backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo "  Veya Docker: docker compose -f docker/docker-compose.yml up -d"
