#!/usr/bin/env python3
"""Create Oxee's permanent Android signing key and store it in GitHub secrets.

Run once, on a computer where `gh` is signed in to GitHub. It:

  * generates the key (RSA 4096, self-signed certificate valid 30 years) in
    memory;
  * stores it in the repository secrets the release workflow reads
    (OXEE_ANDROID_KEYSTORE_BASE64, OXEE_ANDROID_KEYSTORE_PASSWORD,
    OXEE_ANDROID_KEY_ALIAS, OXEE_ANDROID_KEY_PASSWORD);
  * writes a backup (the keystore file and its password) to --backup-dir.
    Keep that backup safe and offline, for example in a password manager:
    APKs installed outside Google Play can only be updated by builds signed
    with this same key. (With Google Play, this is the "upload key": Google
    signs the app with its own key and can reset this one.)

Nothing is printed except the backup location and the certificate
fingerprints (public).

    python brand/tools/android_keystore.py

Refuses to run if the secrets already exist; --replace overrides that, which
breaks updates for anyone who installed an APK signed with the old key.

Needs: pip install cryptography
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import secrets
import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[2]
BRAND = json.loads((ROOT / "brand/brand.json").read_text(encoding="utf-8"))
REPO = BRAND["repoUrl"].split("github.com/", 1)[1]
ALIAS = "oxee"
SECRET = "OXEE_ANDROID_KEYSTORE_BASE64"


def gh(*args: str, stdin: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True, check=check)


def fingerprint(cert: x509.Certificate, algorithm) -> str:
    return ":".join(f"{b:02X}" for b in cert.fingerprint(algorithm))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backup-dir", default=str(Path.home() / "Documents" / "Oxee signing keys"),
                        help="where to write the backup (default: Documents\\Oxee signing keys)")
    parser.add_argument("--replace", action="store_true",
                        help="replace an existing key (breaks updates of APKs signed with it)")
    args = parser.parse_args()

    if gh("auth", "status", check=False).returncode != 0:
        raise SystemExit("gh is not signed in to GitHub. Run: gh auth login")
    existing = gh("secret", "list", "--repo", REPO, check=False).stdout.split()
    if SECRET in existing and not args.replace:
        print(f"{REPO} already has its Android signing key ({SECRET}). Nothing to do.")
        print("Replacing it breaks updates of APKs signed with it; if you really mean to, add --replace.")
        return 0

    backup = Path(args.backup_dir).expanduser()
    backup.mkdir(parents=True, exist_ok=True)
    keystore_file = backup / "oxee-android-signing-key.p12"
    password_file = backup / "oxee-android-signing-key-password.txt"
    if keystore_file.exists() and not args.replace:
        raise SystemExit(f"{keystore_file} already exists. Move it away first, or use --replace.")

    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Oxee"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Oxeegen"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            # Google Play requires validity past 2033; 30 years leaves margin.
            .not_valid_after(now + dt.timedelta(days=365 * 30))
            .sign(key, hashes.SHA256()))

    password = secrets.token_urlsafe(24)
    # PKCS#12 is Java's default keystore type: Gradle reads it as is. For
    # PKCS#12 the key password equals the store password.
    p12 = pkcs12.serialize_key_and_certificates(
        ALIAS.encode(), key, cert, None, serialization.BestAvailableEncryption(password.encode()))

    keystore_file.write_bytes(p12)
    password_file.write_text(
        "Oxee Android signing key\n"
        f"Keystore file: {keystore_file.name} (PKCS#12)\n"
        f"Alias: {ALIAS}\n"
        f"Password (store and key): {password}\n"
        f"SHA-256 certificate fingerprint: {fingerprint(cert, hashes.SHA256())}\n"
        "Keep both files together, offline and private. Needed to sign updates of\n"
        "APKs installed outside Google Play; the GitHub secrets hold the same key.\n",
        encoding="utf-8")

    for secret, value in ((SECRET, base64.b64encode(p12).decode()),
                          ("OXEE_ANDROID_KEYSTORE_PASSWORD", password),
                          ("OXEE_ANDROID_KEY_ALIAS", ALIAS),
                          ("OXEE_ANDROID_KEY_PASSWORD", password)):
        result = gh("secret", "set", secret, "--repo", REPO, stdin=value, check=False)
        if result.returncode != 0:
            raise SystemExit(f"Storing {secret} in GitHub failed:\n{result.stderr}\n"
                             f"The backup in {backup} is complete; re-run with --replace once gh works.")

    print(f"Android signing key created and stored in {REPO} (4 secrets).")
    print(f"Backup written to: {backup}")
    print("  Move those two files somewhere safe and offline (for example a password manager).")
    print(f"SHA-256 fingerprint (public): {fingerprint(cert, hashes.SHA256())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
