package local.trip.app.bridge

import org.json.JSONObject

/**
 * A3 브리지 메시지 계약 — u2 `shared/bridge/protocol.ts` 의 정확한 대응물.
 *
 * 🔴 UD-4 — **`unit-of-work-dependency.md` §2 계약 ②가 단일 진실 공급원이다.**
 *    이 파일과 u2 의 `protocol.ts` 는 그 문서의 복제본이다.
 *    변경할 때는 **문서를 먼저 고치고** 양쪽 코드를 맞춘다.
 *
 * 🔴 SEC-08 / SEC-11 — 아래 5종 외의 메시지를 추가하지 않는다.
 *    파일 접근·임의 인텐트 실행·저장소 접근·연락처를 노출하는 메시지는 **금지**한다.
 *    WebView 에 로드되는 모든 페이지가 잠재적 호출자다.
 */
object BridgeProtocol {

    /** 웹 전역에 심는 객체 이름. u2 의 `BRIDGE_NAME` 과 반드시 일치해야 한다. */
    const val JS_OBJECT_NAME = "tripBridge"

    /** 네이티브 → 웹 전달 콜백 이름. u2 가 `window.__tripBridgeReceive` 로 노출한다. */
    const val JS_RECEIVER = "__tripBridgeReceive"

    const val BRIDGE_VERSION = "1"

    // --- 웹 → 네이티브 -----------------------------------------------------
    const val TYPE_OPEN_MAP = "openMap"
    const val TYPE_SHARE = "share"
    const val TYPE_REQUEST_LOCATION = "requestLocation"

    // --- 네이티브 → 웹 -----------------------------------------------------
    const val TYPE_LOCATION_RESULT = "locationResult"
    const val TYPE_BRIDGE_READY = "bridgeReady"

    /**
     * 웹이 보낸 JSON 을 해석한다.
     *
     * 🔴 ABR-25 — 잘못된 JSON·알 수 없는 type·필수 필드 누락은 **`null` 을 반환**한다.
     *    예외를 밖으로 던지지 않는다. 브리지 콜백에서 예외가 나면 리스너가 죽고,
     *    그 뒤로는 **모든 메시지가 조용히 사라진다.**
     */
    fun parse(payload: String?): Outbound? {
        if (payload.isNullOrBlank()) return null
        val json = try {
            JSONObject(payload)
        } catch (_: Exception) {
            return null
        }
        return when (json.optString("type")) {
            TYPE_OPEN_MAP -> {
                val appUrl = json.optString("appUrl")
                val webUrl = json.optString("webUrl")
                if (appUrl.isEmpty() && webUrl.isEmpty()) null
                else Outbound.OpenMap(appUrl = appUrl, webUrl = webUrl)
            }

            TYPE_SHARE -> Outbound.Share(
                title = json.optString("title"),
                text = json.optString("text"),
                url = json.optString("url"),
            )

            TYPE_REQUEST_LOCATION -> {
                val requestId = json.optString("requestId")
                // requestId 가 없으면 회신을 짝지을 수 없다 — 처리하지 않는다.
                if (requestId.isEmpty()) null else Outbound.RequestLocation(requestId)
            }

            // 계약 밖의 type. 무시한다 (ABR-25).
            else -> null
        }
    }

    /**
     * 네이티브 → 웹 메시지를 JSON 문자열로 만든다.
     *
     * `JSONObject` 로 조립하므로 값에 따옴표·개행·유니코드가 들어가도 안전하다.
     * 문자열 연결로 JSON 을 만들지 않는다 (ABR-31).
     */
    fun encode(message: Inbound): String = when (message) {
        is Inbound.LocationResult -> JSONObject().apply {
            put("type", TYPE_LOCATION_RESULT)
            put("requestId", message.requestId)
            // 🔴 JSONObject.put(String, Object) 에 null 을 주면 **키가 삭제된다.**
            //    u2 는 `lat === null` 을 검사하므로 키가 반드시 있어야 한다.
            //    JSONObject.NULL 을 명시적으로 넣는다.
            put("lat", message.lat ?: JSONObject.NULL)
            put("lng", message.lng ?: JSONObject.NULL)
            put("denied", message.denied)
        }.toString()

        is Inbound.BridgeReady -> JSONObject().apply {
            put("type", TYPE_BRIDGE_READY)
            put("version", message.version)
        }.toString()
    }

    /** 웹 → 네이티브 (3종) */
    sealed interface Outbound {
        data class OpenMap(val appUrl: String, val webUrl: String) : Outbound
        data class Share(val title: String, val text: String, val url: String) : Outbound
        data class RequestLocation(val requestId: String) : Outbound
    }

    /** 네이티브 → 웹 (2종) */
    sealed interface Inbound {
        data class LocationResult(
            val requestId: String,
            val lat: Double?,
            val lng: Double?,
            val denied: Boolean,
        ) : Inbound

        data class BridgeReady(val version: String = BRIDGE_VERSION) : Inbound
    }
}
