package dk.srvlab.jarvis.mobile

import com.facebook.react.BaseReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.module.model.ReactModuleInfo
import com.facebook.react.module.model.ReactModuleInfoProvider

/**
 * Registrerer app'ens egne native moduler.
 *
 * `BaseReactPackage` med en `ReactModuleInfoProvider` er den form New
 * Architecture forventer — et almindeligt `ReactPackage` med
 * `createNativeModules` er den gamle.
 *
 * MÅLT 7/9-2026: navnet på et modul skal være VORES eget. Modulet hed først
 * «ShareModule», hvilket React Native selv bruger (bag `Share.share()`).
 * Kernens vandt, og vores blev kasseret uden en eneste fejl: JS fik et objekt
 * uden metoder, og `getModule("ShareModule")` blev aldrig kaldt her.
 */
class BubblePackage : BaseReactPackage() {

  override fun getModule(name: String, ctx: ReactApplicationContext): NativeModule? =
    when (name) {
      "BubbleModule" -> BubbleModule(ctx)
      "DelingModule" -> DelingModule(ctx)
      else -> null
    }

  override fun getReactModuleInfoProvider(): ReactModuleInfoProvider =
    ReactModuleInfoProvider {
      mapOf(
        "BubbleModule" to ReactModuleInfo(
          "BubbleModule", BubbleModule::class.java.name,
          false, false, false, false
        ),
        "DelingModule" to ReactModuleInfo(
          "DelingModule", DelingModule::class.java.name,
          false, false, false, false
        )
      )
    }
}
