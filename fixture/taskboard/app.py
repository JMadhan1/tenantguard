"""TaskBoard — a task-search API with a planted SQL injection vulnerability.

Each user belongs to a team and can search tasks within their team.
The search endpoint builds the SQL query by string concatenation — the bug
TenantGuard is asked to fix.
"""

from __future__ import annotations

import sqlite3

from fastapi import Depends, FastAPI, Header, HTTPException, Query


def create_app():
    app = FastAPI(title="TaskBoard (fixture)")

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            team TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL
        );
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            team TEXT NOT NULL,
            created_by TEXT NOT NULL,
            done INTEGER DEFAULT 0
        );
        INSERT INTO users VALUES ('alice', 'engineering', 'tok-alice');
        INSERT INTO users VALUES ('bob',   'engineering', 'tok-bob');
        INSERT INTO users VALUES ('carol', 'marketing',   'tok-carol');

        INSERT INTO tasks VALUES ('task-1', 'Fix login bug',       'engineering', 'alice', 0);
        INSERT INTO tasks VALUES ('task-2', 'Deploy v2.0-rc1',     'engineering', 'bob',   0);
        INSERT INTO tasks VALUES ('task-3', 'Update homepage copy', 'marketing',  'carol', 1);
        INSERT INTO tasks VALUES ('task-4', 'Write Q3 report',     'marketing',  'carol', 0);
    """)

    def current_user(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = authorization.split(" ", 1)[1]
        row = conn.execute(
            "SELECT id, team FROM users WHERE token = ?", (token,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="invalid token")
        return dict(row)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/tasks")
    def search_tasks(q: str = Query(""), user=Depends(current_user)):
        # SECURITY BUG (SQL injection):
        # The query string is unsafely interpolated into raw SQL,
        # allowing attackers to inject arbitrary statements.
        team = user["team"]
        sql = "SELECT * FROM tasks WHERE team = '" + team + "' AND title LIKE '%" + q + "%'"
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    return app


app = create_app()
