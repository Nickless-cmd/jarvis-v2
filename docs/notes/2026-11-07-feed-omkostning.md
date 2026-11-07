# Feed-omkostning: «de 929 andre» (7/11-2026)

## Kort

Premissen holdt ikke. Målt mod den levende DB er de «andre» familier **ikke**
95 % af hydreringen: de koster ~0,3 ms ud af ~9 ms. Den reelle omkostning er
**antallet af åbne rækker** (indlæsning + JSON-parse + payload), og den er
~19 ms pr. `feed()`, ikke 169 ms. Rettelsen lukker aldrende, aldrig-kvitterede
familier og halverer feed-tiden.

## Måling FØR (live DB, `feed()` kørt skrive-fri)

Metode: `feed()` mod `~/.jarvis-v2/state/jarvis.db` med `luk`, `genaabn`,
`paa_godkendelse` og `paa_forslag` stubbet til no-op, så målingen ikke ændrer
data. Varm første kald, derefter median af 5-7 kald.

- `feed()` hel: **~18,6-19,1 ms**, 1.320 rækker returneret.
- `aabne()` alene: ~5 ms; kaldes 3 gange pr. poll (feed + to afstemninger).
- `afstem_forslag`: ~4,9 ms. `afstem_godkendelser`: ~0 ms.

Hydrering pr. slags (`_hydrer`, åbne rækker):

| slags | kilde | n | total | pr. række |
|---|---|---|---|---|
| run_done | run | 380 | 8,4 ms | 0,022 ms |
| proposal | proposal | 3 | 0,4 ms | 0,145 ms |
| run_failed | run | 16 | 0,2 ms | 0,010 ms |
| infra_security | egen | 402 | 0,2 ms | ~0 |
| session_inbox:genstart | egen | 262 | 0,1 ms | ~0 |
| reach_out | egen | 99 | ~0 | ~0 |
| release | egen | 79 | ~0 | ~0 |
| øvrige egen (7 slags) | egen | 78 | ~0 | ~0 |

## De fire spørgsmål

1. **Dyr opslag-vej for infra_security / genstart?** Nej. Begge har
   `kilde='egen'`, og `_hydrer` returnerer for `egen` med det samme uden
   opslag (~0,0003 ms/række). Kun `run_done` (0,022 ms, `svar_for_run` =
   egen DB-forbindelse + dekryptering) og `proposal` har en ejer-vej. 169 ms
   kunne ikke genskabes; 8 ms af ~9 ms hydrering er stadig `run_done`.
2. **Kvitteret af et menneske?** Nej. Rækker lukket de seneste 7 dage:
   run_done 888 (alle `foraeldet`), approval 84, proposal 29 — **ingen**
   infra_security, genstart, reach_out eller release, og ingen `seen` for dem.
   Forbehold: `ryd_gamle` sletter klarede rækker efter 7 dage, så «aldrig» er
   bevist for 7 dage, men de åbne er op til 24 dage gamle (14/10), så ingen
   har lukket dem i den tid.
3. **Fælles årsag?** Ja: intet lukker dem. `luk_foraeldede` dækkede kun
   `run_done` (`slags`-default), og kaldes kun ved opstart — de 380 åbne
   run_done er op til 3 dage gamle, fordi API'et har kørt siden.
4. **Øvre grænse pr. slags / undlad hydrering?** Hydreringen er allerede
   billig for disse familier, så «undlad at hydrere» sparer intet. En grænse pr.
   slags ville skjule rækker uden at rydde dem. Rigtig løsning: ryd dem.

## Rettelse

- `notifikationer.py`: `FORAELDES_EFTER_DAGE` (run_done, infra_security,
  genstart, proactivity-bridge: 2 dage; reach_out, release: 7 dage).
  `luk_foraeldede()` uden argumenter dækker alle; `slags=`/`dage=` snævrer
  ind/tilsidesætter. Rækkerne **bevares** (`klaret` + `udfald='foraeldet'`),
  så de ses i `tidligere()`.
- `notifikationer_hydrering.py`: `feed()` kalder `luk_foraeldede()` før
  hydrering, throttlet til hvert 10. minut og med fejl logget, ikke kastet.
  Opstarten (`notifikations_opstart.py`, uden for scope) kalder allerede
  `luk_foraeldede()` uden argumenter og får de nye familier med.
- Med vilje ikke lukket på alder: approval, proposal, keymaker_key_pending,
  reminder, approval_expired, drift, central_flag, maaling, keymaker_key_earned
  — de kan være noget nogen skal handle på.

## Måling EFTER

Rettelsen er ikke kørt mod den levende DB (ville skrive til produktionsdata
uden din godkendelse). I stedet simuleret: samme måling, men `aabne()`
filtreret i SQL med præcis de samme aldersgrænser:

- FØR: 1.320 rækker, **~19,0 ms**
- EFTER: 444 rækker, **~10,7 ms** (samme data, to kørsler: 10,7 / 10,8)

Første rigtige `feed()`/genstart lukker 876 rækker. Resten (~10 ms) er
`run_done`-hydrering og `afstem_forslag`; udenfor denne opgaves scope.

## Tests

`tests/test_notifikationer_hydrering.py` (4 nye): aldrende støjfamilier lukkes
via `feed()` og bevares i `tidligere()`; reach_out/release har 7 dages grænse;
approval/keymaker/reminder/approval_expired lukkes aldrig på alder;
throttle + lukning der kaster tømmer ikke feedet. Mutationskørt: uden kaldet i
`feed()` fejler 3, uden `infra_security` i tabellen fejler 1.
