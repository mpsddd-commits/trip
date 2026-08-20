package local.trip.app.webview

import android.app.Activity
import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.util.Log
import android.webkit.CookieManager
import android.webkit.DownloadListener
import android.webkit.URLUtil
import android.widget.Toast
import local.trip.app.R
import local.trip.app.config.AppConfig
import local.trip.app.config.Origin

/**
 * ABR-23 / ABR-24 — 다운로드 처리 (FR-26). WF-A5.
 *
 * 🔴 문제:
 *    WebView 는 a[download] 나 Content-Disposition: attachment 를 **스스로 처리하지 않는다.**
 *    DownloadListener 가 없으면 사용자가 내보내기 버튼을 눌러도
 *    **아무 일도 일어나지 않고 오류도 나지 않는다.** u2 의 ics 내보내기가 정확히 이 형태다.
 *
 * ⚠️ AD-1 — DownloadManager 는 **시스템 프로세스**에서 동작한다.
 *    따라서 이 앱의 network_security_config(평문 허용)가 **적용되지 않는다.**
 *    개발 환경의 http 다운로드가 기기·OS 에 따라 실패할 수 있다.
 *    그래서 실패를 감지해 시스템 브라우저로 폴백한다. 낙관적으로 등록만 하고 끝내지 않는다.
 */
class DownloadHandler(
    private val activity: Activity,
    private val origin: Origin,
    private val onFallbackToBrowser: (String) -> Unit,
) : DownloadListener {

    override fun onDownloadStart(
        url: String?,
        userAgent: String?,
        contentDisposition: String?,
        mimeType: String?,
        contentLength: Long,
    ) {
        if (url == null) return

        // ABR-23 — 허용 오리진의 URL 만 내려받는다.
        if (!AppConfig.isSameOrigin(url, origin)) {
            Log.w(TAG, "허용 오리진 밖의 다운로드를 거부했다")
            return
        }

        val fileName = URLUtil.guessFileName(url, contentDisposition, mimeType)

        val queued = runCatching {
            val manager = activity.getSystemService(Context.DOWNLOAD_SERVICE) as? DownloadManager
                ?: return@runCatching false

            val request = DownloadManager.Request(Uri.parse(url)).apply {
                setTitle(fileName)
                setDescription(activity.getString(R.string.download_description))
                setMimeType(mimeType)
                setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
                )
                setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName)
                userAgent?.let { addRequestHeader("User-Agent", it) }
                // 공유 토큰이 쿠키에 실릴 일은 없지만(u1 은 쿠키를 쓰지 않는다),
                // 세션이 생기더라도 다운로드가 깨지지 않도록 넘겨 둔다.
                CookieManager.getInstance().getCookie(url)?.let {
                    addRequestHeader("Cookie", it)
                }
            }
            manager.enqueue(request)
            true
        }.getOrElse { error ->
            Log.w(TAG, "DownloadManager 등록 실패", error)
            false
        }

        if (queued) {
            Toast.makeText(activity, R.string.toast_download_started, Toast.LENGTH_SHORT).show()
        } else {
            // AD-1 폴백 — 앱이 못 받으면 브라우저가 받게 한다.
            Toast.makeText(activity, R.string.toast_download_fallback, Toast.LENGTH_SHORT).show()
            onFallbackToBrowser(url)
        }
    }

    private companion object {
        const val TAG = "TripDownload"
    }
}
