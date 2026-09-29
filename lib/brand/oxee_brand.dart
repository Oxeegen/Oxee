// Oxee brand layer: the two Oxeegen Intelligence regions Oxee connects to,
// the strings it adds, and the settings entry that switches region.
// See brand/README.md for every place the layer hooks into upstream code.

import 'package:conduit_core/providers/app_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../core/services/native_sheet_bridge.dart';
import '../l10n/app_localizations.dart';
import '../shared/services/navigation_service.dart';
import '../shared/utils/ui_utils.dart';
import '../shared/widgets/themed_dialogs.dart';

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

  String get regionsSectionTitle => 'Oxeegen Intelligence';

  String get regionTitle => _fr ? 'Région' : 'Region';

  String regionSubtitle(OxeeRegion region) => switch (region) {
    OxeeRegion.us => '${_fr ? 'États-Unis' : 'United States'} · ${region.host}',
    OxeeRegion.fr => 'France · ${region.host}',
  };

  String switchTitle(OxeeRegion to) =>
      _fr ? 'Passer à ${to.label} ?' : 'Switch to ${to.label}?';

  String switchMessage(OxeeRegion? from, OxeeRegion to) {
    if (from == null) {
      return _fr
          ? 'Vous allez vous connecter à ${to.label}.'
          : 'You will sign in to ${to.label}.';
    }
    return _fr
        ? 'Vous serez déconnecté de ${from.label}, puis invité à vous '
              'connecter à ${to.label}. Vos conversations restent sur le '
              'serveur de chaque région.'
        : 'You will be signed out of ${from.label} and asked to sign in to '
              '${to.label}. Your chats stay on each region\'s server.';
  }

  String get switchAction => _fr ? 'Changer de région' : 'Switch region';

  String unreachable(OxeeRegion region) => _fr
      ? 'Impossible de joindre ${region.label}. Vérifiez votre connexion et '
            'réessayez.'
      : 'Could not reach ${region.label}. Check your connection and try '
            'again.';
}

/// Id of the region row in the iOS native settings sheet; main.dart routes
/// its tap to [showOxeeRegionSwitcher].
const String oxeeRegionNativeSheetItemId = 'oxee-region';

NativeSheetItemConfig buildOxeeRegionNativeSheetItem({
  required BuildContext context,
  required WidgetRef ref,
}) {
  // Built from a tap handler, not a build method: read, never watch.
  final region = OxeeRegion.forServerUrl(
    ref.read(activeServerProvider).asData?.value?.url,
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

/// Offers the other region and, once confirmed, signs out and opens its
/// sign-in. Signing in replaces the saved server, so a switch is a sign-out
/// of the current region followed by a sign-in to the other one.
Future<void> showOxeeRegionSwitcher(BuildContext context, WidgetRef ref) async {
  final strings = OxeeStrings.of(context);
  final current = OxeeRegion.forServerUrl(
    ref.read(activeServerProvider).asData?.value?.url,
  );
  final target = current?.other ?? OxeeRegion.us;
  // The router replaces this page once the session ends; keep a handle that
  // outlives it.
  final router = NavigationService.router;

  final confirmed = await ThemedDialogs.confirm(
    context,
    title: strings.switchTitle(target),
    message: strings.switchMessage(current, target),
    confirmText: strings.switchAction,
  );
  if (!confirmed) return;

  try {
    await ref
        .read(signOutCoordinatorProvider)
        .signOut(keepServerDetails: false);
  } catch (_) {
    if (context.mounted) {
      UiUtils.showMessage(context, AppLocalizations.of(context)!.errorMessage);
    }
    return;
  }
  router.go(Routes.serverConnection, extra: target);
}
