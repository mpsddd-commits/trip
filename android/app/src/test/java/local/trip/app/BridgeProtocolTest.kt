package local.trip.app

import local.trip.app.bridge.BridgeProtocol
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * A3 계약 검증 — ABR-25.
 *
 * 🔴 이 테스트가 지키는 것: **잘못된 입력에 예외를 던지지 않는다.**
 *    브리지 콜백에서 예외가 나면 리스너가 죽고, 그 뒤로는 모든 메시지가 조용히 사라진다.
 */
class BridgeProtocolTest {

    // --- 웹 → 네이티브 -----------------------------------------------------

    @Test
    fun `openMap 을 해석한다`() {
        val message = BridgeProtocol.parse(
            """{"type":"openMap","appUrl":"nmap://place?id=1","webUrl":"https://map.naver.com/p/1"}"""
        )
        assertTrue(message is BridgeProtocol.Outbound.OpenMap)
        message as BridgeProtocol.Outbound.OpenMap
        assertEquals("nmap://place?id=1", message.appUrl)
        assertEquals("https://map.naver.com/p/1", message.webUrl)
    }

    @Test
    fun `share 를 해석한다`() {
        val message = BridgeProtocol.parse(
            """{"type":"share","title":"제주 3일","text":"일정 공유","url":"https://x/s/tok"}"""
        )
        assertTrue(message is BridgeProtocol.Outbound.Share)
        assertEquals("제주 3일", (message as BridgeProtocol.Outbound.Share).title)
    }

    @Test
    fun `requestLocation 을 해석한다`() {
        val message = BridgeProtocol.parse("""{"type":"requestLocation","requestId":"loc-1-abc"}""")
        assertEquals(
            "loc-1-abc",
            (message as BridgeProtocol.Outbound.RequestLocation).requestId,
        )
    }

    // --- 거부해야 하는 입력 -------------------------------------------------

    @Test
    fun `잘못된 JSON 은 null 이다`() {
        assertNull(BridgeProtocol.parse("not json"))
        assertNull(BridgeProtocol.parse("{"))
        assertNull(BridgeProtocol.parse("[1,2,3]"))
        assertNull(BridgeProtocol.parse(""))
        assertNull(BridgeProtocol.parse(null))
    }

    @Test
    fun `계약 밖의 type 은 null 이다`() {
        // 🔴 SEC-11 — 계약 5종 외에는 무엇이 와도 처리하지 않는다.
        assertNull(BridgeProtocol.parse("""{"type":"readFile","path":"/etc/hosts"}"""))
        assertNull(BridgeProtocol.parse("""{"type":"startActivity","intent":"..."}"""))
        assertNull(BridgeProtocol.parse("""{"type":""}"""))
        assertNull(BridgeProtocol.parse("""{"foo":"bar"}"""))
    }

    @Test
    fun `requestId 없는 requestLocation 은 null 이다`() {
        // 회신을 짝지을 수 없으므로 받아도 처리할 방법이 없다.
        assertNull(BridgeProtocol.parse("""{"type":"requestLocation"}"""))
        assertNull(BridgeProtocol.parse("""{"type":"requestLocation","requestId":""}"""))
    }

    @Test
    fun `URL 이 모두 빈 openMap 은 null 이다`() {
        assertNull(BridgeProtocol.parse("""{"type":"openMap","appUrl":"","webUrl":""}"""))
    }

    @Test
    fun `한쪽 URL 만 있어도 openMap 은 처리한다`() {
        // 폴백만 있는 경우도 사용자에게는 유효한 동작이다.
        assertTrue(
            BridgeProtocol.parse("""{"type":"openMap","webUrl":"https://map.naver.com"}""")
                is BridgeProtocol.Outbound.OpenMap
        )
    }

    // --- 네이티브 → 웹 -----------------------------------------------------

    @Test
    fun `locationResult 왕복`() {
        val json = BridgeProtocol.encode(
            BridgeProtocol.Inbound.LocationResult("loc-1", 37.5665, 126.9780, denied = false)
        )
        val parsed = JSONObject(json)
        assertEquals("locationResult", parsed.getString("type"))
        assertEquals("loc-1", parsed.getString("requestId"))
        assertEquals(37.5665, parsed.getDouble("lat"), 1e-9)
        assertEquals(126.9780, parsed.getDouble("lng"), 1e-9)
        assertFalse(parsed.getBoolean("denied"))
    }

    @Test
    fun `거부 회신은 lat lng 키를 null 로 유지한다`() {
        // 🔴 JSONObject.put(String, null) 은 **키를 삭제한다.**
        //    u2 는 `message.lat === null` 을 검사하므로 키가 사라지면 undefined 가 되어
        //    판정이 어긋난다. JSONObject.NULL 을 쓰는 이유가 이것이다.
        val json = BridgeProtocol.encode(
            BridgeProtocol.Inbound.LocationResult("loc-2", null, null, denied = true)
        )
        val parsed = JSONObject(json)
        assertTrue(parsed.has("lat"))
        assertTrue(parsed.has("lng"))
        assertTrue(parsed.isNull("lat"))
        assertTrue(parsed.isNull("lng"))
        assertTrue(parsed.getBoolean("denied"))
    }

    @Test
    fun `bridgeReady 를 만든다`() {
        val parsed = JSONObject(BridgeProtocol.encode(BridgeProtocol.Inbound.BridgeReady()))
        assertEquals("bridgeReady", parsed.getString("type"))
        assertEquals("1", parsed.getString("version"))
    }

    @Test
    fun `JS 객체 이름이 u2 와 일치한다`() {
        // u2 shared/bridge/protocol.ts 의 BRIDGE_NAME 과 반드시 같아야 한다.
        // 어긋나면 isNative() 가 false 가 되어 앱에서도 웹 경로를 탄다.
        assertEquals("tripBridge", BridgeProtocol.JS_OBJECT_NAME)
        assertEquals("__tripBridgeReceive", BridgeProtocol.JS_RECEIVER)
    }
}
