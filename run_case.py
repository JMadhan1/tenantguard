"""Run a TenantGuard remediation case.

    python run_case.py                     # offline (no API key): naive fix → recovery → fixed
    python run_case.py --correct-first     # offline, fixes correctly on the first try
    python run_case.py --live              # real Claude run (needs ANTHROPIC_API_KEY)
    python run_case.py --live --model claude-haiku-5-5
"""

import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from tenantguard_agent.runner import run_case


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id", nargs="?", default="invoicely-idor-001")
    ap.add_argument("--live", action="store_true", help="use a real Claude model")
    ap.add_argument("--model", default=None)
    ap.add_argument("--quality", choices=["baseline", "improved"], default="improved",
                    help="live prompt quality for the before/after comparison")
    ap.add_argument("--correct-first", action="store_true",
                    help="offline brain fixes correctly on attempt 1 (no recovery demo)")
    ap.add_argument("--max-attempts", type=int, default=3)
    args = ap.parse_args()

    final = run_case(
        args.case_id,
        offline=not args.live,
        model=args.model,
        quality=args.quality,
        naive_first=not args.correct_first,
        max_attempts=args.max_attempts,
    )

    v = final.get("verdict", {})
    print(f"\n=== TenantGuard: {args.case_id} ===")
    print(f"brain:        {getattr(final.get('brain'), 'kind', '?')}")
    print(f"status:       {final.get('status')}")
    print(f"attempts:     {final.get('attempt')}")
    print(f"baseline:     {len(final.get('baseline_passed', []))} passed / {len(final.get('baseline_failed', []))} failed")
    print(f"verdict:      {v.get('status')} (security={v.get('security_pass')}, functionality={v.get('functionality_pass')})")
    if v.get("security_fixed"):
        print(f"security fixed: {v['security_fixed']}")
    print(f"artifacts:    {final.get('artifact_dir')}")
    print("\n--- phase timeline ---")
    for e in final.get("events", []):
        print(f"  {e['phase']:<24} {e['detail']}")
    return 0 if final.get("status") == "fixed" else 1


if __name__ == "__main__":
    sys.exit(main())
