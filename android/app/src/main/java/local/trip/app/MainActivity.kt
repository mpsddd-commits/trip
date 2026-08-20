package local.trip.app

import android.os.Bundle
import android.util.Log
import android.view.View
import android.webkit.WebView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import local.trip.app.bridge.BridgeHandler
import local.trip.app.bridge.BridgeProtocol
import local.trip.app.config.AppConfig
import local.trip.app.config.ConfigState
import local.trip.app.config.Origin
import local.trip.app.databinding.ActivityMainBinding
import local.trip.app.intent.IntentLauncher
import local.trip.app.location.LocationProvider
import local.trip.app.ui.BackPressPolicy
import local.trip.app.ui.ErrorScreen
import local.trip.app.ui.releaseSafely
import local.trip.app.webview.DownloadHandler
import local.trip.app.webview.TripWebChromeClient
import local.trip.app.webview.TripWebViewClient
import local.trip.app.webview.WebViewConfigurator

/**
 * A1 MainActivity — WebView 호스트 (FR-27, FR-29, FR-30). WF-A1.
 *
 * 🔴 이 액티비티는 **조립만 한다.** 정책은 각 컴포넌트가 갖는다.
 *    로직을 여기에 모으면 전부 에뮬레이터 없이는 검증할 수 없는 코드가 된다.
 */
class MainActivity : AppCompatActivity(), BridgeHandler.Callbacks {

    private lateinit var binding: ActivityMainBinding
    private lateinit var errorScreen: ErrorScreen
    private lateinit var launcher: IntentLauncher

    private var bridge: BridgeHandler? = null
    private var locationProvider: LocationProvider? = null
    private var baseUrl: String = ""

    private val backPolicy = BackPressPolicy()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        errorScreen = ErrorScreen(binding)
        launcher = IntentLauncher(this)

        // 🔴 ABR-02 / ABR-03 — 주소 검증이 먼저다.
        //    주소가 없거나 이상하면 WebView 를 아예 띄우지 않는다.
        //    빈 흰 화면을 보여주고 사용자가 원인을 추측하게 만들지 않는다.
        when (val state = AppConfig.resolve(BuildConfig.BASE_URL)) {
            is ConfigState.Missing -> {
                Log.e(TAG, "BASE_URL 이 비어 있다 — 빌드 시 releaseBaseUrl 을 지정해야 한다")
                errorScreen.showMissingConfig()
            }

            is ConfigState.Malformed -> {
                Log.e(TAG, "BASE_URL 을 해석할 수 없다")
                errorScreen.showMalformedConfig(state.raw)
            }

            is ConfigState.Valid -> {
                baseUrl = state.baseUrl
                setUpWebView(state.origin)
                registerBackHandler()
                errorScreen.onRetry { reload() }
                binding.webView.loadUrl(state.baseUrl)
            }
        }
    }

    // -----------------------------------------------------------------------
    // WebView 조립 (WF-A1, WF-A2)
    // -----------------------------------------------------------------------

    private fun setUpWebView(origin: Origin) {
        val webView: WebView = binding.webView

        // A2 — 하드닝을 먼저 적용한다. 로드가 시작된 뒤에 켜면 이미 늦다.
        WebViewConfigurator.configure(webView)

        webView.webViewClient = TripWebViewClient(
            origin = origin,
            onExternalUrl = { url -> launcher.openExternal(url) },
            onInitialLoadFailed = { detail -> errorScreen.showConnectionFailure(baseUrl, detail) },
            onPageReady = { onPageReady() },
        )

        webView.webChromeClient = TripWebChromeClient(
            onExternalUrl = { url -> launcher.openExternal(url) },
            onProgress = { progress -> showProgress(progress) },
        )

        // 🔴 이것이 없으면 ics 내보내기 버튼이 **무반응**이 된다 (FR-26).
        webView.setDownloadListener(
            DownloadHandler(
                activity = this,
                origin = origin,
                onFallbackToBrowser = { url -> launcher.openExternal(url) },
            )
        )

        locationProvider = LocationProvider(this)
        bridge = BridgeHandler(webView, origin, this).also { it.attach() }
    }

    private fun onPageReady() {
        errorScreen.hide()
        binding.progress.visibility = View.GONE
        // ABR-33 — 수신부가 없으면 스크립트가 조용히 빠져나간다 (현재 u2 에 소비처 없음).
        bridge?.sendBridgeReady()
    }

    private fun showProgress(progress: Int) {
        binding.progress.progress = progress
        binding.progress.visibility = if (progress in 1..99) View.VISIBLE else View.GONE
    }

    private fun reload() {
        errorScreen.hide()
        binding.webView.loadUrl(baseUrl)
    }

    // -----------------------------------------------------------------------
    // 브리지 콜백 (WF-A3) — 전부 UI 스레드에서 불린다 (BridgeHandler 가 보장, ABR-30)
    // -----------------------------------------------------------------------

    override fun onOpenMap(appUrl: String, webUrl: String) {
        // ABR-20 — URL 을 만들지 않는다. 받은 것을 실행만 한다.
        launcher.openMap(appUrl, webUrl)
    }

    override fun onShare(title: String, text: String, url: String) {
        launcher.share(title, text, url)
    }

    override fun onRequestLocation(requestId: String) {
        val provider = locationProvider
        if (provider == null) {
            // ABR-27 — 어떤 경우에도 회신한다. 미회신은 웹을 8초 이상 묶어 둔다.
            replyLocation(requestId, null, null, denied = false)
            return
        }
        provider.request { outcome ->
            when (outcome) {
                is LocationProvider.Outcome.Available ->
                    replyLocation(requestId, outcome.lat, outcome.lng, denied = false)

                // 🔴 ABR-26 — 거부는 오류가 아니다. 웹이 해당 기능만 끄면 된다.
                LocationProvider.Outcome.Denied ->
                    replyLocation(requestId, null, null, denied = true)

                // 위치 서비스가 꺼져 있거나 좌표를 못 얻었다. 거부와는 다른 상황이다.
                LocationProvider.Outcome.Unavailable ->
                    replyLocation(requestId, null, null, denied = false)
            }
        }
    }

    private fun replyLocation(requestId: String, lat: Double?, lng: Double?, denied: Boolean) {
        bridge?.send(
            BridgeProtocol.Inbound.LocationResult(
                requestId = requestId,
                lat = lat,
                lng = lng,
                denied = denied,
            )
        )
    }

    // -----------------------------------------------------------------------
    // 뒤로가기 (WF-A9, ABR-42)
    // -----------------------------------------------------------------------

    private fun registerBackHandler() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                val webView = binding.webView
                if (webView.canGoBack()) {
                    backPolicy.reset()
                    webView.goBack()
                    return
                }
                when (backPolicy.onBackAtTop(System.currentTimeMillis())) {
                    BackPressPolicy.Decision.WARN ->
                        Toast.makeText(
                            this@MainActivity,
                            R.string.toast_back_to_exit,
                            Toast.LENGTH_SHORT,
                        ).show()

                    BackPressPolicy.Decision.EXIT -> finish()
                }
            }
        })
    }

    // -----------------------------------------------------------------------
    // 수명 (ABR-32)
    // -----------------------------------------------------------------------

    override fun onDestroy() {
        bridge?.detach()
        bridge = null
        locationProvider?.dispose()
        locationProvider = null
        if (this::binding.isInitialized) binding.webView.releaseSafely()
        super.onDestroy()
    }

    private companion object {
        const val TAG = "TripMain"
    }
}
