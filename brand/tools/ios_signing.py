#!/usr/bin/env python3
"""Prepare App Store signing for an iOS release build (runs on the macOS CI runner).

Distribution signing only: it needs no registered iPhone and no Mac of our own.

  1. imports the Oxee distribution certificate (OXEE_IOS_DIST_P12, made once by
     brand/tools/ios_certificate.py) into a throwaway keychain;
  2. finds or creates an App Store provisioning profile for the app and its two
     extensions through the App Store Connect API, and checks each one carries
     the App Group the share extension and widget need;
  3. switches the Release configuration of those three targets to manual
     signing with those profiles (in the CI checkout only);
  4. writes the ExportOptions.plist for `xcodebuild -exportArchive`.

    python3 brand/tools/ios_signing.py <work dir>

Environment: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8, IOS_DIST_P12 (base64),
IOS_DIST_P12_PASSWORD. Writes KEYCHAIN_PATH and IPA_EXPORT_OPTIONS to
$GITHUB_ENV.
"""

from __future__ import annotations

import base64
import json
import os
import plistlib
import re
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import jwt
import requests
from cryptography.hazmat.primitives.serialization import pkcs12

ROOT = Path(__file__).resolve().parents[2]
BRAND = json.loads((ROOT / "brand/brand.json").read_text(encoding="utf-8"))
TEAM = BRAND["appleTeamId"]
BUNDLE = BRAND["bundleId"]
APP_GROUP = BRAND["appGroupId"]
TARGETS = [BUNDLE, BUNDLE + ".ShareExtension", BUNDLE + ".ConduitWidget"]
PBXPROJ = ROOT / "ios/Runner.xcodeproj/project.pbxproj"
API = "https://api.appstoreconnect.apple.com/v1"
WWDR_G3 = "https://www.apple.com/certificateauthority/AppleWWDRCAG3.cer"


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is not set")
    return value


def github_env(name: str, value: str) -> None:
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def run(*cmd: str) -> None:
    subprocess.run(cmd, check=True)


class Api:
    def __init__(self) -> None:
        self.key_id, self.issuer, self.key = env("ASC_KEY_ID"), env("ASC_ISSUER_ID"), env("ASC_KEY_P8")

    def headers(self) -> dict:
        now = int(time.time())
        token = jwt.encode({"iss": self.issuer, "iat": now, "exp": now + 600, "aud": "appstoreconnect-v1"},
                           self.key, algorithm="ES256", headers={"kid": self.key_id, "typ": "JWT"})
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def call(self, method: str, path: str, **kw) -> dict:
        r = requests.request(method, API + path, headers=self.headers(), timeout=60, **kw)
        if r.status_code >= 400:
            errors = r.json().get("errors", []) if r.content else []
            detail = "; ".join(e.get("detail") or e.get("title", "") for e in errors)
            raise SystemExit(f"App Store Connect: {method} {path.split('?')[0]} failed ({r.status_code}): {detail}")
        return r.json() if r.content else {}


def import_certificate(work: Path) -> tuple[str, int]:
    """Throwaway keychain with the distribution identity. Returns (keychain, serial)."""
    p12 = base64.b64decode(env("IOS_DIST_P12"))
    password = env("IOS_DIST_P12_PASSWORD")
    _, certificate, _ = pkcs12.load_key_and_certificates(p12, password.encode())

    keychain = str(work / "oxee-signing.keychain-db")
    kc_password = secrets.token_urlsafe(24)
    print(f"::add-mask::{kc_password}")
    run("security", "create-keychain", "-p", kc_password, keychain)
    run("security", "set-keychain-settings", "-lut", "21600", keychain)
    run("security", "unlock-keychain", "-p", kc_password, keychain)
    p12_file = work / "dist.p12"
    p12_file.write_bytes(p12)
    try:
        run("security", "import", str(p12_file), "-k", keychain, "-P", password, "-f", "pkcs12",
            "-T", "/usr/bin/codesign", "-T", "/usr/bin/security")
    finally:
        p12_file.unlink()
    wwdr = work / "AppleWWDRCAG3.cer"
    urllib.request.urlretrieve(WWDR_G3, wwdr)
    subprocess.run(["security", "import", str(wwdr), "-k", keychain], check=False)
    run("security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", kc_password, keychain)
    listed = subprocess.run(["security", "list-keychains", "-d", "user"], capture_output=True, text=True, check=True)
    others = [line.strip().strip('"') for line in listed.stdout.splitlines() if line.strip()]
    run("security", "list-keychains", "-d", "user", "-s", keychain, *others)
    print(f"Distribution certificate imported (serial {certificate.serial_number:X}).")
    return keychain, certificate.serial_number


def certificate_id(api: Api, serial: int) -> str:
    certs = api.call("GET", "/certificates?filter[certificateType]=DISTRIBUTION&limit=200")["data"]
    for cert in certs:
        if int(cert["attributes"]["serialNumber"], 16) == serial:
            return cert["id"]
    raise SystemExit("The certificate in OXEE_IOS_DIST_P12 is not an active distribution certificate of "
                     "this team (revoked or expired?). Recreate it: python brand/tools/ios_certificate.py --replace ...")


def profile_entitlements(content: bytes) -> dict:
    start, end = content.find(b"<?xml"), content.find(b"</plist>")
    return plistlib.loads(content[start:end + len(b"</plist>")]).get("Entitlements", {})


