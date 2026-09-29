#!/usr/bin/env python3
"""Oxee brand layer: rewrite Conduit's user-visible branding to Oxee.

Two kinds of rewrite, both idempotent:

* Product name. Every whole-word "Conduit" that a user can see becomes
  "Oxee": text inside string literals in Dart, Swift and Kotlin (comments and
  identifiers are never touched), ARB translation values, iOS .strings and
  Info.plist values, Android resource text and labels, and the display names
  in the Xcode project. Tests get the same treatment so their assertions keep
  matching the strings they check.
* Identity. Bundle identifiers, the app group, the URL scheme, the Apple team
  and the links that point at the upstream project, from brand/brand.json.

Run from the repository root after every upstream merge:

    python brand/tools/rebrand.py           # apply
    python brand/tools/rebrand.py --check   # list files that would change, exit 1

A merge conflict in a line this script owns resolves as "take upstream's side,
then run this script again".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
BRAND = json.loads((ROOT / "brand" / "brand.json").read_text(encoding="utf-8"))

NAME = BRAND["appName"]
UPSTREAM_NAME = BRAND["upstreamAppName"]
BUNDLE_ID = BRAND["bundleId"]
UPSTREAM_BUNDLE_ID = BRAND["upstreamBundleId"]

# Whole word only: "Conduit's" and "Conduit-Chat" match, "ConduitWidget",
# "askConduit" and "conduit_core" do not.
WORD = re.compile(r"(?<![A-Za-z0-9_$])" + UPSTREAM_NAME + r"(?![A-Za-z0-9_])")

# Never rewritten: vendored reference checkouts and generated output.
EXCLUDED_PARTS = {"openwebui-src", "hermes-src", "third_party", "build", ".dart_tool", "Pods", ".git"}
EXCLUDED_SUFFIXES = (".g.dart", ".freezed.dart", ".g.swift", ".mocks.dart")


def rename_word(text: str) -> str:
    return WORD.sub(NAME, text)


# ---------------------------------------------------------------------------
# String-literal scanner for Dart, Swift and Kotlin.
#
# Returns the character ranges that hold literal string text, excluding
# interpolated code (${...}, $name, \(...)), comments and code. Only those
# ranges are rewritten, so identifiers such as `ConduitHaptics` or a class
# named in an interpolation can never change.
# ---------------------------------------------------------------------------


def _is_ident(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


class _Scanner:
    def __init__(self, src: str, lang: str):
        self.src = src
        self.lang = lang
        self.n = len(src)
        self.spans: list[tuple[int, int]] = []

    def run(self) -> list[tuple[int, int]]:
        self.code(0, None)
        return self.spans

    def skip_block_comment(self, i: int) -> int:
        depth = 0
        while i < self.n:
            if self.src.startswith("/*", i):
                depth += 1
                i += 2
            elif self.src.startswith("*/", i):
                depth -= 1
                i += 2
                if depth == 0:
                    return i
            else:
                i += 1
        return i

    def code(self, i: int, closer: str | None) -> int:
        """Scan code until `closer` (unmatched) or EOF; return index after it."""
        src, n = self.src, self.n
        opener = {"}": "{", ")": "("}.get(closer or "", "")
        depth = 0
        while i < n:
            c = src[i]
            if src.startswith("//", i):
                j = src.find("\n", i)
                i = n if j < 0 else j
                continue
            if src.startswith("/*", i):
                i = self.skip_block_comment(i)
                continue
            if closer and c == opener:
                depth += 1
            elif closer and c == closer:
                if depth == 0:
                    return i + 1
                depth -= 1
            start = self.string_start(i)
            if start is not None:
                i = self.string(*start)
                continue
            if self.lang == "kotlin" and c == "'":
                # Char literal: '"' must not open a string.
                j = i + 1
                if j < n and src[j] == "\\":
                    j += 2
                else:
                    j += 1
                while j < n and src[j] != "'" and src[j] != "\n":
                    j += 1
                i = j + 1
                continue
            i += 1
        return i

    def string_start(self, i: int):
        """(content_start, quote, raw, hashes) if a string literal opens at i."""
        src = self.src
        prev = src[i - 1] if i > 0 else ""
        if self.lang == "dart":
            raw = False
            j = i
            if src[i] == "r" and not _is_ident(prev) and i + 1 < self.n and src[i + 1] in "'\"":
                raw = True
                j = i + 1
            elif src[i] not in "'\"":
                return None
            for q in ("'''", '"""', "'", '"'):
                if src.startswith(q, j):
                    return (j + len(q), q, raw, 0)
            return None
        if self.lang == "swift":
            j = i
            hashes = 0
            while j < self.n and src[j] == "#":
                hashes += 1
                j += 1
            if hashes and _is_ident(prev):
                return None
            for q in ('"""', '"'):
                if src.startswith(q, j):
                    return (j + len(q), q, hashes > 0, hashes)
            return None
        # kotlin
        for q in ('"""', '"'):
            if src.startswith(q, i):
                return (i + len(q), q, q == '"""', 0)
        return None

    def string(self, i: int, quote: str, raw: bool, hashes: int) -> int:
        src, n = self.src, self.n
        close = quote + "#" * hashes
        seg = i
        while i < n:
            if src.startswith(close, i):
                self.spans.append((seg, i))
                return i + len(close)
            c = src[i]
            if len(quote) == 1 and c == "\n":
                self.spans.append((seg, i))
                return i
            # Kotlin raw strings still interpolate; Dart and Swift raw strings do not.
            interpolates = not raw or self.lang == "kotlin"
            if c == "\\" and not raw:
                if self.lang == "swift" and src.startswith("\\(", i):
                    self.spans.append((seg, i))
                    i = self.code(i + 2, ")")
                    seg = i
                    continue
                i += 2
                continue
            if c == "$" and interpolates and self.lang in ("dart", "kotlin"):
                if src.startswith("${", i):
                    self.spans.append((seg, i))
                    i = self.code(i + 2, "}")
                    seg = i
                    continue
                if i + 1 < n and (src[i + 1].isalpha() or src[i + 1] == "_"):
                    self.spans.append((seg, i))
                    i += 1
                    while i < n and _is_ident(src[i]):
                        i += 1
                    seg = i
                    continue
            i += 1
        self.spans.append((seg, n))
        return n


