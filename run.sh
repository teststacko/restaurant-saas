#!/usr/bin/env bash
cd "$(dirname "$0")/backend"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
echo "Open http://localhost:8000"
uvicorn main:app --reload --port 8000
