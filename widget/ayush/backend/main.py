from typing import Optional
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx

BASE_URL = "https://hospilot.carer.ai"

_LAST_TOKEN: Optional[str] = None

app = FastAPI(title="Hospilot Widget Backend")
WIDGET_HTML_PATH = Path(__file__).resolve().parents[1] / "widget.html"

# Allow local development origins; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class SessionRequest(BaseModel):
    goal: str
    constraints: Optional[str] = ""
    autonomous: bool = False


def extract_token(authorization: Optional[str]) -> Optional[str]:
    """Accept either `Bearer <token>` or a raw token string.

    Swagger UI users often paste only the JWT into the header field. The
    backend should treat both forms as valid.
    """
    if not authorization:
        return None
    value = authorization.strip()
    if value.lower().startswith("bearer "):
        value = value.split(None, 1)[1].strip()
    return value or None


def resolve_token(authorization: Optional[str]) -> Optional[str]:
    return extract_token(authorization) or _LAST_TOKEN or os.environ.get("HOSPILOT_TOKEN")


@app.get("/widget", response_class=HTMLResponse)
async def widget_page():
    if not WIDGET_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="Widget HTML file not found")
    return HTMLResponse(WIDGET_HTML_PATH.read_text(encoding="utf-8"))


@app.get("/")
async def root():
    return {"message": "Hospilot widget backend is running", "widget_url": "/widget"}


@app.post("/login")
async def login(body: LoginRequest):
    """Login to Hospilot and return the JSON response (token + user).

    By default this uses the environment variables `HOSPILOT_USERNAME` and
    `HOSPILOT_PASSWORD`. You may optionally POST a body with `username` and
    `password` for testing.
    """
    username = body.username or os.environ.get("HOSPILOT_USERNAME")
    password = body.password or os.environ.get("HOSPILOT_PASSWORD")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing Hospilot credentials")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Network error contacting Hospilot: {exc}")

    if r.status_code != 200:
        raise HTTPException(status_code= r.status_code, detail=r.text)

    data = r.json()

    global _LAST_TOKEN
    _LAST_TOKEN = data.get("token")

    return data


@app.post("/sessions")
async def create_session(req: SessionRequest, authorization: Optional[str] = Header(None)):
    """Create a Hospilot session (mission).

    The client should send `Authorization: Bearer <token>` as returned by `/login`.
    If no header is provided, the server will attempt to use the `HOSPILOT_TOKEN`
    environment variable.
    """
    token = resolve_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Hospilot token; call /login first or set HOSPILOT_TOKEN")

    payload = {"goal": req.goal, "constraints": req.constraints or "", "autonomous": req.autonomous}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(f"{BASE_URL}/api/sessions", json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Network error contacting Hospilot: {exc}")

    if r.status_code not in (200, 201):
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


@app.get("/sessions/{session_id}")
async def get_session(session_id: str, authorization: Optional[str] = Header(None)):
    """Poll a Hospilot session by ID and return the raw session object."""
    token = resolve_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Hospilot token; call /login first or set HOSPILOT_TOKEN")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(f"{BASE_URL}/api/sessions/{session_id}", headers=headers)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Network error contacting Hospilot: {exc}")

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
