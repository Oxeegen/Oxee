// Oxee brand layer: first-run, "change server" and "add account" screen.
// Replaces the backend chooser and the free-form server address page, so
// every path that used to ask for a server now asks for an Oxeegen
// Intelligence region.
//
// Platform UI seam (tool/platform_ui_lint.dart): no material_ui or
// cupertino_ui imports; controls come from the platform_ui facade.

import 'dart:async';

import 'package:conduit_core/models/server_config.dart';
import 'package:conduit_core/providers/openwebui_accounts_controller.dart'
    show accountAdditionOriginProvider, pendingSignInAbandonableProvider;
import 'package:conduit_core/services/api_service.dart';
import 'package:conduit_core/services/worker_manager.dart';
import 'package:conduit_core/utils/debug_logger.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';

import '../core/services/haptic_service.dart';
import '../features/profile/widgets/account_actions.dart'
    show abandonAddedAccount;
import '../l10n/app_localizations.dart';
import '../shared/services/navigation_service.dart';
import '../shared/theme/theme_extensions.dart';
import '../shared/widgets/platform_ui/platform_ui.dart';
import '../shared/widgets/platform_ui/vocabulary.dart';
import '../shared/widgets/utility_components.dart';
import 'oxee_brand.dart';

class OxeeRegionPage extends ConsumerStatefulWidget {
  const OxeeRegionPage({
    super.key,
    this.initialRegion,
    this.addingAccount = false,
  });

  /// Connects to this region as soon as the page opens. Null shows the
  /// choice.
  final OxeeRegion? initialRegion;

  /// Adding an account next to the signed-in one (Settings' Add account, the
  /// Region row): the addition began before this page opened, and this page
  /// ends it when it goes, as upstream's server connection page does.
  final bool addingAccount;

  @override
  ConsumerState<OxeeRegionPage> createState() => _OxeeRegionPageState();
}

class _OxeeRegionPageState extends ConsumerState<OxeeRegionPage> {
  OxeeRegion? _connecting;
  String? _error;
  bool _goingBack = false;
  void Function()? _endAccountAddition;

