package local.trip.app.config

import java.net.URI

/**
 * A7 `AppConfig` — 접속 주소의 단일 해석 지점 (FR-27, CA-1).
 *
 * 🔴 `android.net.Uri` 를 쓰지 않고 `java.net.URI` 를 쓰는 이유:
 *    `android.net.Uri` 는 단위 테스트에서 android.jar 의 **스텁**이라 항상 null 을 돌려준다.
 *    오리진 판정은 보안 경계(SEC-08)이므로 **반드시 테스트로 고정**해야 한다.
 *    순수 JVM 타입을 쓰면 에뮬레이터 없이 검증할 수 있다.
 */
sealed interface ConfigState {
    /** 정상 — WebView 를 띄운다. */
    data class Valid(val baseUrl: String, val origin: Origin) : ConfigState

    /** ABR-02 — 주소가 비어 있다. release 빌드에서 `-PreleaseBaseUrl` 을 잊은 경우. */
    data object Missing : ConfigState

    /** ABR-03 — 주소를 해석할 수 없다. */
    data class Malformed(val raw: String) : ConfigState
}

/**
 * 정규화된 오리진. 기본 포트를 명시적으로 채워 두어 `http://a.com` 과 `http://a.com:80` 이
 * 같다고 판정되게 한다.
 */
data class Origin(val scheme: String, val host: String, val port: Int) {
    /** 사람이 읽고 로그에 남기는 형태. */
    override fun toString(): String = "$scheme://$host:$port"

    /**
     * `WebViewCompat.addWebMessageListener` 의 allowedOriginRules 에 넣는 형태.
     * 기본 포트일 때 `:80` / `:443` 을 붙이면 규칙이 매칭되지 않는 기기가 있어 생략한다.
     */
    fun toRule(): String =
        if (port == defaultPortFor(scheme)) "$scheme://$host" else "$scheme://$host:$port"

    companion object {
        fun defaultPortFor(scheme: String): Int = when (scheme) {
            "https" -> 443
            "http" -> 80
            else -> -1
        }
    }
}

object AppConfig {

    /** 앱이 다룰 수 있는 스킴. 그 밖은 전부 거부한다 (SEC-08). */
    private val ALLOWED_SCHEMES = setOf("http", "https")

    /**
     * ABR-02 / ABR-03 — 빌드에 주입된 주소를 해석한다.
     * 실패를 예외로 던지지 않는다. 액티비티가 상태를 보고 화면을 고른다.
     */
    fun resolve(rawBaseUrl: String?): ConfigState {
        val raw = rawBaseUrl?.trim().orEmpty()
        if (raw.isEmpty()) return ConfigState.Missing
        val origin = parseOrigin(raw) ?: return ConfigState.Malformed(raw)
        return ConfigState.Valid(baseUrl = raw, origin = origin)
    }

    /**
     * URL 에서 정규화된 오리진을 뽑는다. 해석 불가·비허용 스킴이면 `null`.
     *
     * `about:blank`, `data:`, `javascript:`, `file:` 은 전부 여기서 걸러진다 —
     * 스킴 허용목록이 화이트리스트이기 때문이다.
     */
    fun parseOrigin(url: String): Origin? {
        val trimmed = url.trim()
        if (trimmed.isEmpty()) return null
        val uri = try {
            URI(trimmed)
        } catch (_: Exception) {
            return null
        }
        val scheme = uri.scheme?.lowercase() ?: return null
        if (scheme !in ALLOWED_SCHEMES) return null
        val host = uri.host?.lowercase() ?: return null
        if (host.isEmpty()) return null
        val port = if (uri.port == -1) Origin.defaultPortFor(scheme) else uri.port
        return Origin(scheme, host, port)
    }

    /**
     * ABR-14 / ABR-23 — 이 URL 이 허용 오리진 안인가?
     *
     * 🔴 `startsWith(baseUrl)` 로 판정하지 않는다.
     *    `http://10.0.2.2:8200.evil.com` 이 통과한다.
     *    반드시 파싱해서 스킴·호스트·포트를 **각각** 비교한다.
     */
    fun isSameOrigin(url: String?, origin: Origin): Boolean {
        if (url.isNullOrBlank()) return false
        return parseOrigin(url) == origin
    }
}
