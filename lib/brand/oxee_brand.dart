// Oxee brand layer: the two Oxeegen Intelligence regions Oxee connects to,
// the strings it adds, and the Region entry of Settings.
// See brand/README.md for every place the layer hooks into upstream code.
//
// Platform UI seam (tool/platform_ui_lint.dart): no material_ui or
// cupertino_ui imports here; widgets come from flutter/widgets.dart.

import 'package:conduit_core/features/push/services/push_relay_client.dart'
    show kConduitPushRelayUrl;
import 'package:conduit_core/features/librechat/providers/librechat_providers.dart'
    show libreChatBackendEnabledProvider;
import 'package:conduit_core/providers/app_providers.dart';
import 'package:conduit_core/providers/openwebui_accounts_controller.dart'
    show accountAdditionOriginProvider;
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart'
    show Override, ProviderListenable;
import 'package:go_router/go_router.dart';

import '../core/services/native_sheet_bridge.dart';
import '../features/profile/widgets/account_actions.dart'
    show switchToSavedAccount;
import '../shared/services/navigation_service.dart';
import '../shared/widgets/themed_dialogs.dart';

/// Oxee offers Oxeegen Intelligence accounts and Oxee Hermes connections.
/// Upstream's other backends (Direct providers, Apple's models, LibreChat)
/// stay in the code but are not offered. A final, not a const, so the code it
/// guards is still analyzed and compiled rather than reported as dead.
/// LibreChat is switched off at the root instead (main.dart), which hides
/// every LibreChat entry upstream gates on `libreChatBackendEnabledProvider`.
// ignore: prefer_const_declarations
final bool oxeeOffersOtherBackends = false;

/// Whether Settings is Oxee's: the Region row, and no donations, release
/// notes, Direct card or push without a relay (the `oxeeNative*` and
/// [oxeePushSections] adjustments below). Off by default, so upstream's tests
/// of the same pages see upstream's rows; the app turns it on through
/// [oxeeProviderOverrides].
final oxeeSettingsProvider = Provider<bool>((ref) => false);

/// Reads a provider: `ref.read` or `ref.watch` of a widget, a provider's
/// `ref.read`, or a container's `read`.
typedef OxeeReader = T Function<T>(ProviderListenable<T> provider);

/// Values Oxee sets for the whole app (main.dart's provider container).
/// LibreChat is off: upstream then neither offers it (account sheet,
/// backend chooser) nor shows its cards (Accounts, native Accounts page).
/// Settings is Oxee's ([oxeeSettingsProvider]).
final List<Override> oxeeProviderOverrides = [
  libreChatBackendEnabledProvider.overrideWithValue(false),
  oxeeSettingsProvider.overrideWithValue(true),
];

/// An Oxeegen Intelligence deployment. Keep in step with brand/brand.json;
/// brand/tools/check_brand.py compares the two.
enum OxeeRegion {
  us(label: 'Oxeegen US', url: 'https://ai.oxeegen.com', flag: '🇺🇸'),
  fr(label: 'Oxeegen FR', url: 'https://ia.oxeegen.fr', flag: '🇫🇷');

  const OxeeRegion({
    required this.label,
    required this.url,
    required this.flag,
  });

  final String label;
  final String url;
  final String flag;

  String get host => Uri.parse(url).host;

  OxeeRegion get other =>
      this == OxeeRegion.us ? OxeeRegion.fr : OxeeRegion.us;

  /// The region a saved server belongs to, or null for any other server.
  static OxeeRegion? forServerUrl(String? url) {
    if (url == null) return null;
    final host = Uri.tryParse(url.trim())?.host.toLowerCase();
    if (host == null || host.isEmpty) return null;
    for (final region in values) {
      if (region.host == host) return region;
    }
    return null;
  }
}

/// The region of the server the app is currently using, if it is one of ours.
OxeeRegion? oxeeActiveRegion(WidgetRef ref) => OxeeRegion.forServerUrl(
  ref.watch(activeServerProvider).asData?.value?.url,
);

/// The saved accounts whose server is [region]'s, at any of its addresses.
List<OpenWebUiAccountEntry> oxeeAccountsIn(
  Iterable<OpenWebUiAccountEntry> accounts,
  OxeeRegion region,
) => [
  for (final entry in accounts)
    if (entry.server.endpoints.any(
      (endpoint) => OxeeRegion.forServerUrl(endpoint.url) == region,
    ))
      entry,
];

/// Text the brand layer adds. English and French; other locales get English.
/// Kept out of the ARB files so upstream translation updates never conflict.
class OxeeStrings {
  const OxeeStrings._(this._fr);

  factory OxeeStrings.of(BuildContext context) =>
      OxeeStrings.forLocale(Localizations.localeOf(context));

  factory OxeeStrings.forLocale(Locale locale) =>
      OxeeStrings._(locale.languageCode == 'fr');

  final bool _fr;

  String get welcomeTitle => _fr ? 'Bienvenue dans Oxee' : 'Welcome to Oxee';

