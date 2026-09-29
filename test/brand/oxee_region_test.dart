import 'dart:convert';
import 'dart:io';

import 'package:checks/checks.dart';
import 'package:conduit/brand/oxee_brand.dart';
import 'package:conduit/brand/oxee_region_page.dart';
import 'package:conduit/l10n/app_localizations.dart';
import 'package:conduit/l10n/conduit_localizations.dart';
import 'package:conduit/shared/widgets/utility_components.dart';
import 'package:conduit_core/models/server_config.dart';
import 'package:conduit_core/providers/app_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

Future<void> _pumpRegionPage(
  WidgetTester tester, {
  ServerConfig? active,
  Locale locale = const Locale('en'),
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [activeServerProvider.overrideWith((_) async => active)],
      child: MaterialApp(
        locale: locale,
        localizationsDelegates: conduitLocalizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: const OxeeRegionPage(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('OxeeRegion', () {
    test('matches brand/brand.json', () {
      final brand =
          jsonDecode(File('brand/brand.json').readAsStringSync())
              as Map<String, dynamic>;
      final regions = brand['regions'] as Map<String, dynamic>;
      check(regions.keys.toSet()).deepEquals(
        OxeeRegion.values.map((r) => r.name).toSet(),
      );
      for (final region in OxeeRegion.values) {
        final entry = regions[region.name] as Map<String, dynamic>;
        check(region.label).equals(entry['label'] as String);
        check(region.url).equals(entry['url'] as String);
      }
    });

    test('points at the two Oxeegen Intelligence servers', () {
      check(OxeeRegion.us.url).equals('https://ai.oxeegen.com');
      check(OxeeRegion.fr.url).equals('https://ia.oxeegen.fr');
      check(OxeeRegion.us.other).equals(OxeeRegion.fr);
      check(OxeeRegion.fr.other).equals(OxeeRegion.us);
    });

    test('recognises a saved server by host only', () {
      check(OxeeRegion.forServerUrl('https://ai.oxeegen.com')).equals(
        OxeeRegion.us,
      );
      check(OxeeRegion.forServerUrl('https://AI.oxeegen.com/')).equals(
        OxeeRegion.us,
      );
      check(OxeeRegion.forServerUrl(' https://ia.oxeegen.fr/api ')).equals(
        OxeeRegion.fr,
      );
      check(OxeeRegion.forServerUrl('https://open-webui.example')).isNull();
      check(OxeeRegion.forServerUrl('ai.oxeegen.com')).isNull();
      check(OxeeRegion.forServerUrl(null)).isNull();
    });
  });

  group('OxeeRegionPage', () {
    testWidgets('offers exactly the two Oxeegen regions', (tester) async {
      await _pumpRegionPage(tester);

      expect(find.text('Welcome to Oxee'), findsWidgets);
      expect(find.text('Oxeegen US'), findsOneWidget);
      expect(find.text('Oxeegen FR'), findsOneWidget);
      expect(find.text('United States · ai.oxeegen.com'), findsOneWidget);
      expect(find.text('France · ia.oxeegen.fr'), findsOneWidget);
      // Upstream's other backends are not offered.
      expect(find.text('Hermes Agent'), findsNothing);
      expect(find.text('Connect directly'), findsNothing);
    });

    testWidgets('speaks French on French devices', (tester) async {
      await _pumpRegionPage(tester, locale: const Locale('fr'));

      expect(find.text('Bienvenue dans Oxee'), findsWidgets);
      expect(find.text('États-Unis · ai.oxeegen.com'), findsOneWidget);
    });

    testWidgets('marks the region of the saved server', (tester) async {
      await _pumpRegionPage(
        tester,
        active: const ServerConfig(
          id: 'fr',
          name: 'Oxeegen FR',
          url: 'https://ia.oxeegen.fr',
          isActive: true,
        ),
      );

      UtilitySelectionRow row(String key) =>
          tester.widget<UtilitySelectionRow>(find.byKey(ValueKey(key)));
      check(row('oxee-region-fr').selected).isTrue();
      check(row('oxee-region-us').selected).isFalse();
    });
  });
}
