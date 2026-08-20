package local.trip.app.webview

import android.os.Message
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient

/**
 * ABR-22 — window.open 가로채기. WF-A6.
 *
 * 🔴 문제:
 *    WebView 는 setSupportMultipleWindows(true) 와 onCreateWindow 없이는
 *    window.open 을 **조용히 무시**한다. 오류도 나지 않는다.
 *    u2 의 딥링크 웹 폴백이 window.open 을 쓰므로, 브리지 전달이 실패하면
 *    사용자는 아무 반응도 보지 못한다 (FR-24 의 최후 경로가 사라진다).
 *
 * 🔴 해법:
 *    새 창을 실제로 띄우지 않는다. 임시 WebView 를 만들어 URL 만 뽑고 즉시 파기한 뒤
 *    시스템 브라우저로 넘긴다. 진짜 새 창을 유지하면 뒤로가기·수명 관리가 복잡해지고
 *    "네이티브 UI 최소화"(ABR-43) 원칙에도 어긋난다.
 */
class TripWebChromeClient(
    private val onExternalUrl: (String) -> Unit,
    private val onProgress: (Int) -> Unit,
) : WebChromeClient() {

    override fun onCreateWindow(
        view: WebView,
        isDialog: Boolean,
        isUserGesture: Boolean,
        resultMsg: Message?,
    ): Boolean {
        val transport = resultMsg?.obj as? WebView.WebViewTransport ?: return false

        // URL 을 받아내기 위한 일회용 WebView. 화면에 붙이지 않는다.
        val probe = WebView(view.context)
        probe.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                probeView: WebView,
                request: android.webkit.WebResourceRequest,
            ): Boolean {
                request.url?.toString()?.let(onExternalUrl)
                destroyProbe(probeView)
                return true
            }

            @Deprecated("API 23 미만 경로 — minSdk 26 이지만 일부 WebView 구현이 여전히 호출한다")
            @Suppress("OverridingDeprecatedMember", "DEPRECATION")
            override fun shouldOverrideUrlLoading(probeView: WebView, url: String?): Boolean {
                url?.let(onExternalUrl)
                destroyProbe(probeView)
                return true
            }
        }

        transport.webView = probe
        resultMsg.sendToTarget()
        return true
    }

    override fun onProgressChanged(view: WebView, newProgress: Int) {
        onProgress(newProgress)
    }

    private fun destroyProbe(probe: WebView) {
        // post 로 미루는 이유: 콜백 안에서 즉시 destroy 하면 WebView 내부가 자기 자신을
        // 참조하는 중이라 크래시가 난다.
        probe.post {
            probe.stopLoading()
            probe.destroy()
        }
    }
}
