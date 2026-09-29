<h1 align="center">Oxee</h1>

<p align="center">
  <a href="README.md">English</a> · <a href="docs/README.fr.md">Français</a>
</p>

<p align="center">
  <img src="brand/assets/oxee-icon-1024.png" alt="Oxee icon" width="96" height="96" />
</p>

<p align="center">
  <strong>Oxeegen Intelligence in your pocket: the native iPhone and Android app for your Oxeegen AI workspace.</strong>
</p>

<p align="center">
  <img alt="Latest release" src="https://img.shields.io/github/v/release/Oxeegen/Oxee?display_name=tag&color=5A21F2" />
  <img alt="License: GPL-3.0" src="https://img.shields.io/badge/License-GPL%203.0-16A34A" />
</p>

<br>

Oxee is the mobile app for **Oxeegen Intelligence**, Oxeegen's AI chat
workspace. Pick your region, sign in with your Oxeegen account, and your
models, chats, notes and knowledge are there, the same as on the web but
built for a phone: streaming that survives the app going to the background,
voice, the share sheet, home-screen widgets and Siri Shortcuts.

## Regions

Oxee connects only to Oxeegen's own deployments. Choose the one your account
lives on the first time you open the app; you can switch later in
**Settings → Region**.

| Region | Server | For |
| --- | --- | --- |
| **Oxeegen US** | `ai.oxeegen.com` | Accounts hosted in the United States |
| **Oxeegen FR** | `ia.oxeegen.fr` | Accounts hosted in France |

Each region keeps its own accounts and chats. Switching region signs you out
of one and into the other; nothing is copied between them.

## What you get

### Chat built for mobile

Token-by-token streaming, a transcript that holds its place while the answer
grows, and long conversations that load without stalling. Search, folders,
pinned chats, and temporary chats that leave nothing behind.

### Answers that read well on a phone

Native rendering, not a web page in a frame: highlighted code with copy,
Mermaid diagrams, LaTeX, expandable reasoning and tool-call sections, inline
citations with source cards, follow-up suggestions, and charts.

### Your whole workspace

| Area | What's included |
| --- | --- |
| Models and workspace | Models, knowledge, prompts, tools and skills as native screens, following the permissions of your account |
| Files and media | Uploads, re-attaching files already on the server, images in prompts, clipboard image paste, audio attachments |
| Notes | Autosave, pinning, AI-generated titles and enhancement, audio recording, available offline |
| Channels | Threads and reactions, when your workspace has them |
| Voice | Dictation with on-device or server speech recognition, and a hands-free voice-call mode |
| Home screen | Widgets on iOS and Android (new chat, mic, camera, photos, clipboard), quick actions, Siri Shortcuts |
| Sharing | Send text, links and images from any app straight into a prompt |
| Personalization | Light, dark and system themes, accent palettes, native iOS and Material interfaces, haptics |
| Languages | English, French, German, Spanish, Italian, Dutch, Polish, Czech, Slovak, Russian, Japanese, Korean, Simplified and Traditional Chinese |

Features such as web search, image generation, channels and notes appear when
they are enabled for your Oxeegen workspace.

## Getting started

1. Install Oxee on your iPhone or Android phone.
2. Open it and choose **Oxeegen US** or **Oxeegen FR**.
3. Sign in with your Oxeegen account (email and password, or your company
   directory login).
4. Pick a model and start chatting.

Don't have an account yet? Contact [Oxeegen](https://www.oxeegen.com).

## Privacy

- Your chats live in your Oxeegen workspace. The app keeps a copy on your
  device so they open instantly; notes and drafts also work offline.
- Sign-in tokens are kept in the Keychain on iOS and the Keystore on Android.
- No third-party analytics or advertising SDKs.
- The app talks only to the Oxeegen region you chose.

Full details in [PRIVACY_POLICY.md](PRIVACY_POLICY.md).

## Build from source

See **[docs/BUILDING.md](docs/BUILDING.md)** for requirements, code
generation, tests and release builds.

```bash
git clone --recursive https://github.com/Oxeegen/Oxee.git
cd Oxee
flutter pub get
dart run build_runner build
flutter run -d android   # or: flutter run -d ios (needs a Mac)
```

## Feedback

Found a bug or have an idea? Open an
[issue](https://github.com/Oxeegen/Oxee/issues).

## License

Oxee is open-source software under the
[GNU General Public License v3.0](LICENSE). See [NOTICE](NOTICE).

Maintained by [Oxeegen](https://www.oxeegen.com).
