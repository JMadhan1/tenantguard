"""Verify neatlogs traces via the public REST API.

Docs: https://docs.neatlogs.com/api-reference/quickstart

This uses a SERVICE-ACCOUNT token, which is DIFFERENT from the SDK's
NEATLOGS_API_KEY (that one sends traces; this one reads them). Add to .env:

    NEATLOGS_TOKEN=<service-account token>
    NEATLOGS_PROJECT_ID=<project uuid>

    python scripts/neatlogs_check.py

Prints the project and your most recent traces so you can confirm a live run
landed and copy trace references for the submission.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import httpx

BASE = "https://app.neatlogs.com/api/v1/public"


def main():
    token = os.environ.get("NEATLOGS_TOKEN")
    project = os.environ.get("NEATLOGS_PROJECT_ID")
    if not token or not project:
        print("Set NEATLOGS_TOKEN (service-account token) and NEATLOGS_PROJECT_ID in .env.")
        print("Get them from app.neatlogs.com (service accounts / project settings).")
        return 1

    headers = {"Authorization": f"Bearer {token}", "x-project-id": project}
    with httpx.Client(timeout=20) as client:
        try:
            proj = client.get(f"{BASE}/project", headers=headers)
        except httpx.HTTPError as e:
            print(f"request failed: {e}")
            return 1
        print(f"[project]  HTTP {proj.status_code}")
        print(proj.text[:400])
        if proj.status_code != 200:
            print("\nCheck the token and project id (and that the service account has access).")
            return 1

        traces = client.get(f"{BASE}/traces", headers=headers, params={"limit": 5})
        print(f"\n[recent traces]  HTTP {traces.status_code}")
        print(traces.text[:2000])
        print("\nneatlogs REST check OK — traces are reachable via the public API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
