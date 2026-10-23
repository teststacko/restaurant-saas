# Restaurant Ops Dashboard
- backend/main.py   FastAPI + SQLite: schema-driven CRUD, dashboard analytics, bill upload, CSV reports, audit log
- backend/uploads/  bill photos and PDFs
- frontend/         single-page app (sidebar, KPI cards, charts, tables, forms)
- Dockerfile        docker build -t restops . && docker run -p 8000:8000 restops

Quick start (VS Code): File > Open Folder > restaurant-saas, then
  Windows: double-click run.bat   |   Mac/Linux: ./run.sh   |   or press F5 (Run Restaurant Ops) after installing requirements.
Then open http://localhost:8000

Run manually: cd backend && pip install -r requirements.txt && uvicorn main:app --reload
Open http://localhost:8000 and click "Load demo data" on the dashboard.

Add a field or section by editing SCHEMA in backend/main.py; forms, tables and reports follow automatically.

Before hosting for real: replace the X-Tenant header with login and roles, move to Postgres with row-level security,
put /uploads behind auth, serve over HTTPS, schedule backups.

## v3 changes
- Branding: Amber Fort Hotel Operation. Login/app shell no longer flash; section changes fade in; lists load 10 per page from the server.
- Settings & Access: Team (add/edit access with dashboard + tile checkboxes, reset password, activate/deactivate), Roles (custom roles), Activity Log (paginated, filter by member/action), Appearance.
- Migration `0005` is required: run `python manage.py migrate` (run.bat/run.sh now do this automatically).
- Passwords cannot be viewed (they are one-way hashes). Owners use "Reset password" to issue a temporary one shown once.
- WARNING: backend/make_app.py regenerates frontend/js/app.js from an old copy. Do NOT run it, or these changes are overwritten.
- Keep .env private; it contains your database passwords.
