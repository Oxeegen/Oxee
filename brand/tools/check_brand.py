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
         "initialRegion: state.extra is OxeeRegion",
         "child: OxeeRegionPage(\n          addingAccount: true,"],
        ["const BackendChooserPage()", "const ConnectAndSignInPage()",
         "ServerConnectionPage(\n          addingAccount: true,"],
    ),
    "lib/features/profile/views/profile_page.dart": (
        ["key: const Key('oxee-region-entry')", "showOxeeRegionSwitcher(context, ref)"],
        ["_buildDonationSection", "cogwheel0", "launchExternalLink"],
    ),
    "lib/features/profile/widgets/account_sheet.dart": (
        ["OxeeStrings.of(context).accountKindTitle",
         "if (oxeeOffersOtherBackends || _kind == AccountKind.direct)",
         ": OxeeRegionAddChoices(close: close)"],
        [],
    ),
    "lib/features/profile/views/manage_accounts_page.dart": (
        ["if (oxeeOffersOtherBackends) ...[\n          const _DirectCard(),"],
        [],
    ),
    "lib/features/navigation/widgets/sidebar_user_pill.dart": (
        ["oxeeNativeRootSections(", "buildOxeeRegionNativeSheetItem(context, ref.read)"],
        ["supportItems: supportItems", "supportTitle: l10n.supportConduit", "buy-me-a-coffee"],
    ),
    "lib/core/services/native_sheet_hydration_service.dart": (
        ["oxeeNativeAccountsDetail(buildNativeAccountsDetail(",
         "items: oxeeNativeAboutItems(",
         "region: buildOxeeRegionNativeSheetItem(ctx, _ref.read)"],
        [],
    ),
    "lib/main.dart": (
        ["event.id == oxeeRegionNativeSheetItemId", "...oxeeProviderOverrides,"],
        ["ReleaseNotesCoordinator("],
    ),
    "lib/brand/oxee_brand.dart": (
        ["libreChatBackendEnabledProvider.overrideWithValue(false)"],
        [],
    ),
    "lib/core/utils/native_sheet_utils.dart": (
        [],
        ["github.com/cogwheel0/conduit"],
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
        ["- run: dart run tool/run_test_shards.dart"],
    ),
}

# Upstream's donation links and its Pullfrog agent workflow (manual runs
# with upstream's AI provider keys) have no place in Oxee.
MUST_NOT_EXIST = [".github/FUNDING.yml", ".github/workflows/pullfrog.yml"]


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
