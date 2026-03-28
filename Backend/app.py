from urllib.parse import urljoin

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

app = FastAPI()
FRONTEND_URL = os.getenv("MVS_FRONTEND_URL", "https://machine-vision-camera.onrender.com/")
if not FRONTEND_URL.endswith("/"):
    FRONTEND_URL = f"{FRONTEND_URL}/"


# ----------------------------
# Health API
# ----------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def serve_frontend_root():
    return RedirectResponse(url=FRONTEND_URL)


@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    return RedirectResponse(url=urljoin(FRONTEND_URL, full_path))
