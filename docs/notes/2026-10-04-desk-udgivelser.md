# Desk-udgivelser 4/10-2026 — 0.6.186 → 0.6.188

Kort log over hvad der gik ud i dag, og hvad der stadig står åbent.

## Udgivet

| version | tag | indhold |
|---|---|---|
| 0.6.186 | `05bfb587f` | navnet i foden, bug-ikonet og miljøfeltets øverste blok i samme hvide (`--fg-1`) |
| 0.6.187 | `f3f469f70` | diff-rød/grøn samlet i ét token — `--diff-add` / `--diff-del` i `tokens.css` |
| 0.6.188 | `41c9bb038` | codex' tre ting: «Ryd alle» på *Venter på dig*, krydset på opdateringskortet, «Installér nu» |

Farvearbejdet (0.6.187) kom med ind i 0.6.188 via flettet — begge spor rørte `app.css`,
og flettet gik rent.

## Åbent

- **Flaky test.** `JarvisBrowserPanel.test.tsx:122` fejlede `ci` på tag-kørslen for 0.6.188,
  men passerer 12/12 isoleret — og den *samme* commit gik grønt i `ci` på `main`.
  `desk-release` var upåvirket. Værd at se på: den kan fejle en fremtidig udgivelse uden grund.
- **BIOS.** fan5 (AIO-pumpen) følger CPU-temperaturen via `temp_sel=8` og svinger med load.
  Den skal låses — Bjørn tager den i BIOS.
- **Instrument-scanningen** forfaldt 18:33 UTC, ikke ~15:55. Grunden var ikke en fejl:
  `current_tick_tempo()` stod på 2.0, så cooldownen på 360 min blev 720.

## Rebases er blokeret i dette repo

`block-unattributed-rebase` afviser en replay, fordi den bærer en forældet `Actor`-trailer med.
Flet i stedet — det er hookens eget svar, og det gik rent.
