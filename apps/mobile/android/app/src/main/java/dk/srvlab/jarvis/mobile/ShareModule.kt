package dk.srvlab.jarvis.mobile

import android.content.Intent
import android.net.Uri

import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.modules.core.DeviceEventManagerModule

/**
 * Læser det Android har delt med os (ACTION_SEND / ACTION_SEND_MULTIPLE).
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
class ShareModule(private val ctx: ReactApplicationContext) : ReactContextBaseJavaModule(ctx) {
  override fun getName(): String = "ShareModule"

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
      val fraAktivitet = læsOgRyd(ctx.currentActivity?.intent)
      if (fraAktivitet != null) { promise.resolve(fraAktivitet); return }
      val gemt = læsOgRyd(afventende)
      afventende = null
      promise.resolve(gemt)
    } catch (e: Throwable) {
      // En fejl her må ikke forhindre appen i at starte.
      promise.resolve(null)
    }
  }

  // RN kræver disse to for at NativeEventEmitter ikke advarer.
  @ReactMethod fun addListener(eventName: String) {}
  @ReactMethod fun removeListeners(count: Int) {}
}