  String get chooseRegion => _fr
      ? 'Choisissez la région de votre compte Oxeegen Intelligence.'
      : 'Choose the region of your Oxeegen Intelligence account.';

  String get addAccountTitle =>
      _fr ? 'Ajouter un compte Oxeegen' : 'Add an Oxeegen account';

  String get chooseRegionToAdd => _fr
      ? 'Choisissez la région du compte à ajouter. Le compte actuel reste '
            'connecté.'
      : 'Choose the region of the account to add. Your current account '
            'stays signed in.';

  String get regionsSectionTitle => 'Oxeegen Intelligence';

  /// The account sheet's tab for an Oxeegen Intelligence account (next to
  /// Oxee Hermes).
  String get accountKindTitle => 'Oxeegen';

  String get addAccountRegionPrompt => _fr
      ? 'Choisissez la région du compte à ajouter.'
      : 'Choose the region of the account to add.';

  String get regionTitle => _fr ? 'Région' : 'Region';

  String regionSubtitle(OxeeRegion region) => switch (region) {
    OxeeRegion.us => '${_fr ? 'États-Unis' : 'United States'} · ${region.host}',
    OxeeRegion.fr => 'France · ${region.host}',
  };

  String switchTitle(OxeeRegion to) =>
      _fr ? 'Passer à ${to.label} ?' : 'Switch to ${to.label}?';

  /// [signedIn]: an account in [to] is already saved, so this is a switch;
  /// otherwise it is a sign-in that adds one.
  String switchMessage(
    OxeeRegion? from,
    OxeeRegion to, {
    required bool signedIn,
  }) {
    final String stay;
    if (from == null) {
      stay = '';
    } else if (signedIn) {
      stay = _fr
          ? ' Vous restez connecté à ${from.label} et pouvez revenir ici à '
                'tout moment.'
          : ' You stay signed in to ${from.label} and can switch back here '
                'at any time.';
    } else {
      stay = _fr
          ? ' Votre compte ${from.label} reste connecté, et vous pourrez '
                'passer de l\'un à l\'autre ici.'
          : ' Your ${from.label} account stays signed in, and you can switch '
                'between them here.';
    }
    if (signedIn) {
      return (_fr
              ? 'Oxee passe à votre compte ${to.label}.'
              : 'Oxee switches to your ${to.label} account.') +
          stay;
    }
    return (_fr
            ? 'Vous allez vous connecter à ${to.label}.'
            : 'You will sign in to ${to.label}.') +
        stay;
  }

  String get switchAction => _fr ? 'Changer de région' : 'Switch region';

  String unreachable(OxeeRegion region) => _fr
      ? 'Impossible de joindre ${region.label}. Vérifiez votre connexion et '
            'réessayez.'
      : 'Could not reach ${region.label}. Check your connection and try '
            'again.';
}

/// Begins adding an account and opens the region picker for it, on
/// [region] when given. Upstream's `openAddAccount`, with a region instead of
/// a server: the router lets a signed-in user reach sign-in only while an
/// addition is in progress, and the picker ends it when it goes.
void openOxeeRegionAddAccount(
  BuildContext context,
  WidgetRef ref, [
  OxeeRegion? region,
]) => beginOxeeRegionAddAccount(ref, GoRouter.of(context), region);

/// [openOxeeRegionAddAccount] for callers that close what they were shown in
/// first (the account sheet): take the router before closing, then call this.
void beginOxeeRegionAddAccount(
  WidgetRef ref,
  GoRouter router,
  OxeeRegion? region,
) {
  ref
      .read(accountAdditionOriginProvider.notifier)
      .begin(ref.read(settledActiveAccountIdProvider));
  router.goNamed(RouteNames.addServer, extra: region);
}

/// Switches to the other region: to its saved account when there is one,
/// otherwise by adding one. Either way the current account stays signed in.
Future<void> showOxeeRegionSwitcher(BuildContext context, WidgetRef ref) async {
  final strings = OxeeStrings.of(context);
  final current = OxeeRegion.forServerUrl(
    ref.read(activeServerProvider).asData?.value?.url,
  );
  final target = current?.other ?? OxeeRegion.us;
  List<OpenWebUiAccountEntry> accounts;
  try {
    accounts = await ref.read(openWebUiAccountsProvider.future);
  } catch (_) {
    accounts = const [];
  }
  if (!context.mounted) return;
  final saved = oxeeAccountsIn(accounts, target);

  final confirmed = await ThemedDialogs.confirm(
    context,
    title: strings.switchTitle(target),
    message: strings.switchMessage(
      current,
      target,
      signedIn: saved.isNotEmpty,
    ),
    confirmText: strings.switchAction,
  );
  if (!confirmed || !context.mounted) return;

  if (saved.isEmpty) {
    openOxeeRegionAddAccount(context, ref, target);
    return;
  }
  // One that needs no sign-in, when there is one.
  final account = saved.firstWhere(
    (entry) => entry.hasSession,
    orElse: () => saved.first,
  );
  await switchToSavedAccount(context, ref, account.id);
}

/// Id of the region row in the iOS native settings sheet; main.dart routes
/// its tap to [showOxeeRegionSwitcher].
const String oxeeRegionNativeSheetItemId = 'oxee-region';

