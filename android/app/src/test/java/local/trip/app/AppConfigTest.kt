package local.trip.app

import local.trip.app.config.AppConfig
import local.trip.app.config.ConfigState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * A7 검증 — ABR-02 / ABR-03.
 *
 * 이 테스트가 지키는 것: **주소가 없거나 이상할 때 앱이 빈 화면을 띄우지 않는다.**
 */
class AppConfigTest {

    @Test
    fun `빈 주소는 Missing 이다`() {
        assertTrue(AppConfig.resolve("") is ConfigState.Missing)
        assertTrue(AppConfig.resolve("   ") is ConfigState.Missing)
        assertTrue(AppConfig.resolve(null) is ConfigState.Missing)
    }

    @Test
    fun `스킴이 없으면 Malformed 다`() {
        assertTrue(AppConfig.resolve("10.0.2.2:8200") is ConfigState.Malformed)
        assertTrue(AppConfig.resolve("localhost") is ConfigState.Malformed)
    }

    @Test
    fun `허용되지 않은 스킴은 Malformed 다`() {
        // file 과 javascript 를 열어 주면 WebView 하드닝(ABR-10)이 무의미해진다.
        assertTrue(AppConfig.resolve("file:///android_asset/index.html") is ConfigState.Malformed)
        assertTrue(AppConfig.resolve("javascript:alert(1)") is ConfigState.Malformed)
        assertTrue(AppConfig.resolve("about:blank") is ConfigState.Malformed)
        assertTrue(AppConfig.resolve("ftp://example.com") is ConfigState.Malformed)
    }

    @Test
    fun `개발 기본 주소는 Valid 이고 포트가 보존된다`() {
        val state = AppConfig.resolve("http://10.0.2.2:8200")
        assertTrue(state is ConfigState.Valid)
        val origin = (state as ConfigState.Valid).origin
        assertEquals("http", origin.scheme)
        assertEquals("10.0.2.2", origin.host)
        assertEquals(8200, origin.port)
    }

    @Test
    fun `기본 포트는 스킴에 맞춰 채워진다`() {
        val https = AppConfig.parseOrigin("https://trip.example.com")
        assertEquals(443, https?.port)
        val http = AppConfig.parseOrigin("http://trip.example.com")
        assertEquals(80, http?.port)
    }

    @Test
    fun `기본 포트는 규칙 문자열에서 생략된다`() {
        // allowedOriginRules 에 :443 을 붙이면 매칭되지 않는 기기가 있다.
        assertEquals("https://trip.example.com", AppConfig.parseOrigin("https://trip.example.com")?.toRule())
        assertEquals("http://10.0.2.2:8200", AppConfig.parseOrigin("http://10.0.2.2:8200")?.toRule())
    }

    @Test
    fun `호스트 대소문자는 무시된다`() {
        assertEquals(
            AppConfig.parseOrigin("https://Trip.Example.COM"),
            AppConfig.parseOrigin("https://trip.example.com"),
        )
    }

    @Test
    fun `해석할 수 없는 문자열은 null 이다`() {
        assertNull(AppConfig.parseOrigin("http://"))
        assertNull(AppConfig.parseOrigin(""))
        assertNull(AppConfig.parseOrigin("http:// space"))
    }
}
