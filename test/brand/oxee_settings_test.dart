import 'package:checks/checks.dart';
import 'package:conduit/brand/oxee_brand.dart';
import 'package:conduit/brand/oxee_region_page.dart';
import 'package:conduit/core/services/native_sheet_bridge.dart';
import 'package:conduit/l10n/app_localizations.dart';
import 'package:conduit/l10n/conduit_localizations.dart';
import 'package:conduit_core/auth/openwebui_account_summaries.dart';
import 'package:conduit_core/models/openwebui_registry.dart';
import 'package:conduit_core/providers/app_providers.dart';
import 'package:conduit_core/providers/openwebui_accounts_controller.dart'
    show pendingSignInAbandonableProvider;
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart' show MaterialApp;

NativeSheetItemConfig _item(String id) =>
    NativeSheetItemConfig(id: id, title: id);

OpenWebUiAccountEntry _account(String id, String url, {bool session = true}) =>
    OpenWebUiAccountEntry(
      account: OpenWebUiAccount(id: id, serverId: 'server-$id'),
      server: OpenWebUiServer(
        id: 'server-$id',
        name: id,
        endpoints: [OpenWebUiEndpoint(id: 'endpoint-$id', url: url)],
      ),
      summary: const OpenWebUiAccountSummary(),
      isActive: false,
      hasSession: session,
    );

void main() {
  group('native Settings, as Oxee shows it', () {
    test('the root drops the donations and puts Region under the card', () {
      final sections = oxeeNativeRootSections(
        [
          NativeSheetSectionConfig(
            items: [_item('accounts'), _item('account-add')],
          ),
          NativeSheetSectionConfig(items: [_item('appearance')]),
          NativeSheetSectionConfig(
            title: 'Support',
            items: [_item('buy-me-a-coffee'), _item('github-sponsors')],
          ),
        ],
        region: _item(oxeeRegionNativeSheetItemId),
      );

      check(
        sections.map((s) => s.items.map((i) => i.id).toList()).toList(),
      ).deepEquals([
        ['accounts', oxeeRegionNativeSheetItemId, 'account-add'],
        ['appearance'],
      ]);
    });

    test('the Accounts page keeps Oxeegen accounts only', () {
      final detail = oxeeNativeAccountsDetail(
        NativeSheetDetailConfig(
          id: 'accounts',
          title: 'Accounts',
          trailingActionId: 'account-add',
          sections: [
            NativeSheetSectionConfig(items: [_item('account-server:us')]),
            NativeSheetSectionConfig(items: [_item('accounts-hermes')]),
            NativeSheetSectionConfig(
              items: [_item(NativeSheetRoutes.directConnections)],
            ),
          ],
        ),
      );

      check(detail.id).equals('accounts');
      check(detail.trailingActionId).equals('account-add');
      check(
        detail.sections.expand((s) => s.items).map((i) => i.id).toList(),
      ).deepEquals(['account-server:us']);
    });

    test('About has no release notes', () {
      final items = oxeeNativeAboutItems([
        _item('app-version'),
        _item(NativeSheetRoutes.releaseNotesManual),
        _item(NativeSheetRoutes.openSourceLicenses),
      ]);
      check(items.map((i) => i.id).toList()).deepEquals([
        'app-version',
        NativeSheetRoutes.openSourceLicenses,
      ]);
    });
  });

  test('saved accounts are matched to their region by server address', () {
    final accounts = [
      _account('fred-us', 'https://ai.oxeegen.com'),
      _account('fred-fr', 'https://IA.oxeegen.fr/'),
      _account('other', 'https://open-webui.example'),
    ];
    check(
      oxeeAccountsIn(accounts, OxeeRegion.fr).map((a) => a.id).toList(),
    ).deepEquals(['fred-fr']);
    check(
      oxeeAccountsIn(accounts, OxeeRegion.us).map((a) => a.id).toList(),
    ).deepEquals(['fred-us']);
  });

  group('the region picker, adding an account', () {
    Future<void> pump(WidgetTester tester, {Locale? locale}) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            activeServerProvider.overrideWith((_) async => null),
            pendingSignInAbandonableProvider.overrideWith((_) async => false),
          ],
          child: MaterialApp(
            locale: locale,
            localizationsDelegates: conduitLocalizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const OxeeRegionPage(addingAccount: true),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('says it adds an account and offers Back', (tester) async {
      await pump(tester);

      expect(find.text('Add an Oxeegen account'), findsWidgets);
      expect(
        find.text(
          'Choose the region of the account to add. Your current account '
          'stays signed in.',
        ),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('oxee-region-back')), findsOneWidget);
      expect(find.text('Oxeegen US'), findsOneWidget);
      expect(find.text('Oxeegen FR'), findsOneWidget);
    });

    testWidgets('speaks French on French devices', (tester) async {
      await pump(tester, locale: const Locale('fr'));
      expect(find.text('Ajouter un compte Oxeegen'), findsWidgets);
    });
  });
}
