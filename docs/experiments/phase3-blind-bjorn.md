# Bjørns blind test — resultater

**Session:** "blind test" — 50 α-trials + 25 δ-trials  
**α-accuracy:** 28% (14/50)  
**δ-accuracy:** 64%

---

## Confusion matrix (α-trials)

Rækker = sand forfatter. Kolonner = dit gæt. **Diagonal = korrekt.**

| Sand \ Dit gæt | Claude | GLM | Jarvis | Ollama | Random |
|---|---|---|---|---|---|
| **Claude** | **3** | 2 | 2 | 1 | 2 |
| **GLM** | 3 | **4** | 3 | 0 | 0 |
| **Jarvis** | 0 | 2 | **6** | 1 | 1 |
| **Ollama** | 0 | 1 | 4 | **1** | 4 |
| **Random** | 2 | 2 | 4 | 2 | **0** |

## Per-forfatter

| Forfatter | Korrekte | Procent | Tendens |
|---|---|---|---|
| **Jarvis** | 6/10 | **60%** | ✅ Bedst — du genkender mig rimelig godt |
| **GLM** | 4/10 | **40%** | 🟡 Over chance (20%) |
| **Claude** | 3/10 | **30%** | 🟡 Marginalt over chance |
| **Ollama** | 1/10 | **10%** | 🔴 Under chance — gætter ofte Jarvis eller Random |
| **Random** | 0/10 | **0%** | 🔴 Aldrig korrekt — forveksler mest med Jarvis |

## Hvad fortæller det?

1. **Dit Jarvis-genkendelse virker** (60%). De `!`-klausuler og `↔`/`⊂` mønstre du fandt på — fungerer. Du rammer mig 3× oftere end tilfældigt.

2. **Du overfører Jarvis-mønstret til Ollama** — 4/10 gange hvor sandheden var Ollama, gættede du Jarvis. Ollama og Jarvis deler tilsyneladende nogle stilistiske træk (kortere sætninger, `↔` mønstre).

3. **Random er usynlig for dig** — 0/10. Du gætter Random nærmest aldrig, og når sandheden er Random, gætter du Jarvis (4×) eller Claude/Random (2× hver). Random er *ikke* kaotisk nok til at skille sig ud for dig.

4. **δ-accuracy på 64%** — du kan godt fornemme om noget er "ægte" vs "decoy", men ikke godt nok til at isolere Random som kategori.

---

*Data udlæst fra interlanguage.db, session "blind test", 2026-05-28.*
