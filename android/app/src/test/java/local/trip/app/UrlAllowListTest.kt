package local.trip.app

import local.trip.app.config.AppConfig
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * SEC-08 경계 검증 — ABR-14 / ABR-23.
 *
 * 🔴 이 테스트가 막는 사고:
 *    오리진 판정을 startsWith 로 짜면 `http://10.0.2.2:8200.evil.com` 이 통과한다.
 *    그 순간 브리지와 다운로드가 공격자 페이지에 열린다.
 */
class UrlAllowListTest {

    private val origin = requireNotNull(AppConfig.parseOrigin("http://10.0.2.2:8200"))

    @Test
    fun `같은 오리진의 경로는 허용된다`() {
        assertTrue(AppConfig.isSameOrigin("http://10.0.2.2:8200", origin))
        assertTrue(AppConfig.isSameOrigin("http://10.0.2.2:8200/", origin))
        assertTrue(AppConfig.isSameOrigin("http://10.0.2.2:8200/trips/abc", origin))
        assertTrue(AppConfig.isSameOrigin("http://10.0.2.2:8200/api/trips/1/export.ics", origin))
        assertTrue(AppConfig.isSameOrigin("http://10.0.2.2:8200/x?y=1#z", origin))
    }

    @Test
    fun `접두사만 같은 다른 호스트는 거부된다`() {
        // startsWith 로 짰다면 전부 통과했을 것들이다.
        assertFalse(AppConfig.isSameOrigin("http://10.0.2.2:8200.evil.com/", origin))
        assertFalse(AppConfig.isSameOrigin("http://10.0.2.2:82000/", origin))
        assertFalse(AppConfig.isSameOrigin("http://10.0.2.2.evil.com:8200/", origin))
    }

    @Test
    fun `포트가 다르면 거부된다`() {
        assertFalse(AppConfig.isSameOrigin("http://10.0.2.2:8100/", origin))
        assertFalse(AppConfig.isSameOrigin("http://10.0.2.2/", origin))
    }

    @Test
    fun `스킴이 다르면 거부된다`() {
        assertFalse(AppConfig.isSameOrigin("https://10.0.2.2:8200/", origin))
    }

    @Test
    fun `서브도메인은 별개 오리진이다`() {
        val site = requireNotNull(AppConfig.parseOrigin("https://trip.example.com"))
        assertFalse(AppConfig.isSameOrigin("https://evil.trip.example.com/", site))
        assertFalse(AppConfig.isSameOrigin("https://example.com/", site))
        assertTrue(AppConfig.isSameOrigin("https://trip.example.com/a/b", site))
    }

    @Test
    fun `위험한 스킴은 전부 거부된다`() {
        assertFalse(AppConfig.isSameOrigin("javascript:alert(1)", origin))
        assertFalse(AppConfig.isSameOrigin("file:///etc/hosts", origin))
        assertFalse(AppConfig.isSameOrigin("data:text/html,<script>1</script>", origin))
        assertFalse(AppConfig.isSameOrigin("content://com.android.contacts/", origin))
        assertFalse(AppConfig.isSameOrigin("intent://x#Intent;end", origin))
    }

    @Test
    fun `null 과 빈 문자열은 거부된다`() {
        assertFalse(AppConfig.isSameOrigin(null, origin))
        assertFalse(AppConfig.isSameOrigin("", origin))
        assertFalse(AppConfig.isSameOrigin("   ", origin))
        assertNotNull(origin)
    }
}
