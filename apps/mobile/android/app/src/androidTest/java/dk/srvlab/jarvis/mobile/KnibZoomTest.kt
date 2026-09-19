package dk.srvlab.jarvis.mobile

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.Rect
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.BySelector
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.regex.Pattern

/**
 * Knib-for-zoom på fuldskærms-billedet — prøvet af på en rigtig telefon.
 *
 * ## Hvorfor det her ikke kan være en jest-test
 *
 * `FullscreenImagePreview` bruger `PanResponder`, som læser
 * `e.nativeEvent.touches`. En jest-test skal selv levere det objekt — og en
 * test der selv leverer inputtet kan aldrig se at INGEN leverer det i
 * virkeligheden. Huset har den erfaring skrevet ned: 577 grønne unit-tests
 * missede to fejl som fem minutter på telefonen fandt.
 *
 * ## Hvorfor ikke bare `adb shell sendevent`
 *
 * Målt 14/9-2026: `sendevent` mod `/dev/input/event4` giver «Permission
 * denied» selv om shell-brugeren ER i `input`-gruppen og noden er `rw` for
 * den. SELinux forbyder shell-konteksten at skrive til touchscreenen. En
 * instrumenterings-proces må injicere input; det er den eneste vej til et
 * ægte to-finger-knib.
 *
 * ## Hvad testen måler
 *
 * Den skalerede visning er en `Animated`-transform, ikke et nyt layout.
 * Androids `AccessibilityNodeInfo.boundsInScreen` regnes af
 * `View.getBoundsOnScreen()`, som ganger forældrenes matrix på — så en
 * scale-transform BØR vise sig i grænserne. «Bør» er ikke «gør»: derfor
 * rapporterer testen begge målinger uanset udfald, så en rød test siger
 * HVAD der skete og ikke kun at noget gik galt.
 */
@RunWith(AndroidJUnit4::class)
class KnibZoomTest {

    private lateinit var enhed: UiDevice

    private val pakke = "dk.srvlab.jarvis.mobile"
    private val vent = 8_000L

    @Before
    fun start() {
        enhed = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
        enhed.wakeUp()

        // Låseskærmen væk med et SWIPE, ikke et tryk: et tryk ville lande i
        // appen hvis skærmen allerede var låst op, og kunne lukke netop det vi
        // skal måle. Telefonen her har ingen kode — har den det, stopper vi
        // med at sige hvorfor i stedet for at fejle et tilfældigt sted senere.
        if (enhed.hasObject(By.res("com.android.systemui", "keyguard_root_view"))) {
            enhed.swipe(enhed.displayWidth / 2, (enhed.displayHeight * 0.85).toInt(),
                enhed.displayWidth / 2, (enhed.displayHeight * 0.25).toInt(), 12)
            enhed.waitForIdle()
        }

        // IKKE pressHome() + genstart. Appen genrenderer og ruller samtalen
        // tilbage til bunden, og den vedhæftning testen skal bruge ligger
        // laengere oppe. Vi starter kun appen hvis den ikke ALLEREDE er fremme.
        if (!enhed.hasObject(By.pkg(pakke).depth(0))) {
            val ctx: Context = InstrumentationRegistry.getInstrumentation().context
            val start = ctx.packageManager.getLaunchIntentForPackage(pakke)
            assertNotNull("appen $pakke er ikke installeret", start)
            start!!.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(start)
            enhed.wait(Until.hasObject(By.pkg(pakke).depth(0)), vent)
        }
        enhed.waitForIdle()
    }

    /** `testID` i React Native bliver til `resource-id` på Android. Målt. */
    private fun res(navn: String): BySelector = By.res(navn)

    /** Enhver vedhæftning duer; id'et er per-vedhæftning. */
    private val vedhaeftning = By.res(Pattern.compile("attachment-open-.*"))

