// Oxee's account sheet (Settings → Accounts → Add Account): an Oxeegen
// Intelligence account, picked by region, or an Oxee Hermes connection.
// Replaces upstream's test/features/profile/account_sheet_test.dart (see
// brand/upstream-tests-replaced.txt).

import 'package:checks/checks.dart';
import 'package:conduit/brand/oxee_brand.dart';
import 'package:conduit/features/profile/widgets/account_sheet.dart';
import 'package:conduit/l10n/app_localizations.dart';
import 'package:conduit/l10n/conduit_localizations.dart';
import 'package:conduit_core/conduit_core.dart';
import 'package:conduit_core/features/hermes/models/hermes_connection_profile.dart';
import 'package:conduit_core/navigation/routes.dart';
import 'package:conduit_core/persistence/persistence_keys.dart';
import 'package:conduit_core/persistence/preferences_store.dart';
import 'package:conduit_core/providers/app_providers.dart';
import 'package:conduit_core/providers/openwebui_accounts_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

const _home = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

final class _SettledOnAlex extends SettledActiveAccountId {
  @override
  String? build() => 'alex-home';
}

void main() {
  late GoRouter router;

  setUp(() {
    // Other tests share this isolate when CI runs them in shards.
    addTearDown(PreferencesStore.debugReset);
    PreferencesStore.debugOverride(
      InMemoryKeyValueStore(<String, Object?>{
        PreferenceKeys.hermesEnabled: false,
        PreferenceKeys.hermesConnections: HermesConnectionsDocument(
          connections: const [
            HermesConnectionProfile(
              id: _home,
              name: 'Home agent',
              baseUrl: 'https://home.example',
              documentTrustPrincipalId: 'aaaaaaaa-0000-4000-8000-000000000000',
            ),
          ],
        ).encode(),
        PreferenceKeys.hermesActiveConnectionId: _home,
      }),
    );
  });

  Future<ProviderContainer> pumpSheet(
    WidgetTester tester, [
    AccountSheetRequest request = const AddAccountRequest(),
  ]) async {
    tester.view.physicalSize = const Size(1200, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (context, _) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () => showAccountSheet(context, request),
                child: const Text('open'),
              ),
            ),
          ),
        ),
        GoRoute(
          path: Routes.addServer,
          name: RouteNames.addServer,
          builder: (_, state) =>
              Text('add in ${(state.extra as OxeeRegion?)?.name}'),
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          secureStorageProvider.overrideWithValue(
            InMemorySecureKeyValueStore({'hermes_api_key_v1:$_home': 'key'}),
          ),
          openWebUiAccountsProvider.overrideWith((ref) async => const []),
          settledActiveAccountIdProvider.overrideWith(_SettledOnAlex.new),
          reviewerModeProvider.overrideWithValue(false),
          // As main.dart sets it for the app.
          ...oxeeProviderOverrides,
        ],
        child: MaterialApp.router(
          localizationsDelegates: conduitLocalizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          routerConfig: router,
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    return ProviderScope.containerOf(tester.element(find.text('open')));
  }

  Finder tab(String label) => find.descendant(
    of: find.byKey(const Key('account-sheet-kind')),
    matching: find.text(label),
  );

  testWidgets('an addition offers Oxeegen and Oxee Hermes, nothing else', (
    tester,
  ) async {
    await pumpSheet(tester);

    expect(find.text('Add Account'), findsOne);
    expect(tab('Oxeegen'), findsOne);
    expect(tab('Oxee Hermes'), findsOne);
    for (final hidden in ['Open WebUI', 'Direct', 'LibreChat']) {
      expect(tab(hidden), findsNothing);
    }
    // The Oxeegen tab is the region choice, not a server address form.
    expect(find.byKey(const ValueKey('oxee-region-add-choices')), findsOne);
    expect(find.text('Oxeegen US'), findsOne);
    expect(find.text('Oxeegen FR'), findsOne);
    expect(find.byKey(const Key('account-sheet-openwebui')), findsNothing);
  });

  testWidgets('a region closes the sheet and adds an account there', (
    tester,
  ) async {
    final container = await pumpSheet(tester);

    await tester.tap(find.byKey(const ValueKey('oxee-region-add-fr')));
    await tester.pumpAndSettle();

    expect(find.byType(AccountSheet), findsNothing);
    expect(find.text('add in fr'), findsOne);
    // The addition began from the account in use, for the router to leave
    // its sign-in alone.
    check(container.read(accountAdditionOriginProvider)).equals('alex-home');
  });

  testWidgets('the Oxee Hermes tab connects an agent', (tester) async {
    await pumpSheet(tester);

    await tester.tap(tab('Oxee Hermes'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('account-sheet-hermes')), findsOne);
    expect(
      find.byKey(const ValueKey<String>('hermes-server-url-field')),
      findsOne,
    );
  });

  testWidgets('says it in French on French devices', (tester) async {
    tester.platformDispatcher.localesTestValue = const [Locale('fr')];
    addTearDown(tester.platformDispatcher.clearLocalesTestValue);
    await pumpSheet(tester);

    expect(tab('Oxeegen'), findsOne);
    expect(tab('Oxee Hermes'), findsOne);
    expect(
      find.text('Choisissez la région du compte à ajouter.'),
      findsOne,
    );
  });
}
