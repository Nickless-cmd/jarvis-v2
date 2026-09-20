# Noter: beslutninger med en status og en slags

`docs/notes/` var en flad bunke daterede filer uden status og uden slags. Man
kunne ikke se om en note beskrev noget der VAR bygget, noget der var
foreslået, eller noget der var opgivet — og slet ikke finde «alle de gange vi
har fjernet noget igen».

DeepSeek-harness deler deres noter i `implemented` / `proposed` / `archived`
gange seks slags, og håndhæver det med en checker. Det væsentlige i deres
opdeling er ikke mapperne. Det er at **`simplification` er en slags på lige
fod med `feature`**: hos dem er der 24 noter om at rulle kompleksitet tilbage.
At fjerne noget igen er dokumenteret arbejde, ikke noget der sker i tavshed
fordi det føles som et nederlag.

## Formen

```
docs/notes/<status>/<slags>/ÅÅÅÅ-MM-DD-kort-slug.md
```

| Status | Betyder |
|---|---|
| `implementeret` | Det er bygget og står i koden nu |
| `foreslaaet` | Det er besluttet på papir, ikke bygget |
| `arkiveret` | Det gjaldt engang. Frosset — rettes ikke, erstattes af en ny note |

| Slags | Betyder |
|---|---|
| `arkitektur` | En grænse, et ejerskab, en kontrakt |
| `fejlrettelse` | En fejl med en rod, ikke et symptom |
| `funktion` | Noget nyt han kan bruge |
| `proces` | Hvordan vi arbejder — hooks, vagter, commit-form |
| `forenkling` | Noget er FJERNET eller rullet tilbage |
| `test` | Hvordan noget måles eller bevises |

Hver note har fire overskrifter, i denne rækkefølge:

* **Problem** — hvad der faktisk skete, helst med et målt tal
* **Beslutning** — hvad vi gjorde
* **Overvejede alternativer** — hvad vi fravalgte, og hvorfor
* **Konsekvenser** — hvad det koster, og hvad vi IKKE kan love

Den tredje er den vigtige. En note uden fravalg er en annoncering, ikke en
beslutning, og om et halvt år kan ingen se hvorfor vejen ikke blev taget.

## Hvad der ikke flyttes

De 21 flade filer fra før 20/9-2026 bliver liggende hvor de er. En
oprydning der omskriver gammel historik for at tilfredsstille en ny form,
ødelægger mere end den ordner. Formen gælder nye noter.

`scripts/verify_notes.py` håndhæver sti, overskrifter og rækkefølge.