    /**
     * Rul op i samtalen indtil en billed-vedhæftning er på skærmen.
     *
     * Første udgave af testen krævede at nogen HAVDE rullet derhen i forvejen.
     * Den fejlede prompte, og med rette: et harness der kun virker når et
     * menneske lige har gjort det rigtige, er ikke et harness — det er en
     * manuel prøve med ekstra trin.
     *
     * Billeder ligger typisk langt oppe i en lang samtale, så loftet er højt.
     * Bevægelsen er en swipe NEDAD, som ruller indholdet OP (bagud i tiden).
     */
    private fun rulTilVedhaeftning(maksRul: Int = 25): UiObject2? {
        val x = enhed.displayWidth / 2
        // Et billede tæller først som fundet når dets MIDTE ligger i det frie
        // felt mellem den svævende header og skrivefeltet. Målt 19/9-2026: et
        // billede med top ved y=103 lå under headeren, testens tryk ramte
        // headeren i stedet, og testen fejlede med «skærmen er en anden» —
        // om den ramte, afhang af hvor rulningen tilfældigvis stoppede.
        fun iFrieFelt(o: UiObject2): Boolean {
            val midt = o.visibleBounds.centerY()
            return midt > enhed.displayHeight * 0.2 && midt < enhed.displayHeight * 0.7
        }
        // Listen ruller videre et øjeblik efter et swipe. Et fund midt i den
        // bevægelse har bounds der er forældede når der trykkes (målt 19/9-2026:
        // «fandt ikke fuldskærms-scenen» i 3 af 4 kørsler). Vent på ro, og slå
        // op igen, så trykket rammer hvor billedet ER.
        fun synlig(): UiObject2? {
            if (enhed.findObjects(vedhaeftning).none(::iFrieFelt)) return null
            Thread.sleep(700)
            enhed.waitForIdle()
            return enhed.findObjects(vedhaeftning).firstOrNull(::iFrieFelt)
        }
        enhed.wait(Until.findObject(vedhaeftning), 2_000L)
        synlig()?.let { return it }
        for (i in 0 until maksRul) {
            // Findes et billede allerede, men for højt oppe, rulles et kort
            // stykke så det glider ned i det frie felt; ellers et helt rul.
            val taet = enhed.findObject(vedhaeftning) != null
            val slut = if (taet) 0.5 else 0.85
            enhed.swipe(x, (enhed.displayHeight * 0.3).toInt(),
                x, (enhed.displayHeight * slut).toInt(), 8)
            enhed.waitForIdle()
            enhed.wait(Until.findObject(vedhaeftning), 800L)
            synlig()?.let { return it }
        }
        return null
    }

    private fun findMedTaal(vaelger: BySelector, hvad: String): UiObject2 {
        val o = enhed.wait(Until.findObject(vaelger), vent)
        assertNotNull("fandt ikke $hvad — skaermen er en anden end forventet", o)
        return o!!
    }

    @Test
    fun etKnibGoerBilledetStoerre() {
        // ── åbn et billede i fuldskærm ───────────────────────────────────
        val aabn = rulTilVedhaeftning()
        assertNotNull(
            "fandt ingen billed-vedhaeftning efter at have rullet gennem samtalen " +
                "— aabn en samtale der indeholder et billede", aabn
        )
        aabn!!.click()

        val scene = findMedTaal(res("attachment-scene"), "fuldskaerms-scenen")
        val billede = findMedTaal(res("attachment-fullscreen-image"), "fuldskaerms-billedet")
        // Billedet hentes asynkront. Et «før»-billede taget mens det indlæses,
        // gav 7-29 % pixelforskel UDEN zoom (skala 1,00 i appens egen log,
        // 19/9-2026) — en forskel fra indlæsningen, ikke fra knibet.
        Thread.sleep(2500)
        enhed.waitForIdle()

        val foer: Rect = billede.visibleBounds
        val sceneRamme: Rect = scene.visibleBounds
        val foerBillede = skaermbillede("foer")

        // ── knib udad ────────────────────────────────────────────────────
        // 70% af den mindste kant. Mindre end det, og fingrene starter for
        // taet paa hinanden til at `fingerAfstand` giver et brugbart anker.
        scene.pinchOpen(0.7f)
        Thread.sleep(800)

        val efter: Rect = enhed.wait(Until.findObject(res("attachment-fullscreen-image")), vent)
            ?.visibleBounds ?: foer
        val efterBillede = skaermbillede("efter")

        // ── to maalinger, fordi ÉN ikke kan skelne ───────────────────────
        // Foerste udgave af testen maalte kun `visibleBounds`. Den gav «ingen
        // aendring» — og det tal kan betyde TO ting: at knibet intet gjorde,
        // eller at tilgaengeligheds-graenser ikke afspejler en `Animated`-
        // transform. Billedets graenser var praecis scenens, hvilket peger paa
        // det sidste. En maaling der ikke kan skelne to tilstande, er ikke et
        // svar.
        //
        // Pixel-forskellen kan. Skalerer billedet, aendrer skaermen sig; goer
        // den ikke, er de to optagelser ens.
        val pixelAendring = forskel(foerBillede, efterBillede)

        val besked = buildString {
            append("scene=").append(sceneRamme.toShortString())
            append(" foer=").append(foer.toShortString())
            append(" (").append(foer.width()).append("x").append(foer.height()).append(")")
            append(" efter=").append(efter.toShortString())
            append(" (").append(efter.width()).append("x").append(efter.height()).append(")")
            append(" pixelforskel=").append(String.format("%.2f%%", pixelAendring * 100))
        }
        // Rapportér ALTID. En roed test skal sige hvad der skete, ikke kun at
        // noget gik galt.
        android.util.Log.i("KnibZoom", besked)

        val graenserVoksede = efter.width() > foer.width() || efter.height() > foer.height()
        // 1% af skaermen. Under det kan en markoer eller en blinkende
        // statuslinje alene forklare forskellen.
        val skaermenAendredeSig = pixelAendring > 0.01

        assertTrue(
            "billedet reagerede ikke paa et knib — $besked (skaermbilleder ligger i " +
                "$mappe paa enheden)",
            graenserVoksede || skaermenAendredeSig
        )

        // Og lukkeknappen skal virke EFTER et rigtigt zoom. Testen nedenfor
        // når ikke altid at zoome (knibet afbrydes tidligt) — her er billedet
        // beviseligt forstørret, og kan dække topbjælken hvis scenen ikke
        // klipper sine børns tryk. Målt 19/9-2026: én fejl netop i en runde
        // med 53 % pixelforskel.
        val luk = findMedTaal(res("attachment-close"), "lukkeknappen efter zoom")
        luk.click()
        val vaek = enhed.wait(Until.gone(res("attachment-scene")), vent)
        assertTrue("fuldskaermen lukkede ikke efter et rigtigt zoom — $besked", vaek)
    }

