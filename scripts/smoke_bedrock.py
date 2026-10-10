"""Minimal AWS Bedrock connectivity check — one tiny (~20 token) call.

Run this FIRST after pasting your AWS keys into .env, to confirm creds /
region / model before the full agent run:

    python scripts/smoke_bedrock.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from tenantguard_agent.brain import _base_client, detect_backend

backend = detect_backend()
model = os.environ.get("TENANTGUARD_MODEL", "global.anthropic.claude-opus-4-6-v1")
print(f"backend={backend}  region={os.environ.get('AWS_REGION')}  model={model}")

if backend != "bedrock":
    print("AWS keys not detected in .env — set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.")
    sys.exit(1)

client = _base_client("bedrock")
try:
    resp = client.messages.create(
        model=model, max_tokens=20,
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
    print("model replied:", text.strip())
    print("usage:", resp.usage)
    print("\nBEDROCK OK - credentials, region and model all work.")
except Exception as e:
    print(f"\nBEDROCK CALL FAILED: {type(e).__name__}: {e}")
    print("Check: keys correct, model access enabled in Bedrock console for ap-south-1, "
          "and the model id matches an inference profile you can invoke.")
    sys.exit(1)
