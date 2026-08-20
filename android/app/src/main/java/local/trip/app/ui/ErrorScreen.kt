package local.trip.app.ui

import android.view.View
import android.webkit.WebView
import local.trip.app.R
import local.trip.app.databinding.ActivityMainBinding

/**
 * A6 OfflineScreen — 앱이 직접 그리는 유일한 화면 (FR-30, ABR-40, ABR-43).
 *
 * 🔴 ABR-41 — **최초 로드 실패에서만** 보인다.
 *    이후의 오류는 u2 의 OfflineGate 가 저장된 일정을 보여준다.
 *    앱이 덮으면 그 기능을 가려 버린다 — 사용자는 저장해 둔 일정을 못 본다.
 */
class ErrorScreen(private val binding: ActivityMainBinding) {

    /** 최초 로드 실패 (ABR-40) — 접속 주소를 함께 보여준다. */
    fun showConnectionFailure(baseUrl: String, detail: String) {
        show(
            title = binding.root.context.getString(R.string.error_offline_title),
            body = binding.root.context.getString(R.string.error_offline_body),
            address = binding.root.context.getString(R.string.error_address_label, baseUrl),
            retryVisible = true,
        )
        if (detail.isNotBlank()) {
            binding.errorMessage.text = binding.errorMessage.text.toString() + "\n\n(" + detail + ")"
        }
    }

    /** ABR-02 — 빌드에 주소가 없다. 재시도해도 소용없으므로 버튼을 감춘다. */
    fun showMissingConfig() {
        val ctx = binding.root.context
        show(
            title = ctx.getString(R.string.error_config_title),
            body = ctx.getString(R.string.error_config_body),
            address = "",
            retryVisible = false,
        )
    }

    /** ABR-03 — 주소를 해석할 수 없다. */
    fun showMalformedConfig(raw: String) {
        val ctx = binding.root.context
        show(
            title = ctx.getString(R.string.error_config_title),
            body = ctx.getString(R.string.error_config_invalid_body),
            address = ctx.getString(R.string.error_address_label, raw),
            retryVisible = false,
        )
    }

    fun hide() {
        binding.errorPanel.visibility = View.GONE
        binding.webView.visibility = View.VISIBLE
    }

    fun onRetry(action: () -> Unit) {
        binding.retryButton.setOnClickListener { action() }
    }

    private fun show(title: String, body: String, address: String, retryVisible: Boolean) {
        binding.errorTitle.text = title
        binding.errorMessage.text = body
        binding.errorAddress.text = address
        binding.errorAddress.visibility = if (address.isBlank()) View.GONE else View.VISIBLE
        binding.retryButton.visibility = if (retryVisible) View.VISIBLE else View.GONE
        binding.errorPanel.visibility = View.VISIBLE
        // WebView 를 감춘다 — 빈 흰 화면이 오류 패널 뒤에 비치지 않게.
        binding.webView.visibility = View.INVISIBLE
        binding.progress.visibility = View.GONE
    }
}

/** 액티비티에서 WebView 를 안전하게 정리한다 (ABR-32). */
fun WebView.releaseSafely() {
    stopLoading()
    // 부모에서 떼기 전에 destroy 하면 렌더러 참조가 남아 크래시가 난다.
    (parent as? android.view.ViewGroup)?.removeView(this)
    removeAllViews()
    destroy()
}
