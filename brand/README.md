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
| Backends: Oxeegen Intelligence, US (`ai.oxeegen.com`) or FR (`ia.oxeegen.fr`), first; Oxee Hermes (upstream's Hermes Agent, Oxeegen's fork) can be added in Settings → Accounts → Add Account | `lib/brand/`, hooked into the router, the account sheet and Settings |
| "Hermes" / "Hermes Agent" reads "Oxee Hermes" (translations, the default connection and model name) | `tools/rebrand.py` |
| No Direct connections, Apple on-device/PCC or LibreChat entry points | the same hooks, and LibreChat switched off app-wide (`oxeeProviderOverrides`); upstream's code for them stays, unused |
| No donations, tip prompts or upstream release notes | hooks listed below |
| No push notifications yet: they need a relay to Apple and Google, which Oxeegen does not run. Settings leaves push out (`oxeePushSections`, back by itself in a build given `CONDUIT_PUSH_RELAY_URL`); the iOS app claims no `aps-environment` and the notification extension no App Group | `lib/brand/oxee_brand.dart`, `tools/rebrand.py` (`IDENTITY`) |
| Icons (app, Android adaptive, splash, widget and notification glyph), and the Oxee mark where upstream shows the Open WebUI logo or its own icon in the app (`assets/icons/open_webui*.png`, `app_icon_square.png`) | `tools/make_icons.py` |
| CarPlay voice and Private Cloud Compute entitlements removed | `tools/rebrand.py`; Apple grants them per team on request |
| README, French README (`docs/README.fr.md`), privacy policy, NOTICE, build docs, issue templates | written for Oxee; "keep ours" on merges |
| `docs/open-webui-functions.md` (guide for Open WebUI function authors) | `tools/rebrand.py` renames the product in its prose; the protocol value `"client": "conduit"` stays |
| No upstream donation links, Pullfrog agent workflow, or desktop-app and Hermes-plugin workflows (`.github/FUNDING.yml`, `.github/workflows/pullfrog.yml`, `desktop.yml`, `release-desktop.yml`, `publish-hermes-plugin.yml`; Oxee is a phone app, and `release-desktop.yml` would run on every GitHub release) | deleted; `tools/check_brand.py` fails if they come back |
| `packages/conduit_protocol` (the wire protocol of upstream's desktop app and daemon; its tests compare against goldens) | never rewritten by `tools/rebrand.py` |

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
| `tools/rebrand.py` | Rewrites user-visible "Conduit" to "Oxee" inside string literals (Dart, Swift, Kotlin; comments and identifiers untouched), ARB values, `.strings`, plists, Android resources and Xcode display names; applies `brand.json`; fixes Korean particles and Czech/Slovak declension. Renames Hermes to "Oxee Hermes" in every ARB value, and in a whole Dart literal only when the renamed text is an English translation; in tests also a longer message quoting such a translation ("Delivery: Save in Hermes, ..."). A bare "Hermes" in tests is data, except in the sidebar tab tests it lists. Idempotent. `--check` lists what it would change. |
| `tools/check_brand.py` | Fails if a hook was lost or removed upstream code came back, if `rebrand.py --check` is dirty, or if the regions in Dart and `brand.json` differ. Runs in CI and before every release build. |
| `tools/flutter_test.py` | `flutter test` over every test file except `upstream-tests-replaced.txt`. |
| `upstream-tests-replaced.txt` | Upstream test files that assert behaviour Oxee replaces, each with its reason. A listed file that disappears fails the run. |
| `tools/make_icons.py` | Draws the Oxee mark and regenerates every icon at its upstream size. Needs Pillow. |
| `tools/android_keystore.py` | Run once: creates the permanent Android signing key, stores it in GitHub secrets and writes a backup to Documents\Oxee signing keys. |
| `tools/ios_certificate.py` | Run once: creates the Apple Distribution certificate through the API and stores it in GitHub secrets without printing it. |
| `tools/ios_signing.py` | CI: App Store profiles through the API, throwaway keychain, manual Release signing, ExportOptions. |
| `tools/onnxruntime_pods.py`, `vendor/` | CI: ONNX Runtime 1.22.0 for iOS (voice detection) without its dead download host. See "ONNX Runtime on iOS". |
| `assets/` | `oxee-icon-1024.png` (store icon, README), `oxee-mark-1024.png`, `oxee-mark.svg`. |
| `../lib/brand/oxee_brand.dart` | Regions, the strings the layer adds (English and French), the region switcher, the iOS native-sheet row, `oxeeProviderOverrides` (LibreChat off). |
| `../lib/brand/oxee_region_page.dart` | First-run / change-server screen. Health check and Open WebUI check against the fixed region URL, then upstream's sign-in page. Also `OxeeRegionAddChoices`, the account sheet's Oxeegen tab. |
| `../test/brand/` | Region URLs, `brand.json` agreement, the picker in English and French, selection of the saved region; the native Settings adjustments; the account sheet's tabs. |

## Hooks in upstream files

Every hook carries an `// OXEE:` comment; `tools/check_brand.py` asserts each
one (and the absence of what it removed).

| File | Hook |
| --- | --- |
| `lib/core/router/app_router.dart` | `backendChooser`, `serverConnection`, `addServer` and `login` routes build `OxeeRegionPage` (`addServer` in adding mode); `extra` is the region to connect to at once. |
| `lib/features/profile/widgets/account_sheet.dart` | Add Account sheet: tabs Oxeegen (`OxeeRegionAddChoices`: a region, then upstream's sign-in, adding the account) and Oxee Hermes (upstream's Hermes form); no Direct tab (`oxeeOffersOtherBackends`). Every "add account" path opens it. |
| `lib/features/navigation/widgets/sidebar_user_pill.dart` | iOS 26 native Settings root: `oxeeNativeRootSections` adds the Region row and drops the donations; no support items. |
| `lib/features/settings/views/settings_root_page.dart` | The Flutter Settings root (Android, and iOS when the native sheet cannot open), drawn from the same definitions since upstream 4.3.2: `oxeeNativeRootSections` too. |
| `lib/core/services/native_sheet_hydration_service.dart` | The root it rebuilds goes through `oxeeNativeRootSections` too; the Accounts page through `oxeeNativeAccountsDetail` (no Direct); About rows through `oxeeNativeAboutItems` (no release notes); Notifications' push sections through `oxeePushSections`. These pages serve both Settings. |
| `lib/features/settings/settings_controller.dart` | Routes the Region row (either Settings) to `showOxeeRegionSwitcher`. |
| `lib/main.dart` | `oxeeProviderOverrides` in the app's provider container: LibreChat off, and `oxeeSettingsProvider` on, which turns the `oxeeNative*` / `oxeePushSections` adjustments on (off, upstream's tests of the same pages see upstream's rows); no `ReleaseNotesCoordinator` (upstream's "What's new" popup). |
| `lib/core/utils/native_sheet_utils.dart` | Unedited: Oxee adjusts what its builders return, at the call sites, so upstream's tests of them keep passing. |
| `packages/conduit_core/lib/features/support/support_links.dart` | About's repository link (`rebrand.py`). |
| `.github/workflows/release.yml` | Guarded to `cogwheel0/conduit`: upstream's release never runs here. |
| `.github/workflows/ci.yml` | Runs `check_brand.py` before the gates and `flutter_test.py` in place of `tool/run_test_shards.dart`. |

