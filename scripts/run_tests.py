#!/usr/bin/env python3
"""Run every test_*.py under plugins/ with unittest, by path (the skill directories are not packages).

Usage: python3 scripts/run_tests.py [-v]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    tests = sorted(p for p in (ROOT / "plugins").rglob("test_*.py") if "node_modules" not in p.parts)
    if not tests:
        print("no tests found")
        return 1
    print(f"running {len(tests)} test files")
    cmd = [sys.executable, "-m", "unittest", *sys.argv[1:], *[str(t.relative_to(ROOT)) for t in tests]]
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