  @override
  void initState() {
    super.initState();
    if (widget.addingAccount) {
      _endAccountAddition = ref
          .read(accountAdditionOriginProvider.notifier)
          .endLater();
    }
    final initial = widget.initialRegion;
    if (initial != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _connect(initial);
      });
    }
  }

  @override
  void dispose() {
    final endAccountAddition = _endAccountAddition;
    if (endAccountAddition != null) {
      // Not while the tree unmounts: Riverpod forbids changing provider state
      // from a widget lifecycle callback.
      Future.microtask(endAccountAddition);
    }
    super.dispose();
  }

  /// Same checks as upstream's server address page, for a fixed address:
  /// reachable, healthy, really Open WebUI. The server is saved only once
  /// sign-in succeeds, on the authentication page (which adds the account
  /// when an addition is in progress).
  Future<void> _connect(OxeeRegion region) async {
    if (_connecting != null) return;
    final l10n = AppLocalizations.of(context)!;
    final strings = OxeeStrings.of(context);
    setState(() {
      _connecting = region;
      _error = null;
    });

    ApiService? api;
    try {
      final config = ServerConfig(
        id: const Uuid().v4(),
        name: region.label,
        url: region.url,
        isActive: true,
      );
      api = ApiService(
        serverConfig: config,
        workerManager: ref.read(workerManagerProvider),
      );

      final health = await api.checkHealthWithProxyDetection(
        throwOnConnectionError: true,
      );
      switch (health) {
        case HealthCheckResult.healthy:
          break;
        case HealthCheckResult.unhealthy:
          throw Exception(l10n.serverErrorUnavailable);
        case HealthCheckResult.notOpenWebUI:
          throw Exception(l10n.serverNotOpenWebUI);
        case HealthCheckResult.proxyAuthRequired ||
            HealthCheckResult.unreachable:
          throw Exception(strings.unreachable(region));
      }

      final backendConfig = await api.verifyAndGetConfig();
      if (backendConfig == null) throw Exception(l10n.serverNotOpenWebUI);
      if (!mounted) return;

      ConduitHaptics.success();
      unawaited(
        context.pushNamed(
          RouteNames.authentication,
          extra: AuthFlowConfig(
            serverConfig: config,
            backendConfig: backendConfig,
          ),
        ),
      );
    } catch (e) {
      DebugLogger.error(
        'oxee-region-connect-error',
        scope: 'auth/connection',
        data: {'region': region.name, 'errorType': e.runtimeType.toString()},
      );
      if (mounted) {
        setState(() => _error = strings.unreachable(region));
        ConduitHaptics.error();
      }
    } finally {
      api?.dispose();
      if (mounted) setState(() => _connecting = null);
    }
  }

  Future<void> _goBack() async {
    if (_goingBack) return;
    _goingBack = true;
    try {
      await _leave();
    } finally {
      _goingBack = false;
    }
  }

  /// Back while adding an account, as upstream's page does it: an added
  /// account whose sign-in never finished is dropped (the one it was added
  /// from becomes active again); otherwise back to where adding began.
  Future<void> _leave() async {
    final l10n = AppLocalizations.of(context)!;
    final bool abandonable;
    try {
      abandonable = await ref.read(pendingSignInAbandonableProvider.future);
    } catch (_) {
      // Not known whether the added account is still there, signed out:
      // leaving could leave it active. Stay, say so, let Back be pressed again.
      if (mounted) setState(() => _error = l10n.errorMessage);
      return;
    }
    if (!mounted) return;
    if (abandonable) {
      if (!await abandonAddedAccount(context, ref) && mounted) {
        setState(() => _error = l10n.errorMessage);
      }
      return;
    }
    if (context.canPop()) {
      context.pop();
      return;
    }
    context.go(Routes.chat);
  }

  @override
  Widget build(BuildContext context) {
    final theme = context.conduitTheme;
    final l10n = AppLocalizations.of(context)!;
    final strings = OxeeStrings.of(context);
    final current = oxeeActiveRegion(ref);
    final adding = widget.addingAccount;
    // Kept current for Back, which waits for it.
    if (adding) ref.watch(pendingSignInAbandonableProvider);

    final scaffold = UtilityPageScaffold.auth(
      title: adding ? strings.addAccountTitle : strings.welcomeTitle,
      backNavigation: adding
          ? UtilityBackNavigation(
              label: l10n.back,
              buttonKey: const ValueKey<String>('oxee-region-back'),
              onPressed: _goBack,
            )
          : null,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Spacing.xs),
            child: Text(
              adding ? strings.chooseRegionToAdd : strings.chooseRegion,
              style: AppTypography.bodyMediumStyle.copyWith(
                color: theme.textSecondary,
              ),
            ),
          ),
          const SizedBox(height: Spacing.lg),
          InsetGroupedList(
            title: strings.regionsSectionTitle,
            dividerIndent: _dividerIndent,
            children: [
              for (final region in OxeeRegion.values)
                UtilitySelectionRow(
                  key: ValueKey<String>('oxee-region-${region.name}'),
                  leading: _RegionFlag(region: region),
                  title: region.label,
                  subtitle: strings.regionSubtitle(region),
                  selected: !adding && region == current,
                  showSelectionIndicator: false,
                  trailing: _connecting == region
                      ? const SizedBox.square(
                          dimension: IconSize.medium,
                          child: AdaptiveProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(
                          context.usesCupertinoChrome
                              ? CupertinoIcons.chevron_forward
                              : Icons.chevron_right,
                          color: theme.iconSecondary,
                          size: IconSize.small,
                        ),
                  onTap: () => _connect(region),
                ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: Spacing.md),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.xs),
              child: Text(
                _error!,
                key: const ValueKey<String>('oxee-region-error'),
                style: AppTypography.bodyMediumStyle.copyWith(
                  color: theme.error,
                ),
              ),
            ),
          ],
        ],
      ),
    );

    if (!adding) return scaffold;
    // Adding is the router's location, with nothing beneath it to pop to, so
    // the system back does what Back does rather than leave the app.
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _goBack();
      },
      child: scaffold,
    );
  }
}

const double _flagSize = 40;
const double _dividerIndent = Spacing.md + _flagSize + Spacing.sm + Spacing.xs;

class _RegionFlag extends StatelessWidget {
  const _RegionFlag({required this.region});

  final OxeeRegion region;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: _flagSize,
      height: _flagSize,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: context.conduitTheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(AppBorderRadius.md),
      ),
      child: Text(
        region.flag,
        style: const TextStyle(fontSize: 22),
        semanticsLabel: '',
      ),
    );
  }
}
