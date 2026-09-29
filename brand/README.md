# The Oxee brand layer

Oxee is Conduit (github.com/cogwheel0/conduit, GPL-3.0) with a thin Oxeegen
layer on top. The layer is kept small and mechanical so each upstream release
can be taken as a plain merge. This file is the map: read it before touching
anything the layer owns, and before taking an upstream release.

## What the layer changes

| Change | How |
| --- | --- |
| Product name everywhere users see it (14 languages, iOS and Android resources, Siri/App Intents, permission prompts) | `tools/rebrand.py`, generated, never edited by hand |
| Identity: `com.oxeegen.oxee`, `group.com.oxeegen.oxee`, `oxee://`, Oxeegen repo links | `brand.json` + `tools/rebrand.py` |
| Only backend: Oxeegen Intelligence, US (`ai.oxeegen.com`) or FR (`ia.oxeegen.fr`) | `lib/brand/`, hooked into the router and both settings menus |
| No Hermes, Direct connections, Apple on-device/PCC entry points | the same hooks; upstream's code for them stays, unused |
| No donations, tip prompts or upstream release notes | hooks listed below |
| Icons (app, Android adaptive, splash, widget and notification glyph) | `tools/make_icons.py` |
| CarPlay voice and Private Cloud Compute entitlements removed | `tools/rebrand.py`; Apple grants them per team on request |
| README, French README (`docs/README.fr.md`), privacy policy, NOTICE, build docs, issue templates | written for Oxee; "keep ours" on merges |

What is deliberately **not** renamed: Dart package names (`conduit`,
`conduit_core`, ...), Kotlin package / Android namespace
`app.cogwheel.conduit`, method-channel names, Swift type names, internal
identifiers such as the background-task id. Renaming them would touch
thousands of lines and turn every upstream merge into a conflict. None of them
is visible to users. The Android `applicationId` (what the Play Store and the
device see) is `com.oxeegen.oxee`.

## Files

| Path | Purpose |
| --- | --- |
| `brand.json` | Every identity value: name, bundle id, app group, URL scheme, Apple team, repo, store links, the two regions. |
| `tools/rebrand.py` | Rewrites user-visible "Conduit" to "Oxee" inside string literals (Dart, Swift, Kotlin; comments and identifiers untouched), ARB values, `.strings`, plists, Android resources and Xcode display names; applies `brand.json`; fixes Korean particles and Czech/Slovak declension. Idempotent. `--check` lists what it would change. |
| `tools/check_brand.py` | Fails if a hook was lost or removed upstream code came back, if `rebrand.py --check` is dirty, or if the regions in Dart and `brand.json` differ. Runs in CI and before every release build. |
| `tools/flutter_test.py` | `flutter test` over every test file except `upstream-tests-replaced.txt`. |
| `upstream-tests-replaced.txt` | Upstream test files that assert behaviour Oxee replaces, each with its reason. A listed file that disappears fails the run. |
| `tools/make_icons.py` | Draws the Oxee mark and regenerates every icon at its upstream size. Needs Pillow. |
| `tools/android_keystore.py` | Run once: creates the permanent Android signing key, stores it in GitHub secrets and writes a backup to Documents\Oxee signing keys. |
| `tools/ios_certificate.py` | Run once: creates the Apple Distribution certificate through the API and stores it in GitHub secrets without printing it. |
| `tools/ios_signing.py` | CI: App Store profiles through the API, throwaway keychain, manual Release signing, ExportOptions. |
| `assets/` | `oxee-icon-1024.png` (store icon, README), `oxee-mark-1024.png`, `oxee-mark.svg`. |
| `../lib/brand/oxee_brand.dart` | Regions, the strings the layer adds (English and French), the region switcher, the iOS native-sheet row. |
| `../lib/brand/oxee_region_page.dart` | First-run / change-server screen. Health check and Open WebUI check against the fixed region URL, then upstream's sign-in page. |
| `../test/brand/oxee_region_test.dart` | Region URLs, `brand.json` agreement, the picker in English and French, selection of the saved region. |

