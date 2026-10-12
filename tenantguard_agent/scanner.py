"""Security scanner — takes a public git repo URL, or pasted code / .env / config,
and statically scans it for security issues. It READS files only; it never runs,
builds, installs, or imports the scanned code (safe on untrusted input).

Findings: leaked secrets, dangerous configuration, and access-control red flags,
each with file, line, severity, redacted evidence, and a recommendation.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

MAX_FILE_BYTES = 400_000
MAX_FILES = 3000
MAX_TOTAL_BYTES = 60_000_000
CLONE_TIMEOUT = 40

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "dist", "build", "__pycache__",
             ".next", ".nuxt", "vendor", ".idea", ".vscode", "coverage", "target"}
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".env", ".json", ".yaml",
            ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".txt", ".md", ".go",
            ".rb", ".php", ".java", ".cs", ".sh", ".bash", ".tf", ".tfvars", ".xml", ".html",
            ".sql", ".pl", ".kt", ".swift", ".c", ".cpp", ".rs", ".vue", ".svelte", ""}

_URL_OK = re.compile(r"^https://(www\.)?(github|gitlab|bitbucket)\.com/[\w.\-]+/[\w.\-]+/?$", re.I)


def valid_repo_url(url: str) -> bool:
    return bool(_URL_OK.match((url or "").strip().rstrip("/")) )


def redact(s: str, keep: int = 4) -> str:
    s = s.strip().strip("'\"")
    if len(s) <= keep + 2:
        return "***"
    return s[:keep] + "…" + "*" * 6


# ---- detectors -------------------------------------------------------------
# (category, severity, title, compiled regex, recommendation)
def _c(p):
    return re.compile(p)


SECRET_RULES = [
    ("secret", "critical", "AWS access key id", _c(r"AKIA[0-9A-Z]{16}"),
     "Rotate this AWS key immediately and remove it from the code; use env vars / a secrets manager."),
    ("secret", "critical", "Private key", _c(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
     "Remove the private key from the repo and rotate it; store keys outside version control."),
    ("secret", "critical", "Anthropic API key", _c(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
     "Rotate the key and load it from an environment variable."),
    ("secret", "critical", "OpenAI API key", _c(r"sk-[A-Za-z0-9]{20,}"),
     "Rotate the key and load it from an environment variable."),
    ("secret", "critical", "GitHub token", _c(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"),
     "Revoke the token in GitHub settings and use an env var / secret."),
    ("secret", "high", "Slack token", _c(r"xox[baprs]-[0-9A-Za-z\-]{10,}"),
     "Revoke the Slack token and store it as a secret."),
    ("secret", "high", "Google API key", _c(r"AIza[0-9A-Za-z_\-]{35}"),
     "Restrict/rotate the key and move it to a secret store."),
    ("secret", "high", "JWT", _c(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
     "Do not commit tokens; treat as sensitive and rotate if real."),
    ("secret", "high", "DB connection string with password", _c(r"(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s'\"]+:[^\s'\"@]+@"),
     "Move credentials out of the URL into secrets; rotate the password."),
    ("secret", "high", "Hardcoded password/secret assignment",
     _c(r"(?i)(?:password|passwd|secret|api[_\-]?key|access[_\-]?token|client[_\-]?secret)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
     "Load this from an environment variable, not a literal in code."),
]

SECURITY_RULES = [
    ("config", "high", "Debug mode enabled",
     _c(r"(?i)(debug\s*=\s*true|app\.run\([^)]*debug\s*=\s*true|FLASK_DEBUG\s*=\s*1)"),
     "Never run with debug enabled in production — it can leak stack traces and allow code execution."),
    ("config", "high", "TLS/cert verification disabled",
     _c(r"(?i)(verify\s*=\s*false|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true|CURLOPT_SSL_VERIFYPEER\s*,\s*0)"),
     "Do not disable certificate verification — it enables man-in-the-middle attacks."),
    ("config", "medium", "Wide-open CORS (*)",
     _c(r"(?i)(access-control-allow-origin['\"]?\s*[:=,]\s*['\"]?\*|allow_origins\s*=\s*\[\s*['\"]\*['\"]|origin\s*:\s*['\"]\*['\"])"),
     "Restrict CORS to specific trusted origins instead of '*'."),
    ("injection", "high", "Possible SQL injection (string-built query)",
     _c(r"(?i)(?:execute|cursor\.execute|\.query)\s*\(.*(?:select|insert|update|delete).*(?:\+|%\s|\.format\(|f['\"])"),
     "Use parameterized queries / prepared statements, never string concatenation."),
    ("injection", "high", "Command execution from a variable",
     _c(r"(?i)(os\.system|subprocess\.(?:call|run|Popen)\s*\([^)]*\+|child_process\.exec\s*\(|exec\s*\(|eval\s*\()"),
     "Avoid building shell/command strings from input; use safe APIs with arg lists."),
    ("authz", "medium", "Object fetched by id with no visible ownership/tenant check",
     _c(r"(?i)(find(?:One|ById)?\(\s*(?:req|request)\.(?:params|query|body)|get\(\s*(?:request|req)\.(?:args|params)|objects\.get\(\s*(?:pk|id)\s*=)"),
     "Verify the current user owns / shares a tenant with this record before returning it (prevents IDOR)."),
    ("config", "medium", "Committed .env file",
     _c(r"$never$"),  # handled specially by filename
     "Never commit real .env files; add .env to .gitignore and rotate anything inside."),
]


# ---- file walking ----------------------------------------------------------
def _is_text(name: str) -> bool:
    ext = os.path.splitext(name)[1].lower()
    return ext in TEXT_EXT


def iter_files(root: str):
    total = 0
    count = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if count >= MAX_FILES or total >= MAX_TOTAL_BYTES:
                return
            if not _is_text(fn):
                continue
            path = os.path.join(dp, fn)
            try:
                sz = os.path.getsize(path)
                if sz > MAX_FILE_BYTES:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            total += sz
            count += 1
            yield os.path.relpath(path, root).replace(os.sep, "/"), content


# ---- scanning --------------------------------------------------------------
def scan_text(relpath: str, content: str):
    findings = []
    base = os.path.basename(relpath).lower()
    is_example = any(x in base for x in (".example", ".sample", ".template", ".dist"))

    # committed real .env
    if base == ".env" and not is_example:
        findings.append(dict(file=relpath, line=1, severity="high", category="config",
                             title="Committed .env file",
                             evidence="(a real .env is tracked)",
                             recommendation="Never commit real .env files; add .env to .gitignore and rotate anything inside."))

    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if len(line) > 1000:
            line = line[:1000]
        for cat, sev, title, rx, rec in SECRET_RULES:
            m = rx.search(line)
            if m:
                # skip obvious placeholders
                val = m.group(0)
                if re.search(r"(?i)your[_-]?key|example|placeholder|xxxx|<[^>]+>|\.\.\.|changeme|dummy", line):
                    continue
                findings.append(dict(file=relpath, line=i, severity=sev, category=cat, title=title,
                                     evidence=redact(val), recommendation=rec))
        if not is_example:
            for cat, sev, title, rx, rec in SECURITY_RULES:
                if title == "Committed .env file":
                    continue
                if rx.search(line):
                    findings.append(dict(file=relpath, line=i, severity=sev, category=cat, title=title,
                                         evidence=line.strip()[:160], recommendation=rec))
    return findings


def clone_repo(url: str) -> str:
    if not valid_repo_url(url):
        raise ValueError("Please provide a public https GitHub/GitLab/Bitbucket repo URL.")
    tmp = tempfile.mkdtemp(prefix="scan_")
    dst = os.path.join(tmp, "repo")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="echo")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", url.strip(), dst],
            check=True, capture_output=True, text=True, timeout=CLONE_TIMEOUT, env=env,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError("Cloning timed out — is the repo public and not too large?")
    except subprocess.CalledProcessError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError("Could not clone — check the URL is a PUBLIC repo.")
    return tmp


def severity_rank(s: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(s, 4)
