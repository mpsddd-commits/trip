// u3-trip-android — 단일 모듈 프로젝트 (ABR-43: 네이티브 표면을 최소로 유지)
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    // 🔴 SEC-10 — 저장소를 여기서만 선언한다. 모듈이 임의 저장소를 추가하지 못하게 막는다.
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "trip-android"
include(":app")
