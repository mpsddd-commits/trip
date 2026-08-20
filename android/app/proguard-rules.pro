# ---------------------------------------------------------------------------
# 🔴 가장 중요한 규칙
#
# R8 이 @JavascriptInterface 메서드를 제거하면 **release 빌드에서만** 브리지가 죽는다.
# debug 로는 절대 재현되지 않는다. 아래 규칙을 지우지 마세요.
# ---------------------------------------------------------------------------
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# 브리지 폴백 객체 자체도 유지한다 (클래스가 사라지면 메서드 유지가 의미 없다).
-keep class local.trip.app.bridge.LegacyBridge { *; }

# WebView 콜백은 리플렉션 경로로 불릴 수 있다.
-keepclassmembers class * extends android.webkit.WebViewClient { <methods>; }
-keepclassmembers class * extends android.webkit.WebChromeClient { <methods>; }

# 스택 트레이스를 읽을 수 있게 유지한다 (SEC-13 — 단, 매핑 파일은 배포하지 않는다).
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
