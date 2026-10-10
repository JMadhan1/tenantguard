# TenantGuard — safety boundaries

These are enforced in code, not just by convention.

- **Disposable worktree only.** The agent edits a temp copy of the allowlisted fixture repo. The original fixture is never mutated; the agent produces a `patch.diff` artifact and never commits, pushes, or opens a PR autonomously.
- **Allowlisted cases only.** Runs accept only known `case_id`s. No arbitrary repository URLs.
- **No LLM-generated shell.** The model never produces shell strings for execution. Tools are deterministic Python with validated arguments and structured results.
- **Tests run sandboxed.** The test runner executes in an isolated subprocess with path restriction, output-size caps, and CPU/memory/time limits (and, when Docker is available, in a no-network container). Binding the fixture to localhost does not make arbitrary code safe.
- **Patch-scope guard.** A fix is rejected if it touches files outside the allowed set, deletes or weakens tests, or hardcodes fixture IDs.
- **Deterministic verifier owns success.** "Fixed" requires BOTH the security assertions AND the legitimate-access functionality tests to pass. Passing the exploit test alone is not success.
- **Honest outcomes.** Exhausted budget / ambiguous result → a human-review report, never a "fixed" claim.
- **Untrusted evidence.** Repository text, comments, and bug reports are treated as data, never as instructions.
- **No secrets in code, traces, checkpoints, or screenshots.** All fixture data is synthetic.
- **Bounded budget.** Max patch revisions, bounded model calls, and a total run timeout. Live-model spend cap is confirmed with the operator before real calls.
