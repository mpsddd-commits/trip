package local.trip.app.bridge

import android.util.Log
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import local.trip.app.config.Origin
import org.json.JSONObject

/**
 * A3 `BridgeHandler` — 웹 ↔ 네이티브 메시지 중계 (FR-28).
 *
 * 두 경로를 지원한다 (Q8=A):
 *   ① `WebViewCompat.addWebMessageListener` — **오리진 허용목록을 프레임워크가 강제**한다. 우선.
 *   ② `@JavascriptInterface` 폴백 — 기기가 ①을 지원하지 않을 때.
 *
 * 🔴 u2 입장에서 두 경로는 **구분되지 않는다.** 둘 다 `window.tripBridge.postMessage(string)` 을
 *    만든다. u2 의 `isNative()` 가 보는 것이 정확히 그것이다.
 *
 * 🔴 SEC-08 — 폴백 경로(②)에는 프레임워크의 오리진 강제가 없다. 대신
 *    `TripWebViewClient` 가 허용 오리진 밖 내비게이션을 아예 차단하므로(ABR-14)
 *    WebView 안에 다른 오리진의 페이지가 뜨지 않는다. 노출 범위는 ①과 같다.
 */
class BridgeHandler(
    private val webView: WebView,
    private val origin: Origin,
    private val callbacks: Callbacks,
) {

    interface Callbacks {
        fun onOpenMap(appUrl: String, webUrl: String)
        fun onShare(title: String, text: String, url: String)
        fun onRequestLocation(requestId: String)
    }

    /** ①이 실제로 쓰였는지. 로그·진단용. */
    var usingWebMessageListener: Boolean = false
        private set

    private var legacyAttached = false

    // -----------------------------------------------------------------------
    // 부착 / 해제
    // -----------------------------------------------------------------------

    fun attach() {
        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            // 프레임워크가 오리진을 검사한다. 허용 규칙 밖에서 온 메시지는 콜백에 도달하지 않는다.
            WebViewCompat.addWebMessageListener(
                webView,
                BridgeProtocol.JS_OBJECT_NAME,
                setOf(origin.toRule()),
            ) { _, message, sourceOrigin, isMainFrame, _ ->
                // 이중 확인: 메인 프레임에서 온 것만 받는다.
                // 광고·위젯 iframe 이 브리지를 호출하는 경로를 남기지 않는다.
                if (!isMainFrame) {
                    Log.w(TAG, "메인 프레임이 아닌 곳에서 온 메시지를 버렸다: $sourceOrigin")
                    return@addWebMessageListener
                }
                dispatch(message.data)
            }
            usingWebMessageListener = true
            Log.i(TAG, "브리지 부착: WebMessageListener (오리진 ${origin.toRule()})")
        } else {
            @Suppress("DEPRECATION")
            webView.addJavascriptInterface(LegacyBridge(this), BridgeProtocol.JS_OBJECT_NAME)
            legacyAttached = true
            Log.i(TAG, "브리지 부착: JavascriptInterface 폴백 (레거시 경로)")
        }
    }

    fun detach() {
        if (legacyAttached) {
            webView.removeJavascriptInterface(BridgeProtocol.JS_OBJECT_NAME)
            legacyAttached = false
        }
        if (usingWebMessageListener &&
            WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)
        ) {
            runCatching {
                WebViewCompat.removeWebMessageListener(webView, BridgeProtocol.JS_OBJECT_NAME)
            }
            usingWebMessageListener = false
        }
    }

    // -----------------------------------------------------------------------
    // 수신
    // -----------------------------------------------------------------------

    /**
     * 🔴 ABR-30 — **UI 스레드로 넘긴 뒤** 처리한다.
     *
     *   · `addWebMessageListener` 콜백은 UI 스레드에서 온다.
     *   · **`@JavascriptInterface` 콜백은 WebView 의 전용 바인더 스레드에서 온다.**
     *     그 스레드에서 WebView·액티비티를 만지면 예외가 나거나 조용히 어긋난다.
     *
     * 두 경로를 여기서 하나로 모아 항상 UI 스레드로 올린다.
     */
    internal fun dispatch(payload: String?) {
        webView.post {
            val message = BridgeProtocol.parse(payload)
            if (message == null) {
                // ABR-25 — 무시하고 로그만. 예외를 던지면 리스너가 죽고
                // 그 뒤 모든 메시지가 사라진다.
                Log.w(TAG, "해석할 수 없는 브리지 메시지를 버렸다")
                return@post
            }
            when (message) {
                is BridgeProtocol.Outbound.OpenMap ->
                    callbacks.onOpenMap(message.appUrl, message.webUrl)

                is BridgeProtocol.Outbound.Share ->
                    callbacks.onShare(message.title, message.text, message.url)

                is BridgeProtocol.Outbound.RequestLocation ->
                    callbacks.onRequestLocation(message.requestId)
            }
        }
    }

    // -----------------------------------------------------------------------
    // 송신
    // -----------------------------------------------------------------------

    /**
     * ABR-30 / ABR-31 — 웹으로 회신한다.
     *
     * 값은 `JSONObject` 로 조립하고 스크립트에 넣을 때 `JSONObject.quote` 로 감싼다.
     * 장소명에 따옴표나 개행이 있어도 스크립트가 깨지지 않는다.
     */
    fun send(message: BridgeProtocol.Inbound) {
        val json = BridgeProtocol.encode(message)
        val script = buildScript(json)
        webView.post {
            webView.evaluateJavascript(script) { /* 반환값을 쓰지 않는다 */ }
        }
    }

    /**
     * ABR-33 — 페이지 로드 완료 후 1회.
     *
     * ⚠️ **현재 u2 에는 이 메시지의 소비처가 없다.**
     *    u2 의 `__tripBridgeReceive` 는 `requestLocation()` 이 처음 호출될 때 비로소 설치되고,
     *    설치되더라도 `locationResult` 외의 타입을 무시한다.
     *    계약(UD-4)에 정의된 메시지이므로 **삭제하지 않고** 유지하되,
     *    수신부가 없을 때 조용히 넘어가도록 `buildScript` 가 가드를 넣는다.
     */
    fun sendBridgeReady() {
        send(BridgeProtocol.Inbound.BridgeReady())
    }

    private fun buildScript(json: String): String {
        // JSONObject.quote 가 따옴표를 포함한 **JS 문자열 리터럴**을 만들어 준다.
        val literal = JSONObject.quote(json)
        return """
            (function () {
              var receive = window.${BridgeProtocol.JS_RECEIVER};
              if (typeof receive !== 'function') { return; }
              try { receive($literal); } catch (e) { }
            })();
        """.trimIndent()
    }

    /**
     * `@JavascriptInterface` 폴백 객체.
     *
     * 🔴 노출 메서드는 `postMessage` **하나뿐이다.** 늘리지 않는다 (SEC-11).
     * 🔴 R8 이 이 클래스를 지우면 release 에서만 브리지가 죽는다 — `proguard-rules.pro` 참조.
     */
    class LegacyBridge(private val handler: BridgeHandler) {
        @JavascriptInterface
        fun postMessage(payload: String?) {
            // 이 호출은 **UI 스레드가 아니다.** dispatch 가 UI 스레드로 올린다 (ABR-30).
            handler.dispatch(payload)
        }
    }

    private companion object {
        const val TAG = "TripBridge"
    }
}
