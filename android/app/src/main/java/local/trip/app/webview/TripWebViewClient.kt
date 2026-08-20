package local.trip.app.webview

import android.net.http.SslError
import android.util.Log
import android.webkit.SslErrorHandler
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import local.trip.app.config.AppConfig
import local.trip.app.config.Origin

/**
 * 내비게이션·오류 정책 (ABR-14, ABR-15, ABR-41). WF-A2, WF-A8.
 */
class TripWebViewClient(
    private val origin: Origin,
    private val onExternalUrl: (String) -> Unit,
    private val onInitialLoadFailed: (String) -> Unit,
    private val onPageReady: () -> Unit,
) : WebViewClient() {

    /**
     * 최초 로드가 성공했는가.
     *
     * 🔴 ABR-41 — 이 플래그가 켜진 뒤의 오류는 **앱이 화면을 덮지 않는다.**
     *    u2 의 OfflineGate 가 저장된 일정을 보여준다. 앱이 덮으면 그 기능을 가린다.
     */
    private var firstLoadSucceeded = false

    /**
     * ABR-14 — 허용 오리진 밖은 WebView 에서 열지 않고 시스템 브라우저로 내보낸다.
     *
     * 🔴 startsWith(baseUrl) 로 판정하지 않는다 — AppConfig.isSameOrigin 이
     *    스킴·호스트·포트를 각각 비교한다.
     */
    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
        val url = request.url?.toString() ?: return true
        if (AppConfig.isSameOrigin(url, origin)) return false   // WebView 안에서 로드
        onExternalUrl(url)
        return true                                             // 여기서 가로챈다
    }

    override fun onPageFinished(view: WebView, url: String?) {
        super.onPageFinished(view, url)
        firstLoadSucceeded = true
        onPageReady()
    }

    /**
     * ABR-41 — 최초 로드 실패에서만 오류 화면을 띄운다.
     *
     * 메인 프레임의 실패만 본다. 이미지 하나가 404 라고 전체 화면을 덮으면 안 된다.
     */
    override fun onReceivedError(
        view: WebView,
        request: WebResourceRequest,
        error: WebResourceError,
    ) {
        super.onReceivedError(view, request, error)
        if (!request.isForMainFrame) return
        if (firstLoadSucceeded) {
            // u2 가 알아서 처리한다. 앱은 개입하지 않는다.
            Log.i(TAG, "최초 로드 이후의 오류 — 웹에 맡긴다")
            return
        }
        onInitialLoadFailed(error.description?.toString().orEmpty())
    }

    override fun onReceivedHttpError(
        view: WebView,
        request: WebResourceRequest,
        errorResponse: WebResourceResponse,
    ) {
        super.onReceivedHttpError(view, request, errorResponse)
        if (!request.isForMainFrame || firstLoadSucceeded) return
        onInitialLoadFailed("HTTP " + errorResponse.statusCode)
    }

    /**
     * 🔴 ABR-15 — **proceed() 를 절대 호출하지 않는다.**
     *
     * 인증서 오류를 무시하면 TLS 가 아무 의미가 없어진다. 개발 편의를 위해
     * 여기에 예외를 두고 싶어지지만, 그 코드는 반드시 릴리스까지 살아남는다.
     * 개발 환경은 평문 HTTP 를 debug 전용으로 허용하는 쪽(ABR-04)으로 해결한다.
     */
    override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
        Log.w(TAG, "SSL 오류로 연결을 취소했다: " + error.primaryError)
        handler.cancel()
        if (!firstLoadSucceeded) onInitialLoadFailed("SSL")
    }

    private companion object {
        const val TAG = "TripWebViewClient"
    }
}
