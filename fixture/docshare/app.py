"""DocShare — a file-sharing API with a planted path traversal vulnerability.

Each user has a personal folder under 'storage/'. The download endpoint is
supposed to serve files only from the requesting user's folder — but it
joins the query-parameter path without sanitizing directory traversal.
"""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse

DOCS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")

_USERS = {
    "tok-alice": {"id": "alice", "folder": "alice"},
    "tok-bob": {"id": "bob", "folder": "bob"},
}


def create_app():
    app = FastAPI(title="DocShare (fixture)")

    def current_user(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = authorization.split(" ", 1)[1]
        user = _USERS.get(token)
        if not user:
            raise HTTPException(status_code=401, detail="invalid token")
        return user

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/files")
    def get_file(path: str = Query(...), user=Depends(current_user)):
        # SECURITY BUG (path traversal):
        # the path query parameter is joined directly without sanitization,
        # allowing ../../ to escape the user's directory and read
        # arbitrary files on the server.
        target = os.path.join(DOCS_ROOT, user["folder"], path)
        if not os.path.isfile(target):
            raise HTTPException(status_code=404, detail="file not found")
        return PlainTextResponse(open(target, encoding="utf-8").read())

    return app


app = create_app()
