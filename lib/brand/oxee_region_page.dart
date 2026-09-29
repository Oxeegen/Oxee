// Oxee brand layer: first-run and "change server" screen. Replaces both the
// backend chooser and the free-form server address page, so every path that
// used to ask for a server now asks for an Oxeegen Intelligence region.

import 'package:conduit_core/models/server_config.dart';
import 'package:conduit_core/services/api_service.dart';
import 'package:conduit_core/services/worker_manager.dart';
import 'package:conduit_core/utils/debug_logger.dart';
import 'package:cupertino_ui/cupertino_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:uuid/uuid.dart';

import '../core/services/haptic_service.dart';
import '../l10n/app_localizations.dart';
import '../shared/services/navigation_service.dart';
import '../shared/theme/theme_extensions.dart';
import '../shared/widgets/platform_ui/platform_ui.dart';
import '../shared/widgets/utility_components.dart';
import 'oxee_brand.dart';

class OxeeRegionPage extends ConsumerStatefulWidget {
  const OxeeRegionPage({super.key, this.initialRegion});

  /// Connects to this region as soon as the page opens (region switch from
  /// settings). Null shows the choice.
  final OxeeRegion? initialRegion;

  @override
  ConsumerState<OxeeRegionPage> createState() => _OxeeRegionPageState();
}

class _OxeeRegionPageState extends ConsumerState<OxeeRegionPage> {
  OxeeRegion? _connecting;
  String? _error;

  @override
  void initState() {
    super.initState();
    final initial = widget.initialRegion;
    if (initial != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _connect(initial);
      });
    }
  }

  /// Same checks as upstream's server address page, for a fixed address:
  /// reachable, healthy, really Open WebUI. The server is saved only once
  /// sign-in succeeds, on the authentication page.
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
        case HealthCheckResult.proxyAuthRequired ||
            HealthCheckResult.unreachable:
          throw Exception(strings.unreachable(region));
      }

      final backendConfig = await api.verifyAndGetConfig();
      if (backendConfig == null) throw Exception(l10n.serverNotOpenWebUI);
      if (!mounted) return;

      ConduitHaptics.success();
      context.pushNamed(
        RouteNames.authentication,
        extra: AuthFlowConfig(
          serverConfig: config,
          backendConfig: backendConfig,
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

  @override
  Widget build(BuildContext context) {
    final theme = context.conduitTheme;
    final strings = OxeeStrings.of(context);
    final current = oxeeActiveRegion(ref);

    return UtilityPageScaffold.auth(
      title: strings.welcomeTitle,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Spacing.xs),
            child: Text(
              strings.chooseRegion,
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
                  selected: region == current,
                  showSelectionIndicator: false,
                  trailing: _connecting == region
                      ? const SizedBox.square(
                          dimension: IconSize.medium,
                          child: CircularProgressIndicator(strokeWidth: 2),
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
