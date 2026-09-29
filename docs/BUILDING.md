# Building Oxee

Everything needed to build, run, and verify Oxee from source. To *use* the
app, install it from the App Store or Google Play.

## Requirements

| | |
| --- | --- |
| Flutter SDK | Flutter `3.47.0` or newer, with Dart `3.13.0` or newer |
| Android | Java 17+, AGP 9.1.0, KGP 2.4.0, Gradle 9.3.1, Android SDK 36, Android 7.0+ (API 24) at runtime |
| iOS | Xcode with an iOS 16.0+ deployment target |
| Backend | An Oxeegen Intelligence account, in the US (`ai.oxeegen.com`) or FR (`ia.oxeegen.fr`) region |
| Brand tooling | Python 3.10+ and Pillow (icons only) |

## Clone

```bash
git clone --recursive https://github.com/Oxeegen/Oxee.git
cd Oxee
```

`--recursive` matters. Oxee vendors four submodules:

- `third_party/mermaid`: the native Mermaid renderer packages
  (`mermaid_core`, `mermaid_flutter`), referenced by path from `pubspec.yaml`.
  Without it, `flutter pub get` fails.
- `third_party/katex`: KaTeX assets for math rendering.
- `openwebui-src`: a vendored Open WebUI checkout used **only** as an API
  reference. It is not built or shipped.
- `hermes-src`: a vendored Hermes Agent checkout (NousResearch/hermes-agent)
  used **only** as the reference for the Hermes gateway RPC and REST contracts
  (`tui_gateway/`, `gateway/platforms/api_server.py`). It is not built or
  shipped.

For an existing clone:

```bash
git submodule update --init --recursive
```

## Run

```bash
flutter pub get
dart run build_runner build
XCODE_XCCONFIG_FILE="$PWD/ios/Flutter/ArmOnly.xcconfig" flutter run -d ios
# or
flutter run -d android
```

`dart run build_runner build` is not optional. Riverpod providers, Freezed
models, JSON serialization, Drift tables, and Pigeon bindings all generate into
`*.g.dart` / `*.freezed.dart` files that are **git-ignored**. A fresh clone or a
new worktree has none of them, so the analyzer will report hundreds of errors
until codegen runs. If you see missing-symbol errors that look impossible, run
codegen before you start debugging.

The iOS simulator build targets Apple Silicon only. The `XCODE_XCCONFIG_FILE`
setting excludes x86_64 from Swift packages as well as the app and extensions.
Use an ARM emulator or device for Android development.

Pigeon remains pinned separately because its analyzer constraint does not
overlap the Dart 3.13-compatible Riverpod and Freezed generators. Install its
isolated tool dependencies before regenerating platform bindings:

```bash
dart pub get --directory tool/pigeon_codegen
dart tool/pigeon_codegen/bin/generate.dart
```