/// [read] is `ref.read` of a widget or a provider: the sheet is built from
/// tap handlers and refreshed by the hydration service, never in a build.
NativeSheetItemConfig buildOxeeRegionNativeSheetItem(
  BuildContext context,
  T Function<T>(ProviderListenable<T> provider) read,
) {
  final region = OxeeRegion.forServerUrl(
    read(activeServerProvider).asData?.value?.url,
  );
  return NativeSheetItemConfig(
    id: oxeeRegionNativeSheetItemId,
    title: OxeeStrings.of(context).regionTitle,
    subtitle: region?.label,
    sfSymbol: 'globe',
    dismissOnSelect: true,
    actionId: oxeeRegionNativeSheetItemId,
    actionValue: true,
  );
}

// ---------------------------------------------------------------------------
// Settings (the iOS native sheet, and since upstream 4.3.2 the Flutter pages
// drawn from the same definitions): upstream builds the sections, Oxee
// adjusts the result, so upstream's builders stay unedited.
// ---------------------------------------------------------------------------

bool _isDonationItem(NativeSheetItemConfig item) =>
    item.id == 'buy-me-a-coffee' || item.id == 'github-sponsors';

/// [section] without its donation rows, and without the footer asking for
/// support that comes with them; null when nothing else was in it.
NativeSheetSectionConfig? _withoutDonations(NativeSheetSectionConfig section) {
  if (!section.items.any(_isDonationItem)) return section;
  final items = [
    for (final item in section.items)
      if (!_isDonationItem(item)) item,
  ];
  if (items.isEmpty) return null;
  return NativeSheetSectionConfig(
    title: section.title,
    reorderActionId: section.reorderActionId,
    items: items,
  );
}

/// The Settings root: no donation rows (since upstream 4.3.1 they share
/// About's group, whose support footer goes with them), and the Region row
/// under the account card. [region] builds that row, only when it is shown.
List<NativeSheetSectionConfig> oxeeNativeRootSections(
  OxeeReader read,
  List<NativeSheetSectionConfig> sections, {
  required NativeSheetItemConfig Function() region,
}) {
  if (!read(oxeeSettingsProvider)) return sections;
  final kept = [
    for (final section in sections)
      if (_withoutDonations(section) case final trimmed?) trimmed,
  ];
  if (kept.isEmpty) return kept;
  final card = kept.first;
  return [
    NativeSheetSectionConfig(
      title: card.title,
      footer: card.footer,
      reorderActionId: card.reorderActionId,
      items: [...card.items.take(1), region(), ...card.items.skip(1)],
    ),
    ...kept.skip(1),
  ];
}

/// The About page: no release-notes row (the bundled notes describe
/// upstream's releases, not Oxee's).
List<NativeSheetItemConfig> oxeeNativeAboutItems(
  OxeeReader read,
  List<NativeSheetItemConfig> items,
) => !read(oxeeSettingsProvider)
    ? items
    : [
        for (final item in items)
          if (item.id != NativeSheetRoutes.releaseNotesManual) item,
      ];

/// Push notifications reach a phone through a relay to Apple and Google,
/// whose address a build is given (`CONDUIT_PUSH_RELAY_URL`). Oxeegen runs
/// none yet, so Settings leaves push out rather than show it as "Not
/// available in this build"; a build given a relay shows it again. (The iOS
/// app does not claim push either: see `IDENTITY` in brand/tools/rebrand.py.)
List<NativeSheetSectionConfig> oxeePushSections(
  OxeeReader read,
  List<NativeSheetSectionConfig> sections,
) => read(oxeeSettingsProvider) && kConduitPushRelayUrl.isEmpty
    ? const []
    : sections;

bool _isOtherBackendSection(NativeSheetSectionConfig section) => section.items
    .any((item) => item.id == NativeSheetRoutes.directConnections);

/// The Accounts page: Oxeegen accounts and Oxee Hermes; no Direct card.
/// (Upstream leaves LibreChat's card out itself while LibreChat is off and
/// has no saved account, as [oxeeProviderOverrides] makes it.)
NativeSheetDetailConfig oxeeNativeAccountsDetail(
  OxeeReader read,
  NativeSheetDetailConfig d,
) => !read(oxeeSettingsProvider)
    ? d
    : NativeSheetDetailConfig(
      id: d.id,
      title: d.title,
      subtitle: d.subtitle,
      items: d.items,
      sections: [
        for (final section in d.sections)
          if (!_isOtherBackendSection(section)) section,
      ],
      confirmActionId: d.confirmActionId,
      confirmActionLabel: d.confirmActionLabel,
      maxHeightFraction: d.maxHeightFraction,
      trailingActionId: d.trailingActionId,
      trailingActionSfSymbol: d.trailingActionSfSymbol,
      trailingActionDetailId: d.trailingActionDetailId,
      discardPrompt: d.discardPrompt,
      busy: d.busy,
      announcement: d.announcement,
      edited: d.edited,
      search: d.search,
      calendar: d.calendar,
    );
