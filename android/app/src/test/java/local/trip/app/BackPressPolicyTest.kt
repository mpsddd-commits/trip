package local.trip.app

import local.trip.app.ui.BackPressPolicy
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * ABR-42 검증 — 최상위에서의 이중 뒤로가기. WF-A9.
 *
 * 시각을 인자로 받게 설계했기 때문에 에뮬레이터 없이 경계를 고정할 수 있다.
 */
class BackPressPolicyTest {

    private val window = 2_000L

    @Test
    fun `첫 입력은 안내다`() {
        val policy = BackPressPolicy(window)
        assertEquals(BackPressPolicy.Decision.WARN, policy.onBackAtTop(1_000))
    }

    @Test
    fun `창 안의 재입력은 종료다`() {
        val policy = BackPressPolicy(window)
        policy.onBackAtTop(1_000)
        assertEquals(BackPressPolicy.Decision.EXIT, policy.onBackAtTop(2_500))
    }

    @Test
    fun `경계값은 종료로 친다`() {
        val policy = BackPressPolicy(window)
        policy.onBackAtTop(1_000)
        assertEquals(BackPressPolicy.Decision.EXIT, policy.onBackAtTop(3_000))
    }

    @Test
    fun `창을 넘기면 다시 안내다`() {
        val policy = BackPressPolicy(window)
        policy.onBackAtTop(1_000)
        assertEquals(BackPressPolicy.Decision.WARN, policy.onBackAtTop(3_001))
    }

    @Test
    fun `종료 후 상태가 초기화된다`() {
        val policy = BackPressPolicy(window)
        policy.onBackAtTop(1_000)
        policy.onBackAtTop(1_500)   // EXIT
        // finish 가 즉시 끝내지 못한 경우에도 다음 입력이 곧바로 종료가 되면 안 된다.
        assertEquals(BackPressPolicy.Decision.WARN, policy.onBackAtTop(1_600))
    }

    @Test
    fun `reset 은 카운트를 지운다`() {
        val policy = BackPressPolicy(window)
        policy.onBackAtTop(1_000)
        // 사용자가 WebView 히스토리를 타고 들어갔다 나왔다.
        policy.reset()
        assertEquals(BackPressPolicy.Decision.WARN, policy.onBackAtTop(1_500))
    }
}