Prefer a call-site adjustment over an edit inside an upstream builder: the
builder's upstream tests keep passing and merges do not conflict there.

**Platform UI seam.** Upstream's CI (`tool/platform_ui_lint.dart`) fails a
`lib/` file that imports `material_ui`/`cupertino_ui` or uses a listed
control (`CircularProgressIndicator`, `AlertDialog`, ...) beyond its entry in
`tool/platform_ui_allowlist.yaml`, and also fails an entry that became
*smaller* (stale). Brand files stay at zero: `flutter/widgets.dart`, the
`platform_ui` facade and `platform_ui/vocabulary.dart` (icons, `Theme`). A hook
must not add or remove a counted import or control in an upstream file.

### How switching region works

Since upstream 4.2.0 several Open WebUI accounts stay signed in. The Region
row (`showOxeeRegionSwitcher`) switches to the other region's saved account
(`switchToSavedAccount`) when there is one; otherwise it begins an account
addition (`openOxeeRegionAddAccount`: `accountAdditionOriginProvider.begin`,
then `addServer` with the region) and the sign-in page adds the account next
to the current one. The picker in adding mode ends the addition when it goes
and, on Back, drops an addition whose sign-in never finished
(`abandonAddedAccount`), as upstream's server page does.

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

New upstream entry points to Direct connections, Apple models or another
backend (a new settings row, a new onboarding path, a new account-sheet tab)
need a hook of their own: search the merge diff for
`RouteNames.directConnections`, `AccountKind`, `Routes.backendChooser` and
`buyMeACoffee`. New donation or review prompts likewise. Hermes entry points
are fine: Oxee offers Oxee Hermes. A new upstream test whose literal is a
bare "Hermes" tab label goes into `HERMES_TAB_TESTS` in `rebrand.py`. Fixtures
that carry the product token (LibreChat's pinned User-Agents) get a `Rule`.

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
  publish unticked. Artifacts: arm64/armv7 APKs, the AAB, and the IPA. The
  IPA also goes through App Store Connect's upload checks (`altool
  --validate-app`), so a build Apple would refuse fails here, not at publish.
- TestFlight: the same with publish ticked, or push an annotated tag
  `oxee-v1.0.0` whose message is the release notes (written about Oxee only).
  The iOS build is uploaded to App Store Connect; a tag also makes a GitHub
  release with the APKs.

Without secrets both jobs still build (Android with a throwaway key, iOS
unsigned): that proves the code compiles on both platforms but produces
nothing installable on iPhone.

Apple Silicon runners are sometimes all taken ("The job was not acquired by
Runner"). Run the workflow with `ios_runner` set to `macos-26-intel`: same
macOS and Xcode on Intel, slower but usually free.

### ONNX Runtime on iOS

The vendored vad plugin (voice detection) calls ONNX Runtime through FFI and
pulls it in with the CocoaPods pods `onnxruntime-objc` and `onnxruntime-c`
1.22.0. CocoaPods downloads them from download.onnxruntime.ai, dead since
November 2026 (wrong certificate, then 404), and `github.com/microsoft/onnxruntime`
is gone too. Before `pod install`, `tools/onnxruntime_pods.py` builds both pods
from Microsoft's own copies and points the CI checkout's Podfile at them:

- `onnxruntime-c`: the iOS xcframework and headers from the NuGet package
  Microsoft.ML.OnnxRuntime 1.22.0, checked against nuget.org's SHA-512.
- `onnxruntime-objc`: `vendor/onnxruntime-objc`, the sources of the same
  release commit, committed (its README says where they came from).

The podspecs repeat CocoaPods trunk's settings. When vad moves to another
ONNX Runtime version, update the NuGet version and hash, and the vendored
sources, together.

### iOS signing

Distribution (App Store) signing only, done in CI by
`tools/ios_signing.py`: it imports the Oxee distribution certificate into a
throwaway keychain, finds or creates an App Store profile for each of the
four app ids through the App Store Connect API (named `Oxee App Store <id>`),
checks the app, share extension and widget profiles carry the App Group, and
switches the four Release configurations to manual signing in the CI
checkout. The notification extension (upstream 4.3.2) needs no capability in
Oxee, so the script registers its app id itself when the account lacks it. The committed project
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
