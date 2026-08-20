package local.trip.app.ui

/**
 * ABR-42 — 최상위 화면에서의 뒤로가기 판정. WF-A9.
 *
 * 액티비티에서 분리해 둔 이유: **시각 경계는 단위 테스트로 고정해야 하는 로직**인데,
 * 액티비티 안에 있으면 에뮬레이터 없이는 검증할 수 없다.
 */
class BackPressPolicy(private val windowMs: Long = DEFAULT_WINDOW_MS) {

    enum class Decision {
        /** 안내를 보여주고 머문다. */
        WARN,

        /** 종료한다. */
        EXIT,
    }

    private var lastPressAt: Long? = null

    /**
     * WebView 히스토리를 다 쓴 뒤(= 최상위) 눌린 뒤로가기.
     * nowMs 를 인자로 받는 이유는 테스트에서 시간을 통제하기 위함이다.
     */
    fun onBackAtTop(nowMs: Long): Decision {
        val previous = lastPressAt
        // 경계값은 "이내"로 본다: 정확히 windowMs 가 지난 시점의 재입력은 종료로 친다.
        if (previous != null && nowMs - previous <= windowMs) {
            lastPressAt = null
            return Decision.EXIT
        }
        lastPressAt = nowMs
        return Decision.WARN
    }

    /** 사용자가 다른 화면으로 들어갔다 나오면 카운트를 초기화한다. */
    fun reset() {
        lastPressAt = null
    }

    companion object {
        const val DEFAULT_WINDOW_MS = 2_000L
    }
}
