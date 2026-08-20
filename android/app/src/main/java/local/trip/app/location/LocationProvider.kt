package local.trip.app.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat

/**
 * A5 LocationProvider — 위치 권한과 좌표 조회 (FR-12, FR-28). WF-A7.
 *
 * 🔴 ABR-26 — **권한 거부는 오류가 아니다.** denied = true 로 회신하고 앱은 정상 동작한다.
 * 🔴 ABR-27 — **모든 요청에 반드시 회신한다.** 실패도 타임아웃도 회신이다.
 *
 * Play Services 의 FusedLocationProvider 를 쓰지 않고 플랫폼 LocationManager 를 쓴다.
 * APK 크기와 컨테이너 빌드 복잡도를 둘 다 줄이고, GMS 없는 기기에서도 동작한다.
 */
class LocationProvider(private val activity: ComponentActivity) {

    /** 회신 형태. Denied 와 Unavailable 을 구분한다 — 웹이 다른 안내를 할 수 있다. */
    sealed interface Outcome {
        data class Available(val lat: Double, val lng: Double) : Outcome
        data object Denied : Outcome
        data object Unavailable : Outcome
    }

    private val handler = Handler(Looper.getMainLooper())

    /** 권한 대화상자를 기다리는 요청들. 여러 건이 겹칠 수 있다. */
    private val awaitingPermission = mutableListOf<(Outcome) -> Unit>()

    private val permissionLauncher =
        activity.registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions()
        ) { grants ->
            val granted = grants.values.any { it }
            val waiting = awaitingPermission.toList()
            awaitingPermission.clear()
            waiting.forEach { callback ->
                if (granted) fetch(callback) else callback(Outcome.Denied)
            }
        }

    /**
     * 웹이 requestLocation 을 보냈을 때만 호출된다 (Q11=A).
     * 앱 첫 실행에 미리 권한을 묻지 않는다 — 맥락 없는 요청은 거부율이 높다.
     */
    fun request(onResult: (Outcome) -> Unit) {
        if (hasPermission()) {
            fetch(onResult)
            return
        }
        awaitingPermission += onResult
        permissionLauncher.launch(
            arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION,
            )
        )
    }

    fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(activity, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(activity, Manifest.permission.ACCESS_COARSE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED

    /** 대기 중인 요청을 정리한다. 액티비티가 사라진 뒤 콜백이 불리지 않게 한다 (ABR-32). */
    fun dispose() {
        awaitingPermission.clear()
        handler.removeCallbacksAndMessages(null)
    }

    private fun fetch(onResult: (Outcome) -> Unit) {
        val manager = activity.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
        if (manager == null) {
            onResult(Outcome.Unavailable)
            return
        }

        // ① 최근 위치가 충분히 신선하면 그대로 쓴다. 대부분 여기서 끝난다.
        val fresh = lastFreshLocation(manager)
        if (fresh != null) {
            onResult(Outcome.Available(fresh.latitude, fresh.longitude))
            return
        }

        // ② 없으면 한 번만 갱신을 받는다.
        val provider = bestEnabledProvider(manager)
        if (provider == null) {
            // 위치 서비스가 꺼져 있다. 권한 거부와는 다른 상황이다.
            onResult(Outcome.Unavailable)
            return
        }

        var settled = false
        var listener: LocationListener? = null

        // 🔴 ABR-27 / 발견 C — u2 는 10초 타임아웃을 자체 보유한다.
        //    여기서 8초에 회신해 **u2 보다 먼저** 끝낸다. 같은 값이면 경합이 생긴다.
        val timeout = Runnable {
            if (settled) return@Runnable
            settled = true
            listener?.let { runCatching { manager.removeUpdates(it) } }
            onResult(Outcome.Unavailable)
        }

        val received = LocationListener { location: Location ->
            if (settled) return@LocationListener
            settled = true
            handler.removeCallbacks(timeout)
            listener?.let { runCatching { manager.removeUpdates(it) } }
            onResult(Outcome.Available(location.latitude, location.longitude))
        }
        listener = received

        try {
            manager.requestLocationUpdates(provider, 0L, 0f, received, Looper.getMainLooper())
            handler.postDelayed(timeout, FIX_TIMEOUT_MS)
        } catch (e: SecurityException) {
            // 권한이 방금 회수된 경우. 회신은 반드시 한다.
            settled = true
            Log.w(TAG, "위치 갱신 요청이 거부됐다", e)
            onResult(Outcome.Denied)
        }
    }

    private fun lastFreshLocation(manager: LocationManager): Location? =
        try {
            PROVIDERS
                .mapNotNull { runCatching { manager.getLastKnownLocation(it) }.getOrNull() }
                .filter { System.currentTimeMillis() - it.time <= MAX_AGE_MS }
                .maxByOrNull { it.time }
        } catch (_: SecurityException) {
            null
        }

    private fun bestEnabledProvider(manager: LocationManager): String? =
        PROVIDERS.firstOrNull {
            runCatching { manager.isProviderEnabled(it) }.getOrDefault(false)
        }

    private companion object {
        const val TAG = "TripLocation"

        /** u2 의 10초보다 먼저 끝내기 위한 값 (발견 C). */
        const val FIX_TIMEOUT_MS = 8_000L

        /** 2분 이내면 "지금 위치"로 인정한다. */
        const val MAX_AGE_MS = 2 * 60 * 1000L

        val PROVIDERS = listOf(
            LocationManager.NETWORK_PROVIDER,
            LocationManager.GPS_PROVIDER,
            LocationManager.PASSIVE_PROVIDER,
        )
    }
}
