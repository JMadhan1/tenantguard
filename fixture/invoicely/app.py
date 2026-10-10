"""Invoicely FastAPI app.

Intended authorization rule: an authenticated user may read any invoice that
belongs to THEIR OWN tenant; cross-tenant reads must be refused (403).

This fixture ships with the rule NOT enforced on the read endpoint — the bug
TenantGuard is asked to fix.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException

from .store import seed, user_for_token


def create_app():
    app = FastAPI(title="Invoicely (fixture)")
    data = seed()

    def current_user(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = authorization.split(" ", 1)[1]
        user = user_for_token(data, token)
        if not user:
            raise HTTPException(status_code=401, detail="invalid token")
        return user

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/invoices/{invoice_id}")
    def get_invoice(invoice_id: str, user=Depends(current_user)):
        invoice = data["invoices"].get(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=404, detail="invoice not found")
        # SECURITY BUG (broken object-level authorization / IDOR):
        # the invoice is returned without checking that it belongs to the
        # caller's tenant, so any authenticated user can read any invoice.
        return invoice

    return app


app = create_app()
