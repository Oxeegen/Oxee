#!/usr/bin/env python3
"""Fail if an upstream merge dropped part of the Oxee brand layer.

Checks, without needing Flutter:
  * brand/tools/rebrand.py has nothing left to rewrite;
  * every hook in upstream files is still there (and what it removed is
    still gone);
  * the regions in lib/brand/oxee_brand.dart match brand/brand.json;
  * upstream's release workflow cannot run in this repository.

    python brand/tools/check_brand.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# file -> (must contain, must not contain)
HOOKS: dict[str, tuple[list[str], list[str]]] = {
    "lib/core/router/app_router.dart": (
        ["_buildPlatformPage(state: state, child: const OxeeRegionPage())",
         "initialRegion: state.extra is OxeeRegion"],
        ["const BackendChooserPage()", "const ConnectAndSignInPage()"],
    ),
    "lib/features/profile/views/profile_page.dart": (
        ["showOxeeRegionSwitcher(context, ref)"],
        ["RouteNames.hermesSettings", "RouteNames.directConnections", "_buildDonationSection", "cogwheel0"],
    ),
    "lib/features/navigation/widgets/sidebar_user_pill.dart": (
        ["buildOxeeRegionNativeSheetItem(context: context, ref: ref)"],
        ["buy-me-a-coffee", "github-sponsors", "id: NativeSheetRoutes.hermes,", "'add-owui-server'"],
    ),
    "lib/main.dart": (
        ["event.id == oxeeRegionNativeSheetItemId"],
        ["ReleaseNotesCoordinator("],
    ),
    "lib/core/services/native_sheet_hydration_service.dart": (
        [],
        ["id: NativeSheetRoutes.releaseNotesManual", "github.com/cogwheel0"],
    ),
    "lib/features/profile/views/about_page.dart": (
        [],
        ["_openReleaseNotes", "github.com/cogwheel0"],
    ),
    ".github/workflows/release.yml": (
        ["if: github.repository == 'cogwheel0/conduit'"],
        [],
    ),
    ".github/workflows/ci.yml": (
        ["python3 brand/tools/flutter_test.py", "python3 brand/tools/check_brand.py"],
        [],
    ),
}

MUST_NOT_EXIST = [".github/FUNDING.yml"]


def main() -> int:
    problems: list[str] = []

    rebrand = subprocess.run(
        [sys.executable, str(ROOT / "brand/tools/rebrand.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if rebrand.returncode != 0:
        problems.append("rebrand.py --check:\n" + rebrand.stdout + rebrand.stderr)

    for rel, (present, absent) in HOOKS.items():
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in present:
            if needle not in text:
                problems.append(f"{rel}: brand hook lost, expected {needle!r}")
        for needle in absent:
            if needle in text:
                problems.append(f"{rel}: upstream code the brand removes is back: {needle!r}")

    for rel in MUST_NOT_EXIST:
        if (ROOT / rel).exists():
            problems.append(f"{rel}: must not exist in Oxee")

    brand = json.loads((ROOT / "brand/brand.json").read_text(encoding="utf-8"))
    dart = (ROOT / "lib/brand/oxee_brand.dart").read_text(encoding="utf-8")
    declared = {
        m.group(1): (m.group(2), m.group(3))
        for m in re.finditer(r"^\s*(\w+)\(label: '([^']+)', url: '([^']+)'", dart, re.M)
    }
    expected = {k: (v["label"], v["url"]) for k, v in brand["regions"].items()}
    if declared != expected:
        problems.append(f"regions differ: oxee_brand.dart {declared} vs brand.json {expected}")

    if problems:
        print("Oxee brand check failed:\n")
        for problem in problems:
            print(" - " + problem)
        return 1
    print(f"Oxee brand check passed ({len(HOOKS)} hooked files, regions {sorted(expected)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
