# `core.util` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/util/timezone.py`
_Central Copenhagen timezone utilities — én sandhedskilde for dansk tid._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `dk_now` | `()` | Return current datetime i Danmark (CEST/CET). | [src](../../../core/util/timezone.py#L38) |
| function | `dk_timestamp` | `()` | ISO timestamp i dansk tid, f.eks. '2026-06-10 15:31:45 CEST'. | [src](../../../core/util/timezone.py#L43) |
| function | `dk_hour` | `()` | Nuværende time i Danmark (0-23). | [src](../../../core/util/timezone.py#L49) |
| function | `dk_date_str` | `()` | Dansk dato, f.eks. '10. juni 2026'. | [src](../../../core/util/timezone.py#L54) |
| function | `dk_time_str` | `()` | Klokkeslæt, f.eks. '15:31'. | [src](../../../core/util/timezone.py#L60) |
| function | `dk_weekday_da` | `()` | Dansk ugedag, f.eks. 'onsdag'. | [src](../../../core/util/timezone.py#L65) |
| function | `dk_weekday_en` | `()` | — | [src](../../../core/util/timezone.py#L70) |
| function | `is_dk_quiet_hours` | `(quiet_start=…, quiet_end=…)` | Er vi indenfor stille-tid (default 22:00-07:00 dansk tid)? | [src](../../../core/util/timezone.py#L74) |
| function | `from_utc_iso` | `(iso_str)` | Parse en UTC ISO-streng og konvertér til dansk tid. | [src](../../../core/util/timezone.py#L89) |
| function | `time_label_dk` | `(iso_str)` | Konvertér en ISO-streng til dansk tidslabel, f.eks. '15:31'. | [src](../../../core/util/timezone.py#L106) |
| function | `dk_label` | `(iso_str)` | Dato + klokkeslæt i dansk tid, f.eks. 'ons 11/11 09:59'. | [src](../../../core/util/timezone.py#L118) |