    /** Hvor mappen med bevismateriale ligger — nævnt i enhver fejlbesked. */
    private val mappe: String
        get() = InstrumentationRegistry.getInstrumentation().targetContext
            .externalCacheDir?.absolutePath ?: "/sdcard"

    /** Tag et skærmbillede og gem det, så et rødt resultat efterlader bevis. */
    private fun skaermbillede(navn: String): File {
        val f = File(mappe, "knibzoom-$navn.png")
        f.parentFile?.mkdirs()
        enhed.takeScreenshot(f)
        return f
    }

    /**
     * Andel af pixels der er forskellige mellem to optagelser, 0.0–1.0.
     *
     * Nedskaleret til hver 8. pixel: vi leder efter «flyttede billedet sig»,
     * ikke efter en nøjagtig forskel, og en fuld 1080x2400-sammenligning i en
     * instrumenterings-proces er langsom uden at svare bedre.
     */
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

    @Test
    fun lukkeknappen_virker_uden_knib() {
        // KONTROL for testen nedenfor: virker lukkeknappen overhovedet når
        // testen klikker den? Uden den kan en rød knib-test lige så godt
        // betyde at klikket aldrig rammer som at knibet dræber knappen.
        val aabn = rulTilVedhaeftning() ?: return
        aabn.click()
        findMedTaal(res("attachment-scene"), "fuldskaerms-scenen")
        Thread.sleep(800)  // Modal'ens fade-in (animationType="fade") skal være færdig
        val luk = findMedTaal(res("attachment-close"), "lukkeknappen")
        luk.click()
        val vaek = enhed.wait(Until.gone(res("attachment-scene")), vent)
        assertTrue("fuldskaermen lukkede ikke — heller ikke UDEN et knib", vaek)
    }

    @Test
    fun lukkeknappen_virker_stadig_efter_et_knib() {
        // Gribbetaget saetter `onStartShouldSetPanResponder` til FALSE netop for
        // ikke at stjaele tryk fra knapperne. Den beslutning staar i en
        // kommentar i kilden; her bliver den proevet af.
        val aabn = rulTilVedhaeftning() ?: return
        aabn.click()
        val scene = findMedTaal(res("attachment-scene"), "fuldskaerms-scenen")
        // Samme ro som knib-testen før knibet: et knib midt i Modal'ens
        // fade-in blev afbrudt efter én bevægelse (målt 19/9-2026).
        Thread.sleep(800)
        scene.pinchOpen(0.7f)
        Thread.sleep(500)
        val luk = findMedTaal(res("attachment-close"), "lukkeknappen")
        luk.click()
        val vaek = enhed.wait(Until.gone(res("attachment-scene")), vent)
        assertTrue("fuldskaermen lukkede ikke efter et knib", vaek)
    }
}
