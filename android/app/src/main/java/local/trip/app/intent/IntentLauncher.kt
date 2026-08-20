package local.trip.app.intent

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.util.Log
import android.widget.Toast
import local.trip.app.R

/**
 * A4 `IntentLauncher` — 앱 밖으로 나가는 모든 경로 (FR-23, FR-24, FR-28).
 *
 * 🔴 DD-11 / ABR-20 — **딥링크 URL 을 여기서 만들지 않는다.**
 *    u2 의 W13(`shared/deeplink`)이 만든 것을 받아 실행만 한다.
 *    양쪽에서 URL 을 만들면 웹과 앱의 동작이 갈라진다.
 */
class IntentLauncher(private val activity: Activity) {

    /**
     * 🔴 SEC-11 — 웹이 준 URL 을 그대로 인텐트에 태우되 **스킴을 제한**한다.
     *
     * u2 는 nmap 스킴과 https 만 만든다. 그럼에도 화이트리스트를 두는 이유는
     * WebView 에 예상 밖의 페이지가 뜨는 상황에서 임의 스킴 실행 경로가 되지 않게 하기 위함이다.
     * (intent 스킴 URI 를 Intent.parseUri 로 해석하는 코드는 두지 않는다 —
     *  그것이 WebView 임의 인텐트 실행 취약점의 전형적인 형태다.)
     */
    private val allowedSchemes = setOf("nmap", "http", "https")

    /**
     * FR-23 / FR-24 — 네이버지도 열기. WF-A4.
     *
     * ① 앱 URL 시도 → ② ActivityNotFoundException 이면 웹 URL → ③ 둘 다 실패하면 토스트.
     *
     * queryIntentActivities 로 미리 조회하지 않는 이유(Q10=A):
     * Android 11+ 의 패키지 가시성 제한 때문에 queries 선언이 필요하고,
     * **선언을 빠뜨리면 설치돼 있어도 "없다"고 판정**한다. 예외 처리가 더 견고하다.
     */
    fun openMap(appUrl: String, webUrl: String) {
        if (launch(appUrl)) return
        if (launch(webUrl)) return
        // ABR-21 — 조용히 실패하지 않는다. 사용자는 자기가 누른 것이 먹혔는지 알아야 한다.
        toast(R.string.toast_map_failed)
    }

    /** ABR-14 — 허용 오리진 밖 링크는 시스템 브라우저로. WF-A6 도 이 경로를 쓴다. */
    fun openExternal(url: String) {
        if (!launch(url)) toast(R.string.toast_browser_failed)
    }

    /** FR-28 — 시스템 공유 시트. */
    fun share(title: String, text: String, url: String) {
        val body = listOf(text, url).filter { it.isNotBlank() }.joinToString("\n")
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, title)
            putExtra(Intent.EXTRA_TITLE, title)
            putExtra(Intent.EXTRA_TEXT, body)
        }
        try {
            activity.startActivity(
                Intent.createChooser(send, activity.getString(R.string.share_chooser_title))
            )
        } catch (_: ActivityNotFoundException) {
            toast(R.string.toast_share_failed)
        }
    }

    /** 실행 성공 여부를 돌려준다. 실패를 예외로 밖에 흘리지 않는다. */
    private fun launch(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        val uri = try {
            Uri.parse(url)
        } catch (_: Exception) {
            return false
        }
        val scheme = uri.scheme?.lowercase()
        if (scheme == null || scheme !in allowedSchemes) {
            Log.w(TAG, "허용되지 않은 스킴이라 실행하지 않았다: " + scheme)
            return false
        }
        return try {
            activity.startActivity(
                Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
            true
        } catch (_: ActivityNotFoundException) {
            false
        } catch (e: SecurityException) {
            // 대상 앱이 export 하지 않은 액티비티를 가리키는 경우 등.
            Log.w(TAG, "인텐트 실행이 거부됐다", e)
            false
        }
    }

    private fun toast(resId: Int) {
        Toast.makeText(activity, resId, Toast.LENGTH_SHORT).show()
    }

    private companion object {
        const val TAG = "TripIntent"
    }
}
