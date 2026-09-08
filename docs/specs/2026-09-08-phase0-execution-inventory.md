# Phase 0 — inventar over udførelses-stier

Dato: 2026-09-08 · Hører til [DeepSeek Harness Lessons for Jarvis-v2](2026-09-08-deepseek-harness-lessons-for-jarvis.md)

Spec'ens Fase 0, punkt tre: *«inventory every shell/subprocess path and record
its actual sandbox, network, environment, cancellation, and fail-open/fail-closed
behavior»*. Udgangs-kriteriet er skarpt formuleret: *«no surface claims sandbox
enforcement more strongly than the inventory proves»*.

## Tallet

**53 filer i `core/` og `apps/api/` starter underprocesser. Én af dem går
gennem sandkassen.**

Blandt de model-kaldbare værktøjer:

| værktøjsfil | sandkasse |
|---|---|
| `core/tools/simple_tools_web.py` (engangs-bash) | **ja** |
| `core/tools/bash_session.py` (persistent shell) | nej |
| `core/tools/workspace_capabilities_execute.py` | nej |
| `core/tools/process_tools.py` | nej |
| `core/tools/worktree_tools.py` | nej |
| `core/tools/claude_dispatch/{tool,runner,worktree}.py` | nej |
| `core/tools/phone_adb.py` | nej |
| `core/tools/screen_tool.py` | nej |
| `core/tools/github_tools.py` | nej |
| `core/tools/verify_tools.py` | nej |
| `core/tools/code_navigation_tools.py` | nej |
| `core/tools/restart_self_tools.py` | nej |
| `core/tools/auto_ensure_tests.py` | nej |
| `core/tools/mic_listen_tool.py` | nej |
| `core/tools/workspace_capabilities.py` | nej |

Sytten værktøjsfiler starter processer; seksten af dem kan ikke indespærres.

## Det er ikke nødvendigvis forkert — men det skal stå skrevet

Flere af de seksten er bevidste. Den persistente shell er **med vilje** uden
gate: den er ejerens vej udenom systemet, og den beslutning står ved magt.
Andre (adb, skærm, mikrofon) giver ingen mening at bwrap'e.

Pointen er ikke at sandkassen skal dække alt. Pointen er udgangs-kriteriet:
**ingen flade må love mere indespærring end inventaret beviser.** Med én dækket
sti ud af 53 er der god plads til at love for meget.

Oveni gælder Gap H's tre målte forhold for den ene dækkede sti:

1. `is_enabled()` defaulter til **slukket** — usat betyder fra.
2. Den dækker kun **engangs**-vejen, ikke den persistente shell.
3. Den **fejler åbent**: mangler `bwrap`, køres kommandoen alligevel.

Modulets egen docstring formulerer det bedre end en spec kan: *«Et halvt
dækkende lag der er tændt er værre end et der er slukket, for det giver en
tryghed der ikke svarer til virkeligheden.»*

## Hvad Fase 3 skal levere

Spec'ens Fase 3-kriterium er allerede den rigtige formulering:

> every process-producing provider reports requested policy and actual
> enforcement; requested confinement fails before execution when unavailable

Det kræver to ting som inventaret nu gør muligt at planlægge:

- **En rapporteret håndhævelses-kvalitet pr. sti** — fuld, delvis, utilgængelig,
  eller eksplicit fuld adgang. Ikke en boolean.
- **Fejl-lukket når en profil LOVER indespærring.** Det står ikke i modstrid med
  at bash-vejen fejler åbent i dag: forskellen er om nogen har lovet noget. En
  sti der ikke lover indespærring må gerne køre uindespærret; en der gør, må
  ikke.

## Endnu ikke målt

`network`, `environment` og `cancellation` pr. sti står tilbage. De 53 stier
skal gennemgås enkeltvis for:

- arver processen forældrens miljø (og dermed hemmeligheder)?
- kan den nå nettet?
- bliver den faktisk dræbt når runnet afbrydes, eller lever den videre?

Det sidste har vi allerede set fejle i praksis: baggrundsjob der overlevede
deres run stod som `lost` i process-supervisoren efter en runtime-genstart.
