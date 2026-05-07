#!/usr/bin/env bash
set -e
mkdir -p data/uploads
cd backend
python -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
