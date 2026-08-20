package local.trip.app

import local.trip.app.bridge.BridgeProtocol
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ABR-31 검증 — evaluateJavascript 에 넘기는 문자열 인코딩.
 *
 * 🔴 이 테스트가 막는 사고:
 *    장소명에 따옴표나 개행이 들어간 상태로 문자열 연결로 스크립트를 만들면
 *    JS 구문이 깨지고 **회신이 도착하지 않는다.** 앱은 아무 오류도 보여주지 않는다.
 *    실기기 체크리스트 8번이 이 경우다.
 */
class JsEncodingTest {

    /** BridgeHandler.buildScript 와 같은 조립 방식. WebView 없이 검증하기 위해 복제한다. */
    private fun buildScript(json: String): String {
        val literal = JSONObject.quote(json)
        return "(function(){var r=window." + BridgeProtocol.JS_RECEIVER +
            ";if(typeof r!=='function'){return;}try{r(" + literal + ");}catch(e){}})();"
    }

    private val nastyNames = listOf(
        """오름 "정상" 전망대""",
        "줄바꿈\n이 든 이름",
        "역슬래시 \\ 포함",
        "탭\t포함",
        "</script><script>alert(1)</script>",
        "유니코드 \u2028 줄구분자",
        "'홑따옴표' 포함",
    )

    @Test
    fun `따옴표가 든 값이 스크립트를 깨뜨리지 않는다`() {
        nastyNames.forEach { name ->
            val json = BridgeProtocol.encode(
                BridgeProtocol.Inbound.LocationResult(requestId = name, lat = 1.0, lng = 2.0, denied = false)
            )
            val script = buildScript(json)

            // 스크립트 안의 JS 문자열 리터럴은 정확히 하나여야 한다.
            // 이스케이프가 새면 리터럴이 조기 종료되어 구문이 깨진다.
            val literal = JSONObject.quote(json)
            assertTrue("리터럴이 스크립트에 그대로 들어있어야 한다", script.contains(literal))

            // 리터럴 안에 이스케이프되지 않은 큰따옴표가 있으면 안 된다.
            val inner = literal.substring(1, literal.length - 1)
            assertFalse("이스케이프되지 않은 따옴표", hasUnescapedQuote(inner))

            // 리터럴 안에 날것의 개행이 있으면 안 된다 — JS 문자열은 줄바꿈을 담을 수 없다.
            assertFalse("날것의 개행", inner.contains('\n'))
            assertFalse("날것의 캐리지리턴", inner.contains('\r'))
        }
    }

    @Test
    fun `인코딩한 값이 원래 값으로 되돌아온다`() {
        nastyNames.forEach { name ->
            val json = BridgeProtocol.encode(
                BridgeProtocol.Inbound.LocationResult(name, 37.0, 127.0, denied = false)
            )
            assertEquals(name, JSONObject(json).getString("requestId"))
        }
    }

    @Test
    fun `script 종료 태그가 그대로 나오지 않는다`() {
        // 인라인 스크립트로 삽입될 가능성에 대비한다.
        val json = BridgeProtocol.encode(
            BridgeProtocol.Inbound.LocationResult("</script>", 1.0, 1.0, denied = false)
        )
        val literal = JSONObject.quote(json)
        assertFalse(literal.contains("</script>"))
    }

    private fun hasUnescapedQuote(s: String): Boolean {
        var i = 0
        while (i < s.length) {
            when (s[i]) {
                '\\' -> i++          // 다음 문자는 이스케이프된 것이므로 건너뛴다
                '"' -> return true
            }
            i++
        }
        return false
    }
}