## Hooks in upstream files

Every hook carries an `// OXEE:` comment; `tools/check_brand.py` asserts each
one (and the absence of what it removed).

| File | Hook |
| --- | --- |
| `lib/core/router/app_router.dart` | `backendChooser`, `serverConnection` and `login` routes build `OxeeRegionPage`; `serverConnection` takes the region to auto-connect as `extra`. |
| `lib/features/profile/views/profile_page.dart` | Region row replaces the Hermes, Direct connections and "Connect Open WebUI" rows; donation section and its links removed. |
| `lib/features/navigation/widgets/sidebar_user_pill.dart` | Same for the iOS 26 native settings sheet; support section removed. |
| `lib/main.dart` | Routes the native-sheet region row to `showOxeeRegionSwitcher`; no `ReleaseNotesCoordinator` (upstream's "What's new" popup). |
| `lib/core/services/native_sheet_hydration_service.dart` | No release-notes row in the native About sheet (repo link via `rebrand.py`). |
| `lib/features/profile/views/about_page.dart` | No release-notes row (repo link via `rebrand.py`). |
| `.github/workflows/release.yml` | Guarded to `cogwheel0/conduit`: upstream's release never runs here. |
| `.github/workflows/l10n.yml` | Guarded the same way; `ci.yml`'s Localization job runs its ARB checks. |
| `.github/workflows/ci.yml` | Runs `check_brand.py` and `flutter_test.py` instead of plain `flutter test`. |

### How switching region works

Signing in goes through upstream's `selectUnauthenticatedServerConfig`, which
replaces the saved server. So a switch is: confirm, full sign-out
(`signOutCoordinatorProvider.signOut(keepServerDetails: false)`), then
`serverConnection` with the target region as `extra`, which connects and opens
the sign-in page. Upstream has per-server session vaults
(`switchToServerConfig`) that could later keep both regions signed in; no
upstream UI uses them yet.

## Taking an upstream release

Upstream tags releases `v<version>` on `main`, linearly.

```bash
git fetch upstream --tags
git merge v4.x.y
```

Conflicts, by kind:

- **A line `rebrand.py` rewrote** (a string literal, ARB value, plist, pbxproj
  identity line): take upstream's side, then `python brand/tools/rebrand.py`.
- **A hook** (table above): keep both sides, re-apply the hook to upstream's
  new code.
- **README.md, docs/README.fr.md, PRIVACY_POLICY.md, docs/BUILDING.md, issue
  templates**: keep ours; port any genuinely new user-facing feature into both
  READMEs.

Then:

```bash
python brand/tools/rebrand.py
python brand/tools/check_brand.py
python brand/tools/make_icons.py     # only if upstream changed icon files
flutter pub get && dart run build_runner build
flutter analyze
python brand/tools/flutter_test.py
```

New upstream entry points to Hermes, Direct connections or Apple models (a
new settings row, a new onboarding path) need a hook of their own: search the
merge diff for `RouteNames.hermesSettings`, `RouteNames.directConnections`,
`Routes.backendChooser` and `buyMeACoffee`. New donation or review prompts
likewise.

Public docs (README, French README, CONTRIBUTING if added, release notes, repo
description) talk about Oxee only: no Conduit, upstream or fork. `LICENSE` is
never edited; `NOTICE` carries the GPL-3.0 §5(a) modification notice and must
stay.

## Versioning

Oxee has its own version line, starting at 1.0.0. `pubspec.yaml` keeps
upstream's number so merges stay clean; the release workflow passes
`--build-name` (from the tag) and `--build-number` (1000 + workflow run
number, always increasing, as both stores require).

## Releasing

`.github/workflows/release-oxee.yml` builds Android on Ubuntu and iOS on
GitHub's macOS runners. No Mac is needed.

- Test build: Actions -> Release Oxee -> Run workflow, version `1.0.0`,
  publish unticked. Artifacts: arm64/armv7 APKs, the AAB, and the IPA.
- TestFlight: the same with publish ticked, or push an annotated tag
  `oxee-v1.0.0` whose message is the release notes (written about Oxee only).
  The iOS build is uploaded to App Store Connect; a tag also makes a GitHub
  release with the APKs.

Without secrets both jobs still build (Android with a throwaway key, iOS
unsigned): that proves the code compiles on both platforms but produces
nothing installable on iPhone.

### iOS signing

Distribution (App Store) signing only, done in CI by
`tools/ios_signing.py`: it imports the Oxee distribution certificate into a
throwaway keychain, finds or creates an App Store profile for each of the
three app ids through the App Store Connect API (named `Oxee App Store <id>`),
checks each carries the App Group, and switches the three Release
configurations to manual signing in the CI checkout. The committed project
keeps automatic signing, for anyone building from Xcode on a Mac.

Why not Xcode's automatic signing (`-allowProvisioningUpdates`)? It archives
with a development profile first, and Apple issues none to a team with no
registered iPhone ("Your team has no devices from which to generate a
provisioning profile"). Distribution profiles need no device.

The distribution certificate is long-lived: revoking it would turn builds
uploaded but not yet submitted for review into "Invalid Binary". It is made
once with `tools/ios_certificate.py` (from a computer with `gh` signed in and
the `.p8` key file), which stores it in the secrets below and never prints
it. If the secrets are lost, run it again with `--replace`.

### Apple account setup (once, on the web)

The API cannot do these two:

1. **App Group**: developer.apple.com -> Certificates, Identifiers & Profiles
   -> Identifiers -> + -> App Groups -> description `Oxee`, identifier
   `group.com.oxeegen.oxee`. Then open each of `com.oxeegen.oxee`,
   `com.oxeegen.oxee.ShareExtension`, `com.oxeegen.oxee.ConduitWidget`
   (registered by the "Apple setup" workflow), App Groups -> Configure -> tick
   `group.com.oxeegen.oxee` -> Save.
2. **App record**: appstoreconnect.apple.com -> Apps -> + -> New App: iOS,
   name Oxee, bundle id `com.oxeegen.oxee`, any SKU. Needed before the first
   upload.

Workflows that help: **Check Apple key** (is the key valid, Admin, which team;
what the account already has) and **Apple setup** (registers the app ids,
enables App Groups on them, optionally registers an iPhone).

### Secrets

| Secret | What |
| --- | --- |
| `OXEE_ASC_KEY_ID`, `OXEE_ASC_ISSUER_ID`, `OXEE_ASC_KEY_P8` | App Store Connect **Team** API key, role Admin (Users and Access -> Integrations -> App Store Connect API -> Team Keys). `OXEE_ASC_KEY_P8` is the text of the `.p8` file. |
| `OXEE_IOS_DIST_P12`, `OXEE_IOS_DIST_P12_PASSWORD` | The distribution certificate and its private key, written by `tools/ios_certificate.py`. Its App Store Connect id is the repository variable `OXEE_IOS_DIST_CERT_ID`. |
| `OXEE_ANDROID_KEYSTORE_BASE64` | Upload keystore, base64 |
| `OXEE_ANDROID_KEYSTORE_PASSWORD`, `OXEE_ANDROID_KEY_ALIAS`, `OXEE_ANDROID_KEY_PASSWORD` | Its passwords and alias |

The Apple Team ID (`84S2U7WQDP`) is not a secret: it is `appleTeamId` in
`brand.json`, written into the Xcode project by `rebrand.py` and read by the
workflow.

The Android key comes from `tools/android_keystore.py`, which also writes a
backup (keystore + password) to `Documents\Oxee signing keys`. Keep that
backup offline: APKs installed outside Google Play can only be updated by
builds signed with the same key. With Play App Signing it is the upload
key, which Google can reset.