def rewrite_string_literals(src: str, lang: str) -> str:
    spans = _Scanner(src, lang).run()
    out = []
    last = 0
    for start, end in sorted(spans):
        if start < last:
            continue
        out.append(src[last:start])
        out.append(rename_word(src[start:end]))
        last = end
    out.append(src[last:])
    return "".join(out)


# ---------------------------------------------------------------------------
# Resource formats
# ---------------------------------------------------------------------------

ARB_ENTRY = re.compile(r'^(  "([^"@][^"]*)": ")(.*)("\s*,?\s*)$')


def rewrite_arb(src: str) -> str:
    """Top-level translation values only; keys and @metadata stay upstream's."""
    lines = src.split("\n")
    for idx, line in enumerate(lines):
        m = ARB_ENTRY.match(line)
        if m:
            lines[idx] = m.group(1) + rename_word(m.group(3)) + m.group(4)
    return "\n".join(lines)


def rewrite_dot_strings(src: str) -> str:
    """Keys too: they are the English source text of the Swift literals."""
    out = []
    for line in src.split("\n"):
        stripped = line.lstrip()
        out.append(line if stripped.startswith(("//", "/*", "*")) else rename_word(line))
    return "\n".join(out)


PLIST_STRING = re.compile(r"(<string>)(.*?)(</string>)", re.S)


def rewrite_plist(src: str) -> str:
    return PLIST_STRING.sub(lambda m: m.group(1) + rename_word(m.group(2)) + m.group(3), src)


XML_COMMENT = re.compile(r"<!--.*?-->", re.S)
XML_TEXT = re.compile(r">([^<]+)<")
XML_ATTR = re.compile(r'(android:(?:label|text|description|contentDescription|title|summary|hint)=")([^"]*)(")')


