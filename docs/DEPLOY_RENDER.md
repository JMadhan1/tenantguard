# Deploy the TenantGuard live app (Render) + point tenantguard.jmadhan.me at it

The live app (`server/`) streams the **real** agent (Claude Opus 4.6 on AWS Bedrock, traced in
neatlogs) over SSE, on the built-in fixture case only. Static hosting can't run it — use Render.

## 1. Create the service
1. **render.com → New → Blueprint** → connect GitHub → select **JMadhan1/tenantguard**.
2. Render reads `render.yaml` and creates the **tenantguard** web service (free plan).

## 2. Set the secret env vars
Render dashboard → the service → **Environment** → add (these are `sync: false` in the blueprint):
- `AWS_ACCESS_KEY_ID` = your key
- `AWS_SECRET_ACCESS_KEY` = your secret
- `NEATLOGS_API_KEY` = your neatlogs key

(`AWS_REGION=ap-south-1`, `TENANTGUARD_MODEL`, and the caps are already preset in `render.yaml`.)
Deploy → you get `https://tenantguard.onrender.com`.

## 3. Verify it's running **real**
- Open it → click **Run TenantGuard live**.
- The status line should read **“Live · Claude Opus 4.6 on AWS Bedrock”**, the run streams real phases,
  and the verdict shows a **cost/fix** and **neatlogs traced: yes**. Confirm a new trace in your neatlogs dashboard.
- Without creds it still works in **replay mode** (scripted, free) — useful as a safe fallback.

## 4. Make it the one place — point tenantguard.jmadhan.me at Render
The domain currently serves the Vercel static site. To move it to the live app:
1. **Vercel** → the project serving the domain → **Settings → Domains → remove** `tenantguard.jmadhan.me`.
2. **Render** → service → **Settings → Custom Domains → Add** `tenantguard.jmadhan.me` → Render shows a CNAME target.
3. **Vercel → Domains → jmadhan.me → DNS** → add a **CNAME**: name `tenantguard` → value = Render's target.
4. Render verifies and issues SSL (a few minutes). Done — the live app is now at `https://tenantguard.jmadhan.me`.

## Guardrails & caveats (important for a public endpoint)
- **Cost:** the daily live cap (`TENANTGUARD_DAILY_LIVE_CAP`, default 100) + per-IP cooldown bound your AWS spend. Lower the cap if you like.
- Use a **minimal-privilege IAM user** (Bedrock `InvokeModel` only) for these creds, and set an **AWS billing alert**.
- **Cold start:** the free tier sleeps after ~15 min idle; the first visit takes ~30–60s. **Warm it** (load the page once) before a demo or judging.
- Only the allowlisted fixture case runs — never visitor code.
