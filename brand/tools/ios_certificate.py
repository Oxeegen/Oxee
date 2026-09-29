#!/usr/bin/env python3
"""Create Oxee's Apple Distribution certificate and store it in GitHub secrets.

Run once, on a computer where `gh` is signed in to GitHub and the App Store
Connect API key file (AuthKey_<KEYID>.p8) is available. Nothing secret is
printed or saved: the private key is generated in memory, handed to GitHub's
secret store (OXEE_IOS_DIST_P12, OXEE_IOS_DIST_P12_PASSWORD) and dropped.

    python brand/tools/ios_certificate.py --key <path to AuthKey_XXXXXXXXXX.p8> --issuer <issuer id>

The certificate's id is kept in the repository variable OXEE_IOS_DIST_CERT_ID.
Run again with --replace to revoke that certificate and make a new one (for
example if the secrets were lost). Apps already on the App Store or TestFlight
are not affected by a replacement; builds uploaded but not yet submitted for
review should be rebuilt afterwards.

Needs: pip install cryptography pyjwt requests
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

import jwt
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[2]
BRAND = json.loads((ROOT / "brand/brand.json").read_text(encoding="utf-8"))
REPO = BRAND["repoUrl"].split("github.com/", 1)[1]
API = "https://api.appstoreconnect.apple.com/v1"
CERT_ID_VARIABLE = "OXEE_IOS_DIST_CERT_ID"


def gh(*args: str, stdin: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--key", required=True, help="path to AuthKey_<KEYID>.p8")
    parser.add_argument("--issuer", required=True, help="App Store Connect issuer id")
    parser.add_argument("--key-id", help="key id (default: read from the file name)")
    parser.add_argument("--replace", action="store_true", help="revoke the previous Oxee certificate first")
    args = parser.parse_args()

    key_path = Path(args.key).expanduser()
    key_id = args.key_id or (re.search(r"AuthKey_([A-Z0-9]{10})\.p8$", key_path.name) or [None, None])[1]
    if not key_id:
        raise SystemExit("Could not read the key id from the file name; pass --key-id.")
    signing_key = key_path.read_text(encoding="utf-8").strip()

    def headers() -> dict:
        now = int(time.time())
        token = jwt.encode({"iss": args.issuer.strip(), "iat": now, "exp": now + 600, "aud": "appstoreconnect-v1"},
                           signing_key, algorithm="ES256", headers={"kid": key_id, "typ": "JWT"})
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def fail(response: requests.Response, what: str):
        errors = response.json().get("errors", []) if response.content else []
        detail = "; ".join(e.get("detail") or e.get("title", "") for e in errors)
        raise SystemExit(f"{what} failed ({response.status_code}): {detail}")

    if gh("auth", "status", check=False).returncode != 0:
        raise SystemExit("gh is not signed in to GitHub. Run: gh auth login")

    previous = gh("variable", "get", CERT_ID_VARIABLE, "--repo", REPO, check=False)
    previous_id = previous.stdout.strip() if previous.returncode == 0 else ""
    if previous_id:
        existing = requests.get(f"{API}/certificates/{previous_id}", headers=headers(), timeout=30)
        if existing.status_code == 200 and not args.replace:
            attrs = existing.json()["data"]["attributes"]
            print(f"Oxee already has its distribution certificate ({attrs['name']}, "
                  f"expires {attrs['expirationDate'][:10]}). Nothing to do.")
            print("To make a new one (revoking this one), run again with --replace.")
            return 0
        if existing.status_code == 200:
            r = requests.delete(f"{API}/certificates/{previous_id}", headers=headers(), timeout=30)
            if r.status_code >= 400:
                fail(r, "Revoking the previous certificate")
            print("Previous Oxee certificate revoked.")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(x509.Name([
               x509.NameAttribute(NameOID.COMMON_NAME, "Oxee CI Distribution"),
               x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Oxeegen"),
           ]))
           .sign(private_key, hashes.SHA256()))
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

    r = requests.post(f"{API}/certificates", headers=headers(), timeout=60, json={"data": {
        "type": "certificates",
        "attributes": {"certificateType": "DISTRIBUTION", "csrContent": csr_pem}}})
    if r.status_code >= 400:
        fail(r, "Creating the certificate")
    data = r.json()["data"]
    cert_id, attrs = data["id"], data["attributes"]
    certificate = x509.load_der_x509_certificate(base64.b64decode(attrs["certificateContent"]))

    password = secrets.token_urlsafe(24)
    # Legacy PKCS#12 algorithms: what macOS `security import` reads everywhere.
    encryption = (serialization.PrivateFormat.PKCS12.encryption_builder()
                  .kdf_rounds(50000)
                  .key_cert_algorithm(pkcs12.PBES.PBESv1SHA1And3KeyTripleDESCBC)
                  .hmac_hash(hashes.SHA1())
                  .build(password.encode()))
    p12 = pkcs12.serialize_key_and_certificates(b"Oxee Distribution", private_key, certificate, None, encryption)

    try:
        gh("secret", "set", "OXEE_IOS_DIST_P12", "--repo", REPO, stdin=base64.b64encode(p12).decode())
        gh("secret", "set", "OXEE_IOS_DIST_P12_PASSWORD", "--repo", REPO, stdin=password)
        gh("variable", "set", CERT_ID_VARIABLE, "--repo", REPO, "--body", cert_id)
    except subprocess.CalledProcessError as e:
        # Do not leave a certificate nobody holds the key for.
        requests.delete(f"{API}/certificates/{cert_id}", headers=headers(), timeout=30)
        raise SystemExit(f"Storing the certificate in GitHub failed, so it was revoked again:\n{e.stderr}")

    print(f"Created {attrs['name']} (expires {attrs['expirationDate'][:10]}).")
    print(f"Stored in {REPO}: secrets OXEE_IOS_DIST_P12 and OXEE_IOS_DIST_P12_PASSWORD, variable {CERT_ID_VARIABLE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
