# Codex-kvotemåling: gå bagud til en fil med rate_limits

Status: implementeret
Slags: fejlrettelse

## Problem

`codex_quota()` returnerede `ok=False, error="ingen rate_limits i rollout-2026-11-06T09-44-23-…jsonl"`.
`_latest_rollout()` tog den nyeste fil efter mtime og gav den videre uden at
tjekke om den havde `rate_limits`. Den nyeste fil (09:44) havde ikke feltet.
Den seneste fil MED feltet var fra 5/11 (13-14 timer gammel).

Målt på den rigtige mappe efter rettelsen (~/.codex/sessions, 6/11-2026):
primary 0 % (300 min, vinduet udløbet 5/11 23:46 UTC, så nulstillet; filen
selv sagde 2 %), secondary 90 % (10080 min, nulstilles 9/11 21:25 UTC),
plan `plus`, `stale_hours` = 14.0.

## Beslutning

- `_latest_rollout()` er erstattet af `_recent_rollouts(10)`: de 10 nyeste
  filer, nyeste først. `_load_codex_quota()` tager den første der indeholder
  `rate_limits`.
- Findes ingen, fejler målingen stadig ærligt. Beskeden nævner antal prøvede
  filer og den nyeste fils navn.
- `QuotaReading.stale_hours` (float, standard -1.0 = ukendt) bærer filens alder
  i timer. `observed_at` er fortsat filens egen mtime, ikke «nu». Feltet
  følger med gennem cachen.
- Tests i `tests/test_dispatch_quota.py`: nyeste fil uden felt + ældre med
  felt giver den ældres tal og `stale_hours` ≈ 13; ingen fil med felt giver
  fejl med «prøvede 3 filer»; grænsen på N filer holder.
- Mutationstjek: med opslagsdybden sat til 1 (kun nyeste fil) fejler to af
  de tre nye tests. Grænsetesten består da, hvilket er korrekt, fordi
  dybde 1 også fejler ærligt.

## Overvejede alternativer

- **Gå bagud uden grænse.** Fravalgt: i værste fald læses hele sessionsmappen,
  og en måling fra uger siden ligner et tal uden at være det. Grænsen er 10.
- **Afvise målinger over en alder.** Fravalgt: det ville ændre
  blokeringslogikken (`quota_preflight`), og det er uden for opgaven. Alderen
  gøres kun synlig.
- **Ny kvotekilde, fx Codex-API'et.** Fravalgt: opgaven var kun bagudsøgning
  og aldersfelt.

## Konsekvenser

- Målingen kan nu være timer gammel og stadig `ok=True`. Kalderen skal læse
  `stale_hours`; ingen kalder gør det endnu.
- 10 filer kan alle være uden feltet, så målingen fejler stadig, men nu med
  et tal der viser hvor langt der blev ledt.
- Udløbne vinduer nulstilles til 0 % ud fra reset-tidspunktet, som før.
  Den gamle fil sagde 2 % primary, målingen viser 0 %.
- Åbent: `quota_preflight` bruger ikke `stale_hours`. Om en gammel måling skal
  advare eller blokere er ikke besluttet. Claude-kvoten er urørt, og
  tærskler og `hard_block` er urørte.
- Åbent: hvorfor nyere rollout-filer mangler `rate_limits` er ikke undersøgt.
- Noten ligger flad i `docs/notes/` efter opgavens sti. `verify_notes.py`
  tjekker kun `docs/notes/<status>/<slags>/`, så guarden har ikke set den.
