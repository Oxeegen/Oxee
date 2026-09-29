#!/usr/bin/env python3
"""Run the app's Flutter tests minus the upstream files Oxee replaces.

The skipped files are listed, with a reason each, in
brand/upstream-tests-replaced.txt. Extra arguments go to `flutter test`.

    python brand/tools/flutter_test.py
    python brand/tools/flutter_test.py --reporter expanded
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPLACED = ROOT / "brand" / "upstream-tests-replaced.txt"
# Windows caps a command line at 32k characters; run in batches below that.
BATCH_CHARS = 24_000


def replaced_tests() -> set[str]:
    listed = set()
    for raw in REPLACED.read_text(encoding="utf-8").splitlines():
        path = raw.split("#", 1)[0].strip()
        if path:
            listed.add(path)
    missing = sorted(p for p in listed if not (ROOT / p).is_file())
    if missing:
        raise SystemExit(
            "brand/upstream-tests-replaced.txt lists files that no longer exist:\n  "
            + "\n  ".join(missing)
        )
    return listed


def main() -> int:
    skip = replaced_tests()
    tests = sorted(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "test").rglob("*_test.dart")
        if p.relative_to(ROOT).as_posix() not in skip
    )
    flutter = shutil.which("flutter") or "flutter"
    print(f"flutter test: {len(tests)} files, {len(skip)} replaced upstream file(s) skipped")

    batches: list[list[str]] = [[]]
    size = 0
    for test in tests:
        if size + len(test) > BATCH_CHARS and batches[-1]:
            batches.append([])
            size = 0
        batches[-1].append(test)
        size += len(test) + 1

    status = 0
    for batch in batches:
        result = subprocess.run([flutter, "test", *sys.argv[1:], *batch], cwd=ROOT)
        status = status or result.returncode
    return status


if __name__ == "__main__":
    sys.exit(main())
