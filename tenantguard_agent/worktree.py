"""Disposable worktree + sandboxed test runner + patch-scope guard.

The agent only ever touches a temp copy of the fixture. Edits are restricted to
the case's allowed paths; test files cannot be modified (anti-cheat); tests run
in a bounded subprocess with an output cap.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

from .cases import Case

MAX_OUTPUT = 20_000
TEST_TIMEOUT = 60


@dataclass
class TestOutcome:
    passed: list            # function names
    failed: list            # function names
    digest: str             # short failure text for the model

    def names(self):
        return set(self.passed) | set(self.failed)


class Worktree:
    def __init__(self, case: Case):
        self.case = case
        self.root = tempfile.mkdtemp(prefix="tenantguard_")
        self.repo = os.path.join(self.root, "repo")
        shutil.copytree(case.fixture_src, self.repo)
        self._history: dict[str, list[str]] = {}
        # snapshot test files to detect tampering
        self._test_fingerprint = self._fingerprint_tests()

    # ---- safety helpers --------------------------------------------------
    def _abs(self, rel: str) -> str:
        p = os.path.normpath(os.path.join(self.repo, rel))
        if not p.startswith(self.repo):
            raise ValueError(f"path escapes worktree: {rel}")
        return p

    def _is_test_path(self, rel: str) -> bool:
        norm = rel.replace("\\", "/")
        return norm.startswith(f"{self.case.test_dir}/") or "/tests/" in norm or norm == "conftest.py"

    def _fingerprint_tests(self) -> dict:
        fp = {}
        tdir = os.path.join(self.repo, self.case.test_dir)
        for dp, _, fns in os.walk(tdir):
            for fn in fns:
                if fn.endswith(".py"):
                    p = os.path.join(dp, fn)
                    fp[os.path.relpath(p, self.repo)] = open(p, encoding="utf-8").read()
        return fp

    def tests_untampered(self) -> bool:
        return self._fingerprint_tests() == self._test_fingerprint

    # ---- read tools ------------------------------------------------------
    def list_files(self) -> list:
        out = []
        for dp, dns, fns in os.walk(self.repo):
            dns[:] = [d for d in dns if d not in {"__pycache__", ".pytest_cache", ".git"}]
            for fn in fns:
                if fn.endswith(".pyc"):
                    continue
                out.append(os.path.relpath(os.path.join(dp, fn), self.repo).replace(os.sep, "/"))
        return sorted(out)

    def read_file(self, rel: str) -> str:
        return open(self._abs(rel), encoding="utf-8").read()

    def search_code(self, pattern: str) -> list:
        import re
        rx = re.compile(pattern)
        hits = []
        for rel in self.list_files():
            if not rel.endswith(".py"):
                continue
            for i, line in enumerate(self.read_file(rel).splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{rel}:{i}: {line.strip()}")
        return hits

    # ---- write tools (scope-guarded) ------------------------------------
    def _check_editable(self, rel: str):
        norm = rel.replace("\\", "/")
        if self._is_test_path(norm):
            raise PermissionError(f"editing test files is forbidden: {rel}")
        if norm not in self.case.allowed_edit_paths:
            raise PermissionError(
                f"path '{rel}' is outside the allowed edit scope {self.case.allowed_edit_paths}"
            )

    def _snapshot(self, rel: str):
        abs_p = self._abs(rel)
        cur = open(abs_p, encoding="utf-8").read() if os.path.exists(abs_p) else ""
        self._history.setdefault(rel, []).append(cur)

    def apply_patch(self, rel: str, old: str, new: str) -> str:
        self._check_editable(rel)
        content = self.read_file(rel)
        n = content.count(old)
        if n == 0:
            raise ValueError(f"`old` not found in {rel}; re-read the file and copy exact text.")
        if n > 1:
            raise ValueError(f"`old` not unique in {rel} ({n} matches); add more context.")
        self._snapshot(rel)
        with open(self._abs(rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace(old, new, 1))
        return f"patched {rel}"

    def revert(self, rel: str) -> str:
        hist = self._history.get(rel)
        if not hist:
            return f"nothing to revert for {rel}"
        prev = hist.pop()
        with open(self._abs(rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(prev)
        return f"reverted {rel}"

    # ---- test runner (sandboxed) ----------------------------------------
    def run_tests(self) -> TestOutcome:
        junit = os.path.join(self.root, "junit.xml")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--no-header",
                 "-p", "no:cacheprovider", f"--junitxml={junit}"],
                cwd=self.repo, capture_output=True, text=True, timeout=TEST_TIMEOUT,
            )
            raw = (proc.stdout + "\n" + proc.stderr)[:MAX_OUTPUT]
        except subprocess.TimeoutExpired:
            return TestOutcome(passed=[], failed=["<timeout>"], digest="test run timed out")
        passed, failed = self._parse_junit(junit)
        return TestOutcome(passed=passed, failed=failed, digest=self._digest(raw))

    @staticmethod
    def _parse_junit(path: str):
        import xml.etree.ElementTree as ET
        passed, failed = [], []
        if not os.path.exists(path):
            return passed, failed
        for case in ET.parse(path).iter("testcase"):
            name = case.get("name", "")
            is_fail = any(c.tag in ("failure", "error") for c in case)
            (failed if is_fail else passed).append(name)
        return passed, failed

    @staticmethod
    def _digest(raw: str) -> str:
        lines = raw.splitlines()
        keep, cap = [], False
        for ln in lines:
            if "short test summary info" in ln:
                cap = True
            if cap:
                keep.append(ln)
        return "\n".join(keep or lines[-15:]).strip()

    # ---- artifacts -------------------------------------------------------
    def diff(self) -> str:
        import difflib
        chunks = []
        for rel in self.case.allowed_edit_paths:
            src = os.path.join(self.case.fixture_src, rel)
            dst = self._abs(rel)
            if not (os.path.exists(src) and os.path.exists(dst)):
                continue
            a = open(src, encoding="utf-8").read().splitlines(keepends=True)
            b = open(dst, encoding="utf-8").read().splitlines(keepends=True)
            if a != b:
                chunks.extend(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}"))
        return "".join(chunks)

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)