def ensure_profile(api: Api, identifier: str, cert: str) -> tuple[str, bytes]:
    name = f"Oxee App Store {identifier}"
    bundles = api.call("GET", "/bundleIds", params={"filter[identifier]": identifier})["data"]
    bundles = [b for b in bundles if b["attributes"]["identifier"] == identifier]
    if not bundles:
        raise SystemExit(f"App id {identifier} is not registered. Run the 'Apple setup' workflow.")
    bundle_id = bundles[0]["id"]

    for attempt in range(2):
        found = api.call("GET", "/profiles", params={"filter[name]": name, "limit": 10})["data"]
        for profile in found:
            attrs = profile["attributes"]
            certs = api.call("GET", f"/profiles/{profile['id']}/certificates")["data"]
            usable = (attrs["profileState"] == "ACTIVE" and attrs["profileType"] == "IOS_APP_STORE"
                      and any(c["id"] == cert for c in certs))
            content = base64.b64decode(attrs["profileContent"]) if usable else b""
            groups = profile_entitlements(content).get("com.apple.security.application-groups", []) if usable else []
            if usable and APP_GROUP in groups:
                return name, content
            # Stale (capabilities changed, other certificate) or lacking the group: replace it.
            api.call("DELETE", f"/profiles/{profile['id']}")
        created = api.call("POST", "/profiles", json={"data": {
            "type": "profiles",
            "attributes": {"name": name, "profileType": "IOS_APP_STORE"},
            "relationships": {
                "bundleId": {"data": {"type": "bundleIds", "id": bundle_id}},
                "certificates": {"data": [{"type": "certificates", "id": cert}]},
            }}})["data"]["attributes"]
        content = base64.b64decode(created["profileContent"])
        if APP_GROUP in profile_entitlements(content).get("com.apple.security.application-groups", []):
            return name, content
    raise SystemExit(
        f"The App Group {APP_GROUP} is not enabled for {identifier}. On developer.apple.com: "
        f"Certificates, Identifiers & Profiles -> Identifiers -> {identifier} -> App Groups -> "
        f"Configure -> tick {APP_GROUP} -> Save. See brand/README.md, 'Apple account setup'.")


def install_profile(content: bytes) -> str:
    uuid = plistlib.loads(content[content.find(b"<?xml"):content.find(b"</plist>") + 8])["UUID"]
    for folder in ("Library/MobileDevice/Provisioning Profiles", "Library/Developer/Xcode/UserData/Provisioning Profiles"):
        path = Path.home() / folder
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{uuid}.mobileprovision").write_bytes(content)
    return uuid


def patch_project(profiles: dict[str, str]) -> None:
    """Manual distribution signing for the Release configuration of our targets."""
    text = PBXPROJ.read_text(encoding="utf-8")
    patched = 0

    def patch_block(match: re.Match) -> str:
        nonlocal patched
        block = match.group(0)
        if "name = Release;" not in block:
            return block
        m = re.search(r"PRODUCT_BUNDLE_IDENTIFIER = ([^;]+);", block)
        identifier = m.group(1).strip('"') if m else None
        if identifier not in profiles:
            return block
        settings = {
            "CODE_SIGN_STYLE": "Manual",
            "CODE_SIGN_IDENTITY": '"Apple Distribution"',
            '"CODE_SIGN_IDENTITY[sdk=iphoneos*]"': '"Apple Distribution"',
            "DEVELOPMENT_TEAM": TEAM,
            "PROVISIONING_PROFILE_SPECIFIER": f'"{profiles[identifier]}"',
        }
        for key, value in settings.items():
            pattern = re.compile(r"^(\t+)" + re.escape(key) + r" = [^;]*;$", re.M)
            if pattern.search(block):
                block = pattern.sub(lambda m: f"{m.group(1)}{key} = {value};", block)
            else:
                block = block.replace("buildSettings = {\n", f"buildSettings = {{\n\t\t\t\t{key} = {value};\n", 1)
        patched += 1
        return block

    text = re.sub(r"\t\t[0-9A-F]{24} /\* \w+ \*/ = \{\n\t\t\tisa = XCBuildConfiguration;.*?\n\t\t\};",
                  patch_block, text, flags=re.S)
    if patched != len(profiles):
        raise SystemExit(f"Expected {len(profiles)} Release configurations to patch, found {patched}.")
    PBXPROJ.write_text(text, encoding="utf-8")
    print(f"Xcode project: {patched} Release configurations set to manual App Store signing.")


def main() -> int:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    work.mkdir(parents=True, exist_ok=True)
    api = Api()
    keychain, serial = import_certificate(work)
    cert = certificate_id(api, serial)

    profiles = {}
    for identifier in TARGETS:
        name, content = ensure_profile(api, identifier, cert)
        uuid = install_profile(content)
        profiles[identifier] = name
        print(f"Profile ready: {name} ({uuid}), App Group {APP_GROUP} included.")

    patch_project(profiles)

    export_options = work / "ExportOptions.plist"
    export_options.write_bytes(plistlib.dumps({
        "method": "app-store-connect",
        "destination": "export",
        "teamID": TEAM,
        "signingStyle": "manual",
        "signingCertificate": "Apple Distribution",
        "provisioningProfiles": profiles,
        "manageAppVersionAndBuildNumber": False,
        "uploadSymbols": True,
    }))
    github_env("KEYCHAIN_PATH", keychain)
    github_env("IPA_EXPORT_OPTIONS", str(export_options))
    return 0


if __name__ == "__main__":
    sys.exit(main())
