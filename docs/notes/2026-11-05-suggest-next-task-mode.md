# suggest_next_task: chat vs code mode (målt 5/11-2026)

**Anbefaling: gør IKKE værktøjet chat-only, og byg ingen mode-grænse i `mangler_stilling()`.**
Vagten er allerede FRA (default siden 19/10) og forklarer ikke forskellen. Code-forslag
bliver brugt MERE end chat-forslag. Forskellen er en skæv forventning, ikke en fejl.
Intet er ændret i koden; kun denne note er skrevet.

## Hypotesen er falsificeret

Hypotesen var: vagten (`suggest_standing_guard`) fyrer oftere i code mode og tvinger en ekstra runde.

1. `suggest_standing_guard_enabled()` returnerer **False** som default siden 19/10-2026
   (`core/services/suggest_standing_guard.py`). Hverken `jarvis-api.service` eller
   drop-in'en sætter `JARVIS_SUGGEST_STANDING_GUARD`. Vagten er altså ikke aktiv i de tal du målte
   (events starter 22/10).
2. Journalen har 171 `suggest-standing`-linjer, alle 17/10 (25), 18/10 (86) og 19/10 (60, sidste
   kl. 20:31). Derefter ingen. Journalen går ikke længere tilbage end 17/10, så vagtens runder
   før/efter 7/10 kan ikke tælles; den dækker kun 17-19/10.
3. Frekvensen i code mode er næsten uændret med vagten FRA (se tabellen), og var den samme
   FØR vagten fandtes. Det er modellens eget valg.

## Tal

Kilde: `composer_choices` (en række pr. vist forslag) joinet til `chat_sessions.kind`;
beskeder fra `chat_messages` (role='assistant'). `cache.telemetry` findes ikke som tabel i nogen
`.db` under `~/.jarvis-v2`, og `visible_runs` har ingen `session_id`, så *runs* pr. mode kan ikke
måles direkte. Jeg bruger assistent-beskeder som nævner. Tallene kan derfor ikke sammenlignes
1:1 med «pr. 100 runs» i opgaven (der fik 67 code-kald; denne måling får 77 forslag i
vagt-FRA-perioden, andet vindue og anden kilde).

| Periode | Mode | Forslag | Accepteret | Eget (skrev selv) | Vist (ingen handling) | Accept-rate | Ass.-beskeder | Forslag/100 beskeder |
|---|---|---|---|---|---|---|---|---|
| A: 28/9-7/10 (før vagt) | chat | 0 | – | – | – | – | 188 | 0,00 |
| A | code | 86 | 38 | 33 | 15 | 44,2 % | 1153 | 7,46 |
| B: 7/10-19/10 (vagt TIL) | chat | 62 | 13 | 41 | 8 | 21,0 % | 451 | 13,75 |
| B | code | 398 | 238 | 121 | 39 | 59,8 % | 1239 | 32,12 |
| C: 19/10- (vagt FRA) | chat | 17 | 4 | 12 | 1 | 23,5 % | 1441 | 1,18 |
| C | code | 77 | 32 | 35 | 10 | 41,6 % | 1232 | 6,25 |

Aflæsning:
- Code er 5,3x chat i periode C (6,25 mod 1,18) uden vagt. Før vagten var code 7,46 pr. 100.
  Vagten løftede code til 32 og chat til 14 (B), og begge faldt tilbage, da den blev slået fra.
  Skævheden mellem modes er altså der uden vagten.
- Accept-raten (valg = 'accepteret') er højere i code i alle perioder hvor der er data:
  44/60/42 % mod 21/24 % i chat. Code-forslag er ikke støj.
- Hele historikken: code 323 accepteret / 974 forslag (33 %), chat 18 / 94 (19 %).

## Hvad der IKKE kunne måles

- **Kostede den ekstra runde noget?** Runder pr. tur før/efter 7/10 kan ikke beregnes: tabellen
  `events` starter 22/10 (efter vagten blev slået fra), og journalen starter 17/10. Det ville kræve
  en run-tabel med runde-tælling pr. `run_id` og `session_id` fra før 7/10. Prisen er dog allerede
  dokumenteret i kildens docstring (ekstra runde skubber folden, målt 19/10), og det er derfor vagten er FRA.
- **Vagt vs. modellens eget valg for de 67/77 kald**: vagt-linjer findes kun 17-19/10; alle kald
  efter 19/10 er per definition modellens eget valg, da vagten var FRA.
- Run-baseret rate (opgavens nævner): kræver `run_id` → `session_id`. `tool.invoked` har
  oftest `session_id="UKENDT"`.

## SQL / kommandoer

```sql
-- forslag og valg pr. mode og periode (sqlite3, read-only)
SELECT s.kind, sum(ch.valg='accepteret'), sum(ch.valg='eget'), sum(ch.valg='vist'), count(*)
FROM composer_choices ch JOIN chat_sessions s ON s.session_id = ch.session_id
WHERE ch.vist_at >= :lo AND ch.vist_at < :hi
GROUP BY s.kind;

-- assistent-beskeder pr. mode og periode
SELECT count(*) FROM chat_messages m JOIN chat_sessions s ON s.session_id = m.session_id
WHERE s.kind = :kind AND m.role = 'assistant' AND m.created_at >= :lo AND m.created_at < :hi;
```

Perioder: `:lo/:hi` = 2026-09-28/2026-10-07, 2026-10-07/2026-10-19T20:31, 2026-10-19T20:31/2026-12-31.

```bash
journalctl -u jarvis-api --no-pager -o short-iso | grep "suggest-standing" | cut -c1-10 | sort | uniq -c
```

## Begrundelse for anbefalingen

- Chat-only ville fjerne det værktøj, der bliver mest brugt (33 % accept i code) for at undgå en
  skævhed, der ikke er skadelig.
- Mode-grænse i `mangler_stilling()` retter en vagt, der er slået fra.
- Hvis forslag i chat føles for få, er det en prompt-sag (`output_discipline`), ikke en kode-sag.
  Chat-sessioner er mest samtale uden et teknisk næste skridt.
- Forbehold: «eget» (kun 21-36 % i code, men 54-77 % i chat) viser, at Bjørn oftere skriver selv i
  chat, så chat-forslag rammer dårligere. Det er en mulig senere finjustering af prompten, ikke et
  bevis for støj.
