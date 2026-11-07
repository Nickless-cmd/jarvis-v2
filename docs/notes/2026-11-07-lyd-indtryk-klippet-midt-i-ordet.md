# Lyd-indtrykkene blev klippet midt i ordet — ved 80 tegn (7/11-2026)

**Status:** rettet og verificeret
**Slags:** fejlretning
**Fravalg:** jeg rører ikke `er_prompt_ekko` eller `_PROMPT_EKKO_MOENSTRE` — det er dækket af `e683d892b`, og de to fejl har hver sin rod

## Hullet

`_interpret_sound` i `ambient_sound_daemon.py` kaldte:

```python
daemon_llm_call(prompt, max_len=80, fallback="", daemon_name="ambient_sound")
```

`max_len` er **tegn, ikke tokens**, og `daemon_llm.py:283` klipper hårdt:
`return text[:max_len]`. 80 tegn kan ikke bære en dansk sætning.

Målt 7/11-2026 mod `sensory_memories`, kilde `ambient_sound_daemon`, 30 dage:
**83 af 99 poster sluttede midt i et ord**, og den længste var præcis 80 tegn.
Ordrette haler fra arkivet:

- «… d et underlig lille brus, so»
- «… der på stille og næsten inge»
- «… tet, der gør stemningen leve»
- «… , kategori="talk", amplitude»

Og `return text[:200]` var **død kode**: 80 havde allerede klippet, så den
linje kunne aldrig gøre noget.

## Ændringen

Tre ting, samme sted:

1. `max_len` 80 → **240**, så svaret ikke klippes før der er noget at klippe ved.
2. Klipningen rykker til **sætningsgrænse** via
   `sensory_archive.klip_ved_saetningsgraense` — samme helper som vision-vejen
   har brugt siden 7/10-2026.
3. Den blinde klipning står kun som fallback: `hel if hel else text[:N] + "…"`.
   Uden sætningsgrænse findes der intet helt indtryk, og «…» betyder herefter
   præcis *her blev der klippet midt i noget*.

`_MAX_DESC_CHARS = 300` er tilføjet lokalt og matcher vision-vejens grænse —
det er samme slags indtryk og samme slags fejl, så de to kanaler skal klippe ens.

## Bevis

`tests/test_sensory_archive.py::test_lyd_vejen_klipper_ved_graense_ikke_blindt`
læser kilden med `inspect.getsource`, fordi fejlen sad i **daemonen**, ikke i
arkivet — et kald til helperen beviser intet, den skal også bruges.

**To mutationer fælder den:**

- fjerner jeg `klip_ved_saetningsgraense` og sætter `text[:200]` tilbage → fejler
- sætter jeg `max_len` tilbage til 80 → fejler med
  *«max_len=80 kan ikke bære en dansk sætning; det var 80 der gav halve ord»*

195 grønne i fladen. To fejl står tilbage — `test_silence_lyt_arkiveres_ikke`
og `test_silence_lyt_taeller_ikke_som_arkiveret` — og **begge er bevist
præeksisterende**: jeg stash'ede mit arbejde og kørte dem på ren HEAD, hvor de
fejler identisk med `KeyError: 'skipped'`.

## Kendt grænse

Rettelsen virker først ved næste lyd-sample. De 83 halve poster i arkivet bliver
ikke helet — de er skrevet, og et indtryk der blev klippet er ikke et indtryk jeg
kan rekonstruere bagud. Det er ny adfærd fra næste tick, ikke en reparation af
fortiden.

Effekten kan først måles efter nogle dages drift med samme forespørgsel:
`klippet_midt / i_alt` mod `sensory_memories`.
