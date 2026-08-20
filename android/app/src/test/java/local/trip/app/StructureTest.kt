package local.trip.app

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 구조 테스트 — 설계 규칙이 **코드에 남아 있는지** 검사한다. 동작이 아니라 규칙을 지킨다.
 *
 * 🔴 u3 의 대표적 결함은 전부 컴파일을 통과하고 예외도 내지 않는다.
 *    "하드닝 한 줄이 나중에 풀리는" 사고를 잡을 수 있는 자동 수단은 이것뿐이다.
 *
 * ⚠️ u2 의 design-rules.test.ts 에서 **주석 때문에 오탐이 4건** 났다.
 *    같은 실수를 피하려고 여기서도 검사 전에 주석을 제거한다.
 */
class StructureTest {

    private val mainSrc = File("src/main/java/local/trip/app")
    private val resDir = File("src/main/res")
    private val manifests = listOf(
        File("src/main/AndroidManifest.xml"),
        File("src/debug/AndroidManifest.xml"),
    )

    private val kotlinSources: List<File> by lazy {
        mainSrc.walkTopDown().filter { it.isFile && it.extension == "kt" }.toList()
    }

    @Test
    fun `소스 트리를 찾을 수 있다`() {
        // 경로가 틀리면 아래 테스트가 전부 "위반 없음"으로 통과해 버린다.
        assertTrue("소스 디렉터리를 찾지 못했다: " + mainSrc.absolutePath, mainSrc.isDirectory)
        assertTrue("Kotlin 파일이 없다", kotlinSources.size >= 10)
    }

    // --- ABR-10 / ABR-13 하드닝 -------------------------------------------

    @Test
    fun `파일 접근을 켜는 코드가 없다`() {
        assertNoMatch(Regex("""allowFileAccess\s*=\s*true"""))
        assertNoMatch(Regex("""allowContentAccess\s*=\s*true"""))
        assertNoMatch(Regex("""allowFileAccessFromFileURLs\s*=\s*true"""))
        assertNoMatch(Regex("""allowUniversalAccessFromFileURLs\s*=\s*true"""))
    }

    @Test
    fun `WebView 자체 위치 권한을 켜지 않는다`() {
        // 켜면 브리지 경로와 두 개의 위치 요청 경로가 생긴다 (ABR-13).
        assertNoMatch(Regex("""setGeolocationEnabled\(\s*true\s*\)"""))
    }

    @Test
    fun `혼합 콘텐츠를 허용하지 않는다`() {
        assertNoMatch(Regex("""MIXED_CONTENT_ALWAYS_ALLOW"""))
        assertNoMatch(Regex("""MIXED_CONTENT_COMPATIBILITY_MODE"""))
    }

    // --- ABR-15 SSL -------------------------------------------------------

    @Test
    fun `SSL 오류를 무시하는 코드가 없다`() {
        // 🔴 handler.proceed() 한 줄이면 TLS 가 통째로 무의미해진다.
        assertNoMatch(Regex("""\.proceed\(\s*\)"""))
    }

    // --- ABR-01 주소 하드코딩 ---------------------------------------------

    @Test
    fun `Kotlin 소스에 접속 주소 리터럴이 없다`() {
        // 주소는 BuildConfig.BASE_URL 로만 들어온다.
        val violations = kotlinSources.filter { file ->
            val code = stripComments(file.readText())
            Regex("""["']https?://""").containsMatchIn(code)
        }
        assertEquals("소스에 주소 리터럴이 있다: " + violations.map { it.name }, emptyList<File>(), violations)
    }

    // --- SEC-11 브리지 노출 최소화 ----------------------------------------

    @Test
    fun `JavascriptInterface 는 postMessage 하나뿐이다`() {
        val annotated = kotlinSources.sumOf { file ->
            Regex("""@JavascriptInterface""").findAll(stripComments(file.readText())).count()
        }
        assertEquals("브리지에 노출된 메서드가 늘었다", 1, annotated)
    }

    @Test
    fun `임의 인텐트 파싱 경로가 없다`() {
        // Intent.parseUri 는 WebView 임의 인텐트 실행 취약점의 전형적인 입구다.
        assertNoMatch(Regex("""Intent\.parseUri"""))
    }

    // --- ABR-04 평문 정책 --------------------------------------------------

    @Test
    fun `매니페스트에 usesCleartextTraffic 이 없다`() {
        manifests.filter { it.isFile }.forEach { file ->
            // ⚠️ XML 주석을 먼저 지운다.
            //    이 규칙을 설명하는 주석이 매니페스트에 있어서, 지우지 않으면 자기 자신이 걸린다.
            //    u2 에서 났던 오탐과 같은 형태다.
            val xml = stripXmlComments(file.readText())
            assertTrue(
                file.path + " 에 usesCleartextTraffic 이 있다 — 모든 도메인이 열린다",
                !xml.contains("usesCleartextTraffic"),
            )
        }
    }

    @Test
    fun `main 소스셋에 network_security_config 가 없다`() {
        // 있으면 release 에도 평문 허용이 딸려 간다 (ABR-04).
        val leaked = File(resDir, "xml/network_security_config.xml")
        assertTrue("release 로 새어 나가는 평문 허용 설정", !leaked.exists())
    }

    // --- A2 단일 소유 ------------------------------------------------------

    @Test
    fun `WebView settings 는 WebViewConfigurator 에서만 만진다`() {
        val violations = kotlinSources
            .filter { it.name != "WebViewConfigurator.kt" }
            .filter { Regex("""\.settings\b""").containsMatchIn(stripComments(it.readText())) }
        assertEquals("하드닝이 여러 곳으로 흩어졌다: " + violations.map { it.name }, emptyList<File>(), violations)
    }

    // --- 도우미 ------------------------------------------------------------

    private fun assertNoMatch(pattern: Regex) {
        val violations = kotlinSources.filter { pattern.containsMatchIn(stripComments(it.readText())) }
        assertEquals(pattern.pattern + " 위반: " + violations.map { it.name }, emptyList<File>(), violations)
    }

    /** XML 주석을 제거한다. 규칙을 설명하는 주석이 위반으로 잡히지 않게. */
    private fun stripXmlComments(source: String): String =
        source.replace(Regex("""<!--[\s\S]*?-->"""), "")

    /** 블록 주석과 줄 주석을 제거한다. 문서에 쓴 금지 패턴이 위반으로 잡히지 않게. */
    private fun stripComments(source: String): String =
        source
            .replace(Regex("""/\*[\s\S]*?\*/"""), "")
            .replace(Regex("""//[^\n]*"""), "")
}
