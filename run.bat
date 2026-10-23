@echo off
cd /d "%~dp0backend"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
echo Open http://localhost:8000
uvicorn main:app --reload --port 8000
