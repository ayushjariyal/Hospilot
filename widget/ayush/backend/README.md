# Hospilot Widget Backend (FastAPI)

Tiny backend to perform Hospilot login, session creation and session polling.

Files added
- main.py — FastAPI application with `/login`, `/sessions` (POST) and `/sessions/{id}` (GET).
- requirements.txt — Python dependencies.

Environment
- Set these environment variables (or POST credentials to `/login` during development):
  - `HOSPILOT_USERNAME` — sandbox username
  - `HOSPILOT_PASSWORD` — sandbox password
  - Optionally `HOSPILOT_TOKEN` — a previously obtained token

Install & run (local)

```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Example usage (quick)

1) Login (server will call Hospilot and return token):

```bash
curl -X POST http://127.0.0.1:8000/login -H "Content-Type: application/json" -d '{"username":"<user>","password":"<pass>"}'
```

2) Create a session (use the returned token):

```bash
curl -X POST http://127.0.0.1:8000/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"goal":"[CANDIDATE-yourname] Check ICU bed capacity for tonight","constraints":"","autonomous":false}'
```

3) Poll session:

```bash
curl http://127.0.0.1:8000/sessions/<session_id> -H "Authorization: Bearer <token>"
```

Notes
- This backend is intentionally tiny. For deployment (Vercel serverless, etc.) set the sandbox credentials in environment variables.
- Current CORS policy is permissive for common local origins; lock it down for production.