`vad` 0.0.8 still declares Record 6.x support. The root pubspec temporarily
pins VAD and overrides `record` to 7.1.1; Oxee passes VAD a PCM stream owned
by `VoiceInputService`, so VAD never creates its incompatible internal
recorder. Remove the override and exact VAD pin when [upstream issue
#22](https://github.com/keyur2maru/vad/issues/22) ships Record 7 support. Keep
the Oxee-owned stream until upstream can also preserve externally managed
iOS audio sessions.

## Verify

```bash
flutter pub get
dart run build_runner build
flutter analyze
python brand/tools/check_brand.py
python brand/tools/flutter_test.py
```

`brand/tools/flutter_test.py` runs `flutter test` on every test file except
the few listed in `brand/upstream-tests-replaced.txt`. CI
(`.github/workflows/ci.yml`) runs the same gates on every push to `main` and
on pull requests.

Tests use `flutter_test` with `package:checks` for assertions and `mocktail` for
mocks. Lints come from `flutter_lints` plus `riverpod_lint`.

## Release builds

```bash
# Android
flutter build apk --target-platform android-arm,android-arm64 --release
flutter build appbundle --target-platform android-arm,android-arm64 --release

# iOS
XCODE_XCCONFIG_FILE="$PWD/ios/Flutter/ArmOnly.xcconfig" flutter build ios --release
```

Signed store builds come from `.github/workflows/release-oxee.yml` on
GitHub's macOS and Linux runners, so iOS releases do not need a local Mac.
See `brand/README.md`, "Releasing".

## Localization

Translations live in `lib/l10n/*.arb`, configured by `l10n.yaml`. English
(`app_en.arb`) is the template; every other locale mirrors its keys.

Do not hand-edit the generated localization Dart. Edit the ARB inputs and let
codegen regenerate. Two helpers validate the result, and CI runs the same
checks:

```bash
dart run tool/validate_arb_locales.dart
dart run tool/verify_arb_descriptions.dart
```

Every key in `app_en.arb` needs an `@key` entry with a `description`, and that
description is the only context a translator gets.

## Project layout

```text
lib/
  core/                 auth, routing, models, networking, database, platform services
    auth/               token storage, interceptors, cookie + proxy handling
    database/           Drift schema, DAOs, mappers, full-text search
    services/           API client, streaming, widgets, quick actions
  features/
    auth/               server setup, login, SSO, proxy auth
    channels/           channel browsing and threaded messaging
    chat/               conversations, attachments, tools, streaming, voice call
    direct_connections/ OpenAI-compatible, Ollama, and OpenRouter profiles
    hermes/             Hermes Agent transport, approvals, scheduled jobs
    navigation/         chat shell, drawer, adaptive navigation
    notes/              note editor and AI-assisted note workflows
    notifications/      notification routing and gating
    profile/            theme, preferences, app customization
    prompts/            prompt helpers and prompt variable UI
    terminal/           WebSocket terminal sessions and file browser
    tools/              tool integration surfaces
    workspace/          native models, knowledge, prompts, tools, skills
  l10n/                 ARB translation sources
  shared/               reusable widgets, theme tokens, task infrastructure
```

## Conventions

- Diagnostics go through `DebugLogger` (`lib/core/utils/debug_logger.dart`) with
  slash-scoped `scope:` values like `auth/proxy`, `streaming/helper`, or
  `models/default`. No raw `print` calls.
- Credentials and auth tokens belong in `flutter_secure_storage` via
  `SecureCredentialStorage`. Auth-bearing headers stay scoped to Dio clients
  configured for the selected `ServerConfig.url`.
- `lib/core/services/api_service.dart` is roughly 6000 lines and mixes many
  endpoint families. Verify endpoint names against `openwebui-src/` before
  adding or changing API calls.
- Chat markdown is sanitized in `lib/features/chat/views/chat_page.dart`, but
  Chart.js blocks still render through a WebView in
  `lib/shared/widgets/markdown/markdown_config.dart`. Treat model output as
  untrusted when touching that pipeline.

## Platform permissions

**Android** requests microphone, camera, and optional location access for voice
input, image capture, and location sharing. Attachments go through the system
photo picker, so no broad storage permission is needed.

**iOS** requests microphone, speech recognition, camera, photo library, and
optional location-when-in-use access for the same workflows.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `flutter pub get` cannot resolve `mermaid_core` | Submodules are missing. Run `git submodule update --init --recursive`. |
| Analyzer reports errors in files you never touched | Generated code is missing. Run `dart run build_runner build`. |
| Codegen fails with output conflicts | `dart run build_runner build --delete-conflicting-outputs` |
| iOS device build fails | `cd ios && pod install`, then confirm signing in Xcode. |
| Android build fails | Check the Java 17 / Gradle toolchain, then `flutter clean`. |
| Streaming stalls against your server | Confirm `ENABLE_WEBSOCKET_SUPPORT="true"` on the Open WebUI deployment. |
