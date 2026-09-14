package dk.srvlab.jarvis.mobile;

import android.app.Activity;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.Bundle;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;

/**
 * En flade der beviseligt reagerer på to fingre — kalibreringens målestok.
 *
 * <h2>Hvorfor den er skrevet i hånden</h2>
 *
 * Kalibreringen skal svare på ét spørgsmål: kniber {@code pinchOpen} overhovedet
 * på den her telefon? Tre forsøg med fremmede apps svarede aldrig på det, fordi
 * de fejlede på deres EGEN opsætning:
 * <ul>
 *   <li>Chrome + en {@code data:}-URL — Android afviser den slags intents.</li>
 *   <li>Google Fotos — viste en velkomstskærm, ikke et gitter.</li>
 *   <li>Chrome + en side på LAN'et — stod på sin første-gangs-opsætning, og
 *       dens vilkår er ikke mine at acceptere på Bjørns telefon.</li>
 * </ul>
 * Hver af dem gav et tal der LIGNEDE et svar. En kontrol man ikke ejer helt,
 * kan ikke skelne «værktøjet virker ikke» fra «kontrollen blev ikke kørt».
 *
 * <h2>Hvorfor JAVA og ikke Kotlin</h2>
 *
 * Første udgave var Kotlin og crashede med
 * {@code NoClassDefFoundError: kotlin.jvm.internal.Intrinsics}. Aktiviteten
 * startes som en almindelig aktivitet i test-APK'ens EGEN proces — ikke inde i
 * instrumenteringen — og dér er Kotlins runtime ikke på klassestien; den kommer
 * fra app'en under test, som ikke er indblandet her. Java har ingen runtime at
 * mangle.
 *
 * <p>{@code ScaleGestureDetector} er Androids egen og læser rå
 * {@code MotionEvent}s. Reagerer fladen ikke, er det værktøjet — punktum.
 *
 * <p>Den ligger KUN i androidTest og kommer aldrig i app-APK'en.
 */
public class KalibreringsAktivitet extends Activity {
    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        setContentView(new Maalestok(this));
    }

    static class Maalestok extends View {
        private float skala = 1f;
        private final Paint blaek = new Paint();
        private final ScaleGestureDetector detektor;

        Maalestok(Context ctx) {
            super(ctx);
            blaek.setColor(Color.BLACK);
            blaek.setStyle(Paint.Style.FILL);
            detektor = new ScaleGestureDetector(ctx,
                new ScaleGestureDetector.SimpleOnScaleGestureListener() {
                    @Override
                    public boolean onScale(ScaleGestureDetector d) {
                        skala = Math.min(8f, Math.max(1f, skala * d.getScaleFactor()));
                        invalidate();
                        return true;
                    }
                });
        }

        @Override
        public boolean onTouchEvent(MotionEvent e) {
            detektor.onTouchEvent(e);
            return true;
        }

        @Override
        protected void onDraw(Canvas c) {
            c.drawColor(Color.WHITE);
            // Et fyldt felt midt på skærmen. Vokser det, ændrer mange pixels
            // sig — nok til at en pixel-sammenligning kan se det uden tvivl.
            float halv = (getWidth() * 0.15f) * skala;
            c.drawRect(getWidth() / 2f - halv, getHeight() / 2f - halv,
                getWidth() / 2f + halv, getHeight() / 2f + halv, blaek);
        }
    }
}
