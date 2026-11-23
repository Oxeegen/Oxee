#!/usr/bin/env python3
"""CI: ONNX Runtime 1.22.0 for the iOS build, without download.onnxruntime.ai.

The vad plugin (third_party/vad, voice detection) calls ONNX Runtime's C API
through FFI and pulls it in with the CocoaPods pods onnxruntime-objc and
onnxruntime-c 1.22.0. CocoaPods downloads both from download.onnxruntime.ai,
dead since November 2026 (it serves another site's certificate, and the CDN
behind it answers 404); Microsoft's GitHub copies are gone too. So
`pod install` fails on every clean runner.

This builds the two pods from Microsoft's own copies instead, and points the
CI checkout's ios/Podfile at them (nothing is committed):

  * onnxruntime-c: the iOS onnxruntime.xcframework and its headers from
    Microsoft's NuGet package Microsoft.ML.OnnxRuntime 1.22.0 (release
    commit f217402897f4), checked against the SHA-512 nuget.org publishes.
  * onnxruntime-objc: brand/vendor/onnxruntime-objc, the objectivec/ sources
    of that same commit, committed here (see its README).

Both podspecs repeat CocoaPods trunk's settings for 1.22.0. Run from the
repository root on macOS, after `flutter pub get` and before `pod install`.
"""
from __future__ import annotations

import base64
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

NUPKG_URL = (
    "https://api.nuget.org/v3-flatcontainer/microsoft.ml.onnxruntime/1.22.0/"
    "microsoft.ml.onnxruntime.1.22.0.nupkg"
)
# nuget.org's packageHash for Microsoft.ML.OnnxRuntime 1.22.0 (catalog entry
# 2025.05.09.19.19.21).
NUPKG_SHA512 = "zb3eqkL6hHPGzZgArsuTH9VWdUs4ooKTJHBXF6ZZfQsPvzModaAEv3u69zwtqKuwUJ/DPc8i+uKoyXMzdwqrPg=="
XCFRAMEWORK_IN_NUPKG = "runtimes/ios/native/onnxruntime.xcframework.zip"

ROOT = Path(__file__).resolve().parents[2]
C_POD = ROOT / "brand/vendor/onnxruntime-c"
OBJC_POD = ROOT / "brand/vendor/onnxruntime-objc"
PODFILE = ROOT / "ios/Podfile"
ANCHOR = "  flutter_install_all_ios_pods File.dirname(File.realpath(__FILE__))\n"
PODS = (
    "  # OXEE (CI, brand/tools/onnxruntime_pods.py): ONNX Runtime from Microsoft's\n"
    "  # NuGet package, not the dead download.onnxruntime.ai.\n"
    "  pod 'onnxruntime-c', :path => '../brand/vendor/onnxruntime-c'\n"
    "  pod 'onnxruntime-objc', :path => '../brand/vendor/onnxruntime-objc'\n"
)


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def fetch_nupkg(dest: Path) -> None:
    subprocess.run(["curl", "-fsSL", "--retry", "4", "-o", str(dest), NUPKG_URL], check=True)
    digest = hashlib.sha512()
    with dest.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    got = base64.b64encode(digest.digest()).decode()
    if got != NUPKG_SHA512:
        fail(f"Microsoft.ML.OnnxRuntime 1.22.0 does not match nuget.org's hash (got {got})")


def build_c_pod(nupkg: Path, work: Path) -> None:
    inner = work / "onnxruntime.xcframework.zip"
    with zipfile.ZipFile(nupkg) as z, inner.open("wb") as out:
        with z.open(XCFRAMEWORK_IN_NUPKG) as src:
            shutil.copyfileobj(src, out)
    for stale in ("onnxruntime.xcframework", "Headers"):
        shutil.rmtree(C_POD / stale, ignore_errors=True)
    # unzip, not zipfile: the Mac Catalyst slice is a versioned framework
    # whose symlinks zipfile would turn into small text files.
    subprocess.run(["unzip", "-q", str(inner), "-d", str(C_POD)], check=True)
    device = C_POD / "onnxruntime.xcframework/ios-arm64/onnxruntime.framework"
    if not (device / "onnxruntime").is_file():
        fail("the NuGet package has no ios-arm64 onnxruntime.framework")
    headers = C_POD / "Headers"
    headers.mkdir()
    for h in sorted((device / "Headers").glob("*.h")):
        shutil.copy2(h, headers / h.name)
    for needed in ("onnxruntime_c_api.h", "onnxruntime_cxx_api.h", "coreml_provider_factory.h"):
        if not (headers / needed).is_file():
            fail(f"the NuGet package's framework lacks {needed}")
    print(f"onnxruntime-c: {len(list(headers.iterdir()))} headers, "
          f"{', '.join(sorted(p.name for p in (C_POD / 'onnxruntime.xcframework').iterdir() if p.is_dir()))}")


def patch_podfile() -> None:
    text = PODFILE.read_text(encoding="utf-8")
    if PODS in text:
        return
    if text.count(ANCHOR) != 1:
        fail("ios/Podfile: flutter_install_all_ios_pods line not found once; update onnxruntime_pods.py")
    PODFILE.write_text(text.replace(ANCHOR, ANCHOR + PODS), encoding="utf-8")


def main() -> None:
    if not (OBJC_POD / "onnxruntime-objc.podspec").is_file():
        fail("brand/vendor/onnxruntime-objc is missing")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        nupkg = work / "onnxruntime.nupkg"
        fetch_nupkg(nupkg)
        build_c_pod(nupkg, work)
    patch_podfile()
    print("ios/Podfile now takes onnxruntime-c and onnxruntime-objc from brand/vendor")


if __name__ == "__main__":
    main()
