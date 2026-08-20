package local.trip.app.webview

import android.annotation.SuppressLint
import android.webkit.WebSettings
import android.webkit.WebView
import local.trip.app.BuildConfig

/**
 * A2 WebViewConfigurator — 하드닝 일괄 적용 (SEC-09, Q4=A).
 *
 * 🔴 이 파일이 WebView 설정의 **유일한 지점**이다.
 *    다른 곳에서 webView.settings 를 만지면 하드닝이 어디서 풀렸는지 추적할 수 없다.
 *    StructureTest 가 이 파일 밖의 settings 접근을 검사한다.
 */
object WebViewConfigurator {

    @SuppressLint("SetJavaScriptEnabled")
    fun configure(webView: WebView) {
        val settings = webView.settings

        // --- 켜는 것 -------------------------------------------------------
        // u2 는 React SPA 다. 자바스크립트 없이는 아무것도 뜨지 않는다.
        settings.javaScriptEnabled = true

        // 🔴 ABR-12 — 끄면 안 된다.
        //    u2 의 오프라인 캐시(FR-31)가 IndexedDB 를 쓴다. 끄면 저장된 일정이
        //    **앱에서만** 사라진다. 브라우저에서는 멀쩡해서 원인을 찾기 어렵다.
        settings.domStorageEnabled = true

        // ABR-22 — window.open 을 가로채려면 켜야 한다.
        // 끄면 WebView 가 window.open 을 **조용히 무시**하고, 딥링크 웹 폴백이 죽는다.
        settings.setSupportMultipleWindows(true)
        settings.javaScriptCanOpenWindowsAutomatically = true

        // 뷰포트 — u2 가 반응형이므로 WebView 의 자체 축소를 끈다.
        settings.loadWithOverviewMode = false
        settings.useWideViewPort = true
        settings.builtInZoomControls = false
        settings.displayZoomControls = false

        // u2 가 앱 여부를 보조적으로 판단할 수 있게 표시를 남긴다.
        settings.userAgentString = settings.userAgentString + " TripApp/" + BuildConfig.VERSION_NAME

        // --- 끄는 것 (ABR-10, ABR-11, ABR-13) ------------------------------
        // 로컬 파일·콘텐츠 프로바이더 접근을 전부 차단한다.
        // 브리지가 뚫렸을 때 파일 유출로 이어지는 경로를 없앤다.
        settings.allowFileAccess = false
        settings.allowContentAccess = false

        @Suppress("DEPRECATION")
        settings.allowFileAccessFromFileURLs = false

        @Suppress("DEPRECATION")
        settings.allowUniversalAccessFromFileURLs = false

        // HTTPS 페이지가 HTTP 리소스를 끌어오지 못하게 한다 (SEC-05).
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW

        // 🔴 ABR-13 — 위치는 **브리지 경로로만** 처리한다.
        //    켜 두면 WebView 가 자체 권한 대화상자를 띄워 요청 경로가 둘이 된다.
        //    사용자는 같은 권한을 두 번 묻는 앱을 보게 된다.
        settings.setGeolocationEnabled(false)

        settings.databaseEnabled = true
        settings.mediaPlaybackRequiresUserGesture = true
        settings.saveFormData = false

        // 캐시는 기본 정책을 따른다. u2 가 자체 캐시 전략을 갖고 있으므로 개입하지 않는다.
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // --- 디버깅 (ABR-16) -----------------------------------------------
        // release 에서 켜면 USB 로 연결한 누구나 페이지 내용을 들여다볼 수 있다.
        WebView.setWebContentsDebuggingEnabled(BuildConfig.WEBVIEW_DEBUG)
    }
}
