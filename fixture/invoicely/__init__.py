"""Invoicely — a tiny synthetic multi-tenant invoice API used as TenantGuard's
remediation target. It ships with ONE planted defect: the invoice-read endpoint
is missing a tenant-authorization check (an IDOR / broken-object-level-auth bug).

All data here is synthetic. This package is the *fixture* and is kept separate
from the remediation agent. The agent only ever edits a disposable worktree copy.
"""