def rewrite_android_xml(src: str) -> str:
    parts = []
    last = 0
    for m in XML_COMMENT.finditer(src):
        parts.append(_rewrite_xml_segment(src[last:m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(_rewrite_xml_segment(src[last:]))
    return "".join(parts)


def _rewrite_xml_segment(seg: str) -> str:
    seg = XML_TEXT.sub(lambda m: ">" + rename_word(m.group(1)) + "<", seg)
    return XML_ATTR.sub(lambda m: m.group(1) + rename_word(m.group(2)) + m.group(3), seg)


def rewrite_pbxproj(src: str) -> str:
    team = BRAND["appleTeamId"].strip()

    def display_name(m: re.Match) -> str:
        value = m.group(2).strip('"')
        value = {"ConduitWidget": NAME + " Widget", "ShareExtension": NAME}.get(value, rename_word(value))
        quoted = value if re.fullmatch(r"[A-Za-z0-9_.]+", value) else '"' + value + '"'
        return m.group(1) + quoted + ";"

    src = re.sub(r"(INFOPLIST_KEY_CFBundleDisplayName = )([^;]+);", display_name, src)
    src = re.sub(
        r"(PRODUCT_BUNDLE_IDENTIFIER = )" + re.escape(UPSTREAM_BUNDLE_ID) + r"([^;]*);",
        lambda m: m.group(1) + BUNDLE_ID + m.group(2) + ";",
        src,
    )
    src = re.sub(r"(APP_GROUP_ID = )group\.app\.cogwheel\.conduit\.[a-z0-9]+\.debug;", r"\g<1>" + BRAND["debugAppGroupId"] + ";", src)
    src = re.sub(r"(APP_GROUP_ID = )group\.app\.cogwheel\.conduit;", r"\g<1>" + BRAND["appGroupId"] + ";", src)
    src = re.sub(r'(APP_URL_SCHEME = )"conduit-debug";', r'\g<1>"' + BRAND["urlScheme"] + '-debug";', src)
    src = re.sub(r"(APP_URL_SCHEME = )conduit;", r"\g<1>" + BRAND["urlScheme"] + ";", src)
    # Upstream's team, or ours once brand.json names it. Empty means "pass
    # DEVELOPMENT_TEAM on the xcodebuild command line", which CI does.
    src = re.sub(r"(DEVELOPMENT_TEAM = )[^;]*;", lambda m: m.group(1) + (team or '""') + ";", src)
    return src


# ---------------------------------------------------------------------------
# Identity: exact replacements in named files. Each (old, new) pair must be
# found or already applied, so a moved upstream line fails loudly instead of
# silently shipping Conduit's identity.
# ---------------------------------------------------------------------------

IDENTITY: dict[str, list[tuple[str, str]]] = {
    "android/app/build.gradle.kts": [
        ('applicationId = "' + UPSTREAM_BUNDLE_ID + '"', 'applicationId = "' + BUNDLE_ID + '"'),
    ],
    "ios/Runner/Info.plist": [
        ("<string>" + UPSTREAM_BUNDLE_ID + ".share</string>", "<string>" + BUNDLE_ID + ".share</string>"),
        ("<string>" + UPSTREAM_BUNDLE_ID + ".widget</string>", "<string>" + BUNDLE_ID + ".widget</string>"),
    ],
    "ios/ConduitWidget/ConduitWidget.swift": [
        ('return "conduit"', 'return "' + BRAND["urlScheme"] + '"'),
    ],
    "android/app/src/main/kotlin/app/cogwheel/conduit/ConduitWidgetProvider.kt": [
        ('Uri.parse("conduit://', 'Uri.parse("' + BRAND["urlScheme"] + "://"),
    ],
    "lib/platform/home_widget_service.dart": [
        ("'group.app.cogwheel.conduit'", "'" + BRAND["appGroupId"] + "'"),
        ("'group.app.cogwheel.conduit.x2662v5dt2.debug'", "'" + BRAND["debugAppGroupId"] + "'"),
    ],
    "lib/features/profile/views/about_page.dart": [
        ("'https://github.com/cogwheel0/conduit'", "'" + BRAND["repoUrl"] + "'"),
        ("'github.com/cogwheel0/conduit'", "'" + BRAND["repoUrl"].split("://", 1)[1] + "'"),
    ],
    "lib/core/services/native_sheet_hydration_service.dart": [
        ("url: 'https://github.com/cogwheel0/conduit',", "url: '" + BRAND["repoUrl"] + "',"),
    ],
    "lib/features/release_notes/data/release_links.dart": [
        ("'https://play.google.com/store/apps/details?id=" + UPSTREAM_BUNDLE_ID + "'", "'" + BRAND["playStoreUrl"] + "'"),
        ("'https://apps.apple.com/us/app/conduit-open-webui-client/id6749840287?action=write-review'", "'" + BRAND["appStoreReviewUrl"] + "'"),
    ],
    # Apple grants these two only on request, to the team that asked. Until
    # Oxeegen holds them the app must not claim them: signing fails, and the
    # PCC bridge traps on its first request if the flag says it may call.
    "ios/Runner/Runner.entitlements": [
        ("\t<key>com.apple.developer.private-cloud-compute</key>\n\t<true/>\n", ""),
        ("\t<key>com.apple.developer.carplay-voice-based-conversation</key>\n\t<true/>\n", ""),
    ],
    "ios/Flutter/PccSdk.xcconfig": [
        ("CONDUIT_PCC_ENTITLEMENT_FLAG = CONDUIT_PCC_ENTITLEMENT\n", "CONDUIT_PCC_ENTITLEMENT_FLAG =\n"),
    ],
}


def apply_identity(rel: str, src: str) -> str:
    for old, new in IDENTITY.get(rel, []):
        if old in src:
            src = src.replace(old, new)
        elif new and new not in src:
            raise SystemExit(f"rebrand: {rel}: expected upstream text not found: {old!r}")
        # A removal (new == "") whose text is gone is already applied.
    return src


# ---------------------------------------------------------------------------
# File selection
# ---------------------------------------------------------------------------


@dataclass
class Rule:
    globs: tuple[str, ...]
    rewrite: Callable[[str], str]


RULES = [
    Rule(("lib/**/*.dart", "packages/*/lib/**/*.dart", "test/**/*.dart", "packages/*/test/**/*.dart", "integration_test/**/*.dart"),
         lambda s: rewrite_string_literals(s, "dart")),
    Rule(("ios/Runner/**/*.swift", "ios/ShareExtension/**/*.swift", "ios/ConduitWidget/**/*.swift", "ios/RunnerTests/**/*.swift"),
         lambda s: rewrite_string_literals(s, "swift")),
    Rule(("android/app/src/**/*.kt",), lambda s: rewrite_string_literals(s, "kotlin")),
    Rule(("lib/l10n/*.arb",), rewrite_arb),
    Rule(("ios/Runner/*.lproj/*.strings", "ios/ShareExtension/*.lproj/*.strings", "ios/ConduitWidget/*.lproj/*.strings"),
         rewrite_dot_strings),
    Rule(("ios/Runner/Info.plist", "ios/ShareExtension/Info.plist", "ios/ConduitWidget/Info.plist"), rewrite_plist),
    Rule(("android/app/src/**/res/**/*.xml", "android/app/src/**/AndroidManifest.xml"), rewrite_android_xml),
    Rule(("ios/Runner.xcodeproj/project.pbxproj",), rewrite_pbxproj),
]


def selected_files() -> dict[Path, list[Callable[[str], str]]]:
    files: dict[Path, list[Callable[[str], str]]] = {}
    for rule in RULES:
        for pattern in rule.globs:
            for path in ROOT.glob(pattern):
                rel_parts = path.relative_to(ROOT).parts
                if not path.is_file() or EXCLUDED_PARTS.intersection(rel_parts):
                    continue
                if path.name.endswith(EXCLUDED_SUFFIXES):
                    continue
                files.setdefault(path, [])
                if rule.rewrite not in files[path]:
                    files[path].append(rule.rewrite)
    for rel in IDENTITY:
        files.setdefault(ROOT / rel, [])
    return files


# Grammar the plain rename gets wrong. Korean particles follow the sound the
# name ends on: "Oxee" ends on a vowel, so 을/이/은 become 를/가/는. Czech and
# Slovak decline "Conduit" (o Conduitu, o Conduite); "Oxee" is indeclinable.
LOCALE_FIXES: list[tuple[re.Pattern, list[tuple[str, str]]]] = [
    (re.compile(r"(app_ko\.arb|/ko\.lproj/)"), [(NAME + "을", NAME + "를"), (NAME + "이 ", NAME + "가 "), (NAME + "은", NAME + "는")]),
    (re.compile(r"(app_(cs|sk)\.arb|/(cs|sk)\.lproj/)"), [(UPSTREAM_NAME + "u", NAME), (UPSTREAM_NAME + "e", NAME)]),
]


def apply_locale_fixes(rel: str, text: str) -> str:
    for pattern, pairs in LOCALE_FIXES:
        if pattern.search(rel):
            for old, new in pairs:
                # Values only for ARB: never touch keys such as "aboutConduit".
                if rel.endswith(".arb"):
                    text = re.sub(r'(?m)^(  "[^"@][^"]*": ")(.*)$', lambda m: m.group(1) + _whole(m.group(2), old, new), text)
                else:
                    text = _whole(text, old, new)
    return text


def _whole(text: str, old: str, new: str) -> str:
    return re.sub(r"(?<![A-Za-z0-9_])" + re.escape(old) + r"(?![A-Za-z0-9_])", new, text)


def transform(path: Path, rewrites: list[Callable[[str], str]]) -> tuple[str, str]:
    raw = path.read_bytes()
    original = raw.decode("utf-8")
    # Keep the file's own line endings: Windows checkouts are CRLF.
    crlf = "\r\n" in original
    text = original.replace("\r\n", "\n") if crlf else original
    for rewrite in rewrites:
        text = rewrite(text)
    rel = path.relative_to(ROOT).as_posix()
    text = apply_locale_fixes(rel, text)
    text = apply_identity(rel, text)
    if crlf:
        text = text.replace("\n", "\r\n")
    return original, text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report files that would change and exit 1")
    args = parser.parse_args()

    changed = []
    for path, rewrites in sorted(selected_files().items()):
        if not path.exists():
            raise SystemExit(f"rebrand: missing file {path.relative_to(ROOT)}")
        original, updated = transform(path, rewrites)
        if updated != original:
            changed.append(path.relative_to(ROOT).as_posix())
            if not args.check:
                path.write_bytes(updated.encode("utf-8"))

    for rel in changed:
        print(("would change: " if args.check else "rebranded: ") + rel)
    if args.check and changed:
        print(f"\n{len(changed)} file(s) still carry upstream branding. Run: python brand/tools/rebrand.py")
        return 1
    if not changed:
        print("rebrand: nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
