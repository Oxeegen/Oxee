import 'package:flutter/foundation.dart';

const appleAppStoreReviewUrl =
    '';
const googlePlayStoreUrl =
    'https://play.google.com/store/apps/details?id=com.oxeegen.oxee';

String reviewUrlForPlatform([TargetPlatform? platform]) {
  final resolved = platform ?? defaultTargetPlatform;
  return switch (resolved) {
    TargetPlatform.iOS || TargetPlatform.macOS => appleAppStoreReviewUrl,
    _ => googlePlayStoreUrl,
  };
}
