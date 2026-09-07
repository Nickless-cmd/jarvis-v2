package dk.srvlab.jarvis.mobile

import android.content.Intent
import android.net.Uri

import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.module.annotations.ReactModule
import com.facebook.react.bridge.WritableMap
import com.facebook.react.modules.core.DeviceEventManagerModule

/**
 * Læser det Android har delt med os (ACTION_SEND / ACTION_SEND_MULTIPLE).
 *
 * HED «ShareModule» indtil 7/9-2026 og virkede ikke: React Native har SELV et
 * indbygget modul med det navn (det bag `Share.share()`, som «Del»-knappen
 * bruger). Kernens vandt, mit blev kasseret UDEN en fejl — JS fik et objekt
 * uden metoder, og `getModule("ShareModule")` blev aldrig kaldt på vores
 * pakke. Navnet skal være vores eget.
 *
 * Manifestets intent-filtre gør at Jarvis STÅR i del-arket; uden det her
 * lander delingen bare i en app der ikke kigger efter den. Filtrene har været
 * der uden en læser — en dør uden nogen bag.
 *
 * TO veje ind, og begge skal med:
 *   - Appen var LUKKET  → intenten sidder på activity'en når JS starter op.
 *     Derfor `hentDeling()`, som JS kalder én gang ved opstart.
 *   - Appen KØRTE       → onNewIntent (launchMode er singleTask, så der
 *     kommer ingen ny activity). Derfor hændelsen `jarvis.share`.
 *
 * Intenten RYDDES efter læsning. Uden det ville en rotation eller en tur
 * gennem baggrunden levere den samme deling igen, og teksten ville hobe sig
 * op i komposeren.
 */
@ReactModule(name = "DelingModule")
class DelingModule(private val ctx: ReactApplicationContext) : ReactContextBaseJavaModule(ctx) {
  override fun getName(): String = "DelingModule"

  companion object {
    /** Sættes af MainActivity.onNewIntent mens appen kører. */
    var afventende: Intent? = null

    fun levér(ctx: ReactApplicationContext?, intent: Intent?) {
      val map = tilMap(intent) ?: return
      val emitter = ctx?.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
      if (emitter == null) {
        // JS er ikke oppe endnu — gem den, så hentDeling() kan tage den.
        afventende = intent
        return
      }
      emitter.emit("jarvis.share", map)
    }

    private fun tilMap(intent: Intent?): WritableMap? {
      if (intent == null) return null
      val action = intent.action
      if (action != Intent.ACTION_SEND && action != Intent.ACTION_SEND_MULTIPLE) return null

      val map = Arguments.createMap()
      intent.type?.let { map.putString("mimeType", it) }
      intent.getStringExtra(Intent.EXTRA_TEXT)?.let { map.putString("text", it) }
      intent.getStringExtra(Intent.EXTRA_SUBJECT)?.let { map.putString("subject", it) }

      val uris = Arguments.createArray()
      if (action == Intent.ACTION_SEND) {
        @Suppress("DEPRECATION")
        (intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM))?.let { uris.pushString(it.toString()) }
      } else {
        @Suppress("DEPRECATION")
        intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)
          ?.forEach { uris.pushString(it.toString()) }
      }
      map.putArray("uris", uris)
      return map
    }

    /** Kaldes fra MainActivity.onCreate. Gemmer KUN delings-intents. */
    fun gemStart(intent: Intent?) {
      val action = intent?.action ?: return
      if (action == Intent.ACTION_SEND || action == Intent.ACTION_SEND_MULTIPLE) {
        afventende = intent
      }
    }

    fun læsOgRyd(intent: Intent?): WritableMap? {
      val map = tilMap(intent) ?: return null
      // Samme deling må ikke kunne læses to gange.
      intent?.action = null
      intent?.removeExtra(Intent.EXTRA_TEXT)
      intent?.removeExtra(Intent.EXTRA_STREAM)
      return map
    }
  }

  /** Kaldes én gang ved opstart. Resolver med null når intet blev delt. */
  @ReactMethod
  fun hentDeling(promise: Promise) {
    try {
      // Ventepositionen først: den er sat i onCreate og er den pålidelige vej.
      val gemt = læsOgRyd(afventende)
      afventende = null
      if (gemt != null) { promise.resolve(gemt); return }
      promise.resolve(læsOgRyd(ctx.currentActivity?.intent))
    } catch (e: Throwable) {
      // En fejl her må ikke forhindre appen i at starte.
      promise.resolve(null)
    }
  }

  // RN kræver disse to for at NativeEventEmitter ikke advarer.
  @ReactMethod fun addListener(eventName: String) {}
  @ReactMethod fun removeListeners(count: Int) {}
}
