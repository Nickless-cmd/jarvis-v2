# Audit: run-ejerskab fra oprettelse til afregning

**Dato:** 14/10-2026 · **Omfang:** `run_event_log` → `detached_run._consume` → `_afregn_genoptaget_run`
**Foranledning:** ChatGPT's femte indvending mod `c070b7244`.
**Status:** ét hul målt og stadig åbent; den nære rettelse målt **skadelig** og rullet tilbage; den ægte rettelse kræver oprettelsespunktet.

## Kæden, målt i kilden

| Trin | Hvad sker | Hvor |
|---|---|---|
| 1. Log oprettes | `claim_or_create(sid)` eller `rel.create(run_id, sid)` | `detached_run.py:236`, `:537` |
| 2. Wrapper-id | `run_id` = log-id'et; `start_user_run_detached` kører under det | `detached_run.py:487` |
| 3. Indre run fødes | `start_visible_run` laver sit EGET id: `visible-{uuid4}` | `visible_runs.py:964` |
| 4. Rammen bærer det | `run`-eventet: `{"run_id": run.run_id}` — runnets eget, ikke wrapperens | `visible_runs.py:1325` |
| 5. Alias bindes | `rel.alias(eget, run_id)` — kræver `lid in _RUNS` | `detached_run.py:370` |
| 6. Afregning | `ramme_ejerskab(inner_run_id, wrapper_run_id)` | `detached_run.py:40` |

## Hullet — målt, og stadig åbent

`_consume()` afviser kun `FOREIGN`:

```python
if eget and rel.ramme_ejerskab(eget, run_id) == rel.EJERSKAB_FOREIGN:
    # afvist
elif eget:
    rel.alias(eget, run_id)   # ← UNKNOWN slipper igennem
```

**Målt 14/10-2026** (test gennem den virkelige `_consume()`-vej, mod den
uændrede kode): en ramme med et id der hverken fandtes i `_RUNS` eller
`_ALIASER` gav

```
_ALIASER = {'visible-fremmed-ukendt': 'visible-70dc78b354bf41f2ae002c71b2312a5c'}
ramme_ejerskab('visible-fremmed-ukendt', <wrapper>) == 'owned'
```

Kontrollen er **cirkulær**: den bekræfter et alias som rammen selv satte.

## Den nære rettelse — målt SKADELIG, rullet tilbage

Kravet «kun `OWNED` må binde» blev bygget og målt. Konsekvensen, ordret fra
kørslen:

```
WARNING detached_run: ramme med unknown id visible-vores-eget afvist — binder ikke alias for visible-gen
WARNING opgave opg-A kan ikke afregnes endnu: run visible-gen status=mangler
```

Årsagen er strukturel: et **nyt** indre run er `unknown` **pr. konstruktion**.
`start_visible_run` genererer sit id inde i generatoren (`visible_runs.py:964`),
og det id er hverken i `_RUNS` eller `_ALIASER` når rammen kommer. Bindes
aliaset ikke, bliver `indre_run_id` tom, afregningen falder tilbage til
wrapperens id — hvis post ikke bærer nogen terminal status — og **opgaven
afregnes aldrig**; den brænder sit forsøgs-loft op i stedet.

Et strengt `owned`-krav er altså en **værre fejl end hullet det lukker**.
Rettelsen er rullet tilbage. Kravet står nu som `xfail(strict=True)` i
`tests/test_detached_run.py`, så hullet er fastholdt og melder sig, når det
lukkes.

## Den ægte rettelse — design, ikke bygget

Bindingen skal komme fra **oprettelsespunktet**, ikke fra rammen. Skitse:

1. `start_visible_run` får `wrapper_run_id: str = ""`.
2. Værdien lægges i `run`-eventets payload (`visible_runs.py:1325`).
3. `detached_run.visible_args` sender `"wrapper_run_id": run_id`.
4. `_consume` accepterer kun en ramme der erklærer **netop vores** wrapper.

Generatoren er vores egen og får id'et som argument, så en fremmed ramme kan
ikke bære det.

**Premissen er nu afgjort — statisk, i kilden (målt 14/10-2026 efter auditten).**
Spørgsmålet var *hvorfor* et fremmed id kan nå vores strøm. Den ene af de to
mekanismer er udelukket:

- **Vores egen generator kan IKKE adoptere et fremmed run.** `start_visible_run`
  genererer sit id lokalt (`run_id=f"visible-{uuid4().hex}"`,
  `visible_runs.py:964`), og hver `run_id` der emitteres kommer fra `run.run_id`
  (`:1264`, `:1328`). Den globale aktiv-run-slot bruges kun til at **rydde**
  (`_set_active_visible_run({})`, `:745`, `:785`) og til at **læse** `run_id` for
  levetids-tjek (`:722`, `:768`) — den skriver aldrig et id ind i runnet.
- Derfor må det fremmede id være kommet fra **en anden `start_visible_run`-kalds
  frames**, der løb ind i vores strøm.

**Konsekvens for designet: stemplet virker.** En ramme fra et andet kald bærer
*det* kalds wrapper-id, ikke vores — så `_consume` kan skelne dem. Premissen er
dermed ikke længere et åbent punkt.

**Hvad der stadig ikke er målt:** *hvor* de to strømme blandes — hvilket led der
lækker frames mellem to samtidige runs i samme session. Stemplet gør afregningen
immun over for blandingen, men det kurérer ikke blandingen selv.

## Ærlig begrænsning

`_RUNS`/`_ALIASER` er **proceslokale** og forsvinder ved genstart. `--workers 1`
betyder API'ens tråde deler dem, men `jarvis-runtime` er en separat proces.
Tabellen er præcis nok til frame-routing i én proces — ikke et varigt,
tværproces bevis. Et id kendt før en genstart er `unknown` bagefter.

## Ikke målt

- Om sekvensen er forekommet i **produktion**. Hullet er målt i test, ikke i drift.
- Om `run_er_terminal()` kan lukke opgaven når journal-posten mangler
  (`rec is None`): opgave-relations-tjekket springes da over. Åbningen står i
  kilden, uafprøvet.
- `mark_visible_run_started` sender **intet** `task_id` (`visible_run_journal.py:12`),
  så det indre runs journal-post har tomt `task_id` — og relations-tjekket i
  `_afregn_genoptaget_run` springer derfor over i praksis. Kontrollen er ikke
  virkningsløs, men den bider sjældnere end den ser ud til.
