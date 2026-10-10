#!/usr/bin/env python3
"""Run the app's Flutter tests minus the upstream files Oxee replaces.

The skipped files are listed, with a reason each, in
brand/upstream-tests-replaced.txt. They are set aside for the run (renamed
to *.oxee-skipped) and always put back, then upstream's own runner,
tool/run_test_shards.dart, runs everything else in a few combined
entrypoints. Extra arguments go to that runner (and from it to
`flutter test`).

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
SHARD_RUNNER = ROOT / "tool" / "run_test_shards.dart"
SUFFIX = ".oxee-skipped"
# Fallback when upstream has no shard runner: plain `flutter test` in batches
# below Windows' 32k command-line limit.
BATCH_CHARS = 24_000


def replaced_tests() -> list[Path]:
    listed = []
    for raw in REPLACED.read_text(encoding="utf-8").splitlines():
        path = raw.split("#", 1)[0].strip()
        if path:
            listed.append(ROOT / path)
    missing = sorted(p.relative_to(ROOT).as_posix() for p in listed if not p.is_file())
    if missing:
        raise SystemExit(
            "brand/upstream-tests-replaced.txt lists files that no longer exist:\n  "
            + "\n  ".join(missing)
        )
    return listed


def run_plain(args: list[str]) -> int:
    flutter = shutil.which("flutter") or "flutter"
    tests = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "test").rglob("*_test.dart"))
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
        status = status or subprocess.run([flutter, "test", *args, *batch], cwd=ROOT).returncode
    return status


def main() -> int:
    skipped = replaced_tests()
    print(f"Oxee: {len(skipped)} replaced upstream test file(s) set aside for this run")
    moved: list[tuple[Path, Path]] = []
    try:
        for test in skipped:
            aside = test.with_name(test.name + SUFFIX)
            test.rename(aside)
            moved.append((aside, test))
        if SHARD_RUNNER.is_file():
            dart = shutil.which("dart") or "dart"
            return subprocess.run([dart, "run", str(SHARD_RUNNER.relative_to(ROOT)), *sys.argv[1:]], cwd=ROOT).returncode
        return run_plain(sys.argv[1:])
    finally:
        for aside, original in moved:
            aside.rename(original)


if __name__ == "__main__":
    sys.exit(main())
