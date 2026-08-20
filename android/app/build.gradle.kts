plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

// ---------------------------------------------------------------------------
// 접속 주소 주입 (ABR-01)
//
// 우선순위: -PbaseUrl 커맨드라인  >  gradle.properties  >  빈 문자열
// 🔴 소스에 리터럴을 두지 않는다. 구조 테스트(StructureTest)가 이를 검사한다.
// ---------------------------------------------------------------------------
val debugBaseUrl: String = (project.findProperty("baseUrl") as String?).orEmpty().trim()
val releaseBaseUrl: String = (project.findProperty("releaseBaseUrl") as String?).orEmpty().trim()
val extraCleartextHost: String = (project.findProperty("cleartextHost") as String?).orEmpty().trim()

// ---------------------------------------------------------------------------
// debug 전용 network_security_config 생성 (ABR-04, ABR-05)
//
// 🔴 왜 파일을 생성하는가:
//    사설 IP 대역은 <domain> 에 CIDR 로 쓸 수 없다. 실기기 IP 는 빌드마다 다르므로
//    -PcleartextHost 로 받아 이 시점에 XML 로 굽는다.
//
// 🔴 이 파일은 **debug 소스셋에만** 들어간다. release 매니페스트는 참조하지 않으므로
//    릴리스에서는 평문이 전면 차단된 기본 정책이 그대로 유지된다.
// ---------------------------------------------------------------------------
val nscDir = layout.buildDirectory.dir("generated/res/nsc")

val generateNetworkSecurityConfig by tasks.registering {
    outputs.dir(nscDir)
    // 호스트가 바뀌면 다시 굽는다.
    inputs.property("cleartextHost", extraCleartextHost)
    doLast {
        val xmlDir = nscDir.get().asFile.resolve("xml")
        xmlDir.mkdirs()
        val devHosts = mutableListOf("10.0.2.2", "localhost", "127.0.0.1")
        if (extraCleartextHost.isNotEmpty()) devHosts += extraCleartextHost
        val domains = devHosts.joinToString("\n") {
            """        <domain includeSubdomains="false">$it</domain>"""
        }
        xmlDir.resolve("network_security_config.xml").writeText(
            """<?xml version="1.0" encoding="utf-8"?>
<!--
    생성된 파일 — 직접 고치지 마세요. app/build.gradle.kts 가 굽습니다.
    ABR-04 / ABR-05 — debug 빌드 전용. 개발 주소에만 평문 HTTP 를 허용합니다.
-->
<network-security-config>
    <!-- 기본은 전면 차단. 아래 목록에 없는 도메인은 평문으로 접속할 수 없다. -->
    <base-config cleartextTrafficPermitted="false" />
    <domain-config cleartextTrafficPermitted="true">
$domains
    </domain-config>
</network-security-config>
"""
        )
    }
}

android {
    namespace = "local.trip.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "local.trip.app"
        minSdk = 26          // WebViewCompat.addWebMessageListener 안정 동작 (DD-19)
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        buildConfig = true   // BuildConfig.BASE_URL 을 쓰려면 켜야 한다 (AGP 8 기본 off)
        viewBinding = true
    }

    sourceSets {
        getByName("debug") {
            res.srcDir(nscDir)
        }
    }

    buildTypes {
        getByName("debug") {
            isMinifyEnabled = false
            buildConfigField("String", "BASE_URL", "\"$debugBaseUrl\"")
            // ABR-16 — WebView 원격 디버깅은 debug 에서만.
            buildConfigField("boolean", "WEBVIEW_DEBUG", "true")
        }
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // 🔴 ABR-02 — 기본값은 빈 문자열이다. -PreleaseBaseUrl 을 주지 않으면
            //    앱이 WebView 를 띄우지 않고 설정 오류 화면을 보여준다.
            //    "개발 주소가 릴리스에 섞여 나가는" 사고를 막는 것이 목적이다.
            buildConfigField("String", "BASE_URL", "\"$releaseBaseUrl\"")
            buildConfigField("boolean", "WEBVIEW_DEBUG", "false")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    testOptions {
        // android.jar 스텁이 예외를 던지는 대신 기본값을 돌려주게 한다.
        unitTests.isReturnDefaultValues = true
        unitTests.isIncludeAndroidResources = false
    }

    packaging {
        resources.excludes += setOf("META-INF/*.kotlin_module")
    }
}

// 리소스 병합 전에 network_security_config 를 구워 둔다.
tasks.matching { it.name == "preDebugBuild" }.configureEach {
    dependsOn(generateNetworkSecurityConfig)
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.webkit)
    implementation(libs.androidx.constraintlayout)

    testImplementation(libs.junit)
    // 🔴 android.jar 의 JSONObject 는 스텁이라 단위 테스트에서 쓸 수 없다.
    //    진짜 구현을 테스트 클래스패스 앞에 둔다.
    testImplementation(libs.json)
}
