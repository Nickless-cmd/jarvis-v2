package dk.srvlab.jarvis.mobile

import android.content.ComponentName
import android.content.Intent
import android.graphics.BitmapFactory
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * KALIBRERING: kniber `pinchOpen` overhovedet på den her telefon?
 *
 * ## Hvorfor den findes
 *
 * `KnibZoomTest` målte 0,00% pixelforskel efter et knib i appen. Det tal kan
 * betyde to ting — at appen ikke reagerer, eller at værktøjet ikke kniber. At
 * drage den første konklusion uden at prøve den anden er at stole på et
 * instrument man ikke har kalibreret, og hele grunden til at bygge harnesset
 * var netop at holde op med at gætte.
 *
 * Enkelt-fingre er allerede bevist: `KnibZoomTest` ruller selv gennem samtalen
 * med `UiDevice.swipe` og finder vedhæftningen. Det der mangler er beviset for
 * TO fingre.
 *
 * ## Læs rækkefølgen sådan her
 *
 * - Kalibrering RØD → værktøjet kniber ikke. App-testens resultat siger intet,
 *   og der er INTET at konkludere om appen.
 * - Kalibrering GRØN, app-test RØD → appen reagerer ikke på et ægte knib.
 * - Begge grønne → knib-zoom virker.
 *
 * Uden den første linje er app-testen et tal uden betydning.
 */
@RunWith(AndroidJUnit4::class)
class KnibKontrolTest {

    @Test
    fun pinchOpen_zoomer_en_flade_der_beviseligt_lytter() {
        val enhed = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
        enhed.wakeUp()

        val ctx = InstrumentationRegistry.getInstrumentation().context
        ctx.startActivity(
            Intent().apply {
                component = ComponentName(
                    "dk.srvlab.jarvis.mobile.test",
                    "dk.srvlab.jarvis.mobile.KalibreringsAktivitet"
                )
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        )
        val kom = enhed.wait(
            Until.hasObject(By.pkg("dk.srvlab.jarvis.mobile.test").depth(0)), 15_000L
        )
        // «Blev ikke koert» og «virkede ikke» maa ALDRIG blive det samme svar.
        // Tre tidligere kontroller fejlede paa deres egen opsaetning og gav et
        // nul der lignede et resultat.
        assertTrue("kalibrerings-fladen kom ikke frem — kontrollen blev IKKE koert", kom)
        Thread.sleep(1_500)

        val mappe = InstrumentationRegistry.getInstrumentation().targetContext
            .externalCacheDir?.absolutePath ?: "/sdcard"
        val a = File(mappe, "kontrol-foer.png").also { enhed.takeScreenshot(it) }

        // Samme kald og samme styrke som app-testen. Ellers kalibrerer vi noget
        // andet end det vi bruger.
        val flade = enhed.wait(
            Until.findObject(By.pkg("dk.srvlab.jarvis.mobile.test").depth(0)), 5_000L
        )
        assertTrue("fandt ikke kalibrerings-fladen — kontrollen blev IKKE koert", flade != null)
        flade!!.pinchOpen(0.7f)
        Thread.sleep(1_500)

        val b = File(mappe, "kontrol-efter.png").also { enhed.takeScreenshot(it) }
        val andel = forskel(a, b)
        android.util.Log.i("KnibKontrol", "pixelforskel=%.2f%%".format(andel * 100))

        assertTrue(
            ("pinchOpen aendrede INTET paa en flade der laeser raa MotionEvents " +
                "(%.2f%%) — vaerktoejet kniber ikke paa den her telefon, og " +
                "KnibZoomTest's nul siger derfor INTET om appen").format(andel * 100),
            andel > 0.01
        )
    }

    /** Andel forskellige pixels, hver 8. — vi leder efter «flyttede det sig». */
    private fun forskel(a: File, b: File): Double {
        val bmA = BitmapFactory.decodeFile(a.absolutePath) ?: return 0.0
        val bmB = BitmapFactory.decodeFile(b.absolutePath) ?: return 0.0
        if (bmA.width != bmB.width || bmA.height != bmB.height) return 1.0
        var forskellige = 0
        var talte = 0
        var y = 0
        while (y < bmA.height) {
            var x = 0
            while (x < bmA.width) {
                talte++
                if (bmA.getPixel(x, y) != bmB.getPixel(x, y)) forskellige++
                x += 8
            }
            y += 8
        }
        return if (talte == 0) 0.0 else forskellige.toDouble() / talte
    }
}
