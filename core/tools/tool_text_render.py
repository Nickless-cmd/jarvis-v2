"""Læsbar `text`-form for strukturerede tool-resultater.

Hvorfor det ikke er kosmetik: `format_tool_result_for_model` bruger en
``text``-nøgle hvis den findes. Findes den ikke, dumpes hele resultatet som
JSON og **cappes ved 8000 tegn** — mens et tool der leverer ``text`` får
16000. Formen, ikke størrelsen, afgør altså loftet. Bjørn oplevede det som
«cuttet efter en tool-runde»: han fik en fil med et hul i midten, og der var
ikke noget at arbejde videre på.

Disse rendere ligger samlet her frem for spredt ud i tool-filerne, fordi de
løser det SAMME problem og skal kunne sammenlignes. Fælles disciplin:

* Kun det der bruges. `daemon_status` sender 67 dæmoner med hver sin lange
  beskrivelse — beskrivelserne alene sprænger loftet, og de er statiske. Man
  kigger på status for at vide hvad der KØRER.
* Én linje pr. ting. Så er det læsbart, og et loft skærer hele rækker af frem
  for at ramme midt i en værdi.
* Lange værdier klippes pr. celle, ikke pr. resultat. En enkelt kæmpe payload
  må ikke æde alle de andre rækker.
"""
from __future__ import annotations

from typing import Any

# Pr. celle/linje — nok til at se hvad der står, lille nok til at 200 rækker
# stadig er læsbare.
_CELL = 120
_PAYLOAD = 150


def _cell(value: object, limit: int = _CELL) -> str:
    s = "" if value is None else str(value)
    s = s.replace("\n", " ").replace("\r", " ").strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def render_daemons(daemons: list[dict[str, Any]]) -> str:
    """Én linje pr. dæmon: navn, om den kører, kadence, hvornår sidst.

    `description` udelades med vilje — 67 beskrivelser er det der sprænger
    loftet, og de ændrer sig aldrig. Tændte først: det er dem man spørger om.
    """
    try:
        rows = [d for d in (daemons or []) if isinstance(d, dict)]
    except Exception:
        return "[kunne ikke læse dæmon-liste]"
    if not rows:
        return "[ingen dæmoner]"

    def _line(d: dict[str, Any]) -> str:
        name = _cell(d.get("name"), 28)
        cad = d.get("effective_cadence_minutes")
        bits = [f"{name:<28}", "tændt  " if d.get("enabled") else "slukket"]
        if cad:
            bits.append(f"hver {cad}. min")
        hrs = d.get("hours_since_last_run")
        if isinstance(hrs, (int, float)):
            bits.append(f"sidst {hrs:.1f} t siden")
        elif d.get("last_run_at"):
            bits.append(f"sidst {_cell(d.get('last_run_at'), 20)}")
        else:
            bits.append("aldrig kørt")
        summary = _cell(d.get("last_result_summary"), 70)
        if summary:
            bits.append(f"· {summary}")
        return "  ".join(bits)

    on = [d for d in rows if d.get("enabled")]
    off = [d for d in rows if not d.get("enabled")]
    out = [f"{len(rows)} dæmoner — {len(on)} tændt, {len(off)} slukket", ""]
    out += [_line(d) for d in on]
    if off:
        out += ["", f"Slukket ({len(off)}): " + ", ".join(_cell(d.get("name"), 28) for d in off)]
    return "\n".join(out)


def render_events(events: list[dict[str, Any]]) -> str:
    """Én linje pr. hændelse: tid, art, og begyndelsen af payload.

    `payload` OG `payload_json` er det samme indhold to gange — kun den ene
    tages med. At sende begge fordoblede den dyreste del af resultatet.
    """
    try:
        rows = [e for e in (events or []) if isinstance(e, dict)]
    except Exception:
        return "[kunne ikke læse hændelser]"
    if not rows:
        return "[ingen hændelser]"
    out = [f"{len(rows)} hændelser", ""]
    for e in rows:
        ts = _cell(e.get("created_at"), 32)
        # Kun klokkeslæt når datoen er i dag-formatet — tidspunktet er det
        # man læser efter, datoen gentages på hver eneste linje.
        if "T" in ts:
            ts = ts.split("T", 1)[1][:8]
        kind = _cell(e.get("kind") or e.get("family"), 34)
        payload = _cell(e.get("payload") or e.get("payload_json"), _PAYLOAD)
        out.append(f"{ts:>9}  {kind:<34}  {payload}")
    return "\n".join(out)


def render_rows(columns: list[str], rows: list[dict[str, Any]], *, capped: bool = False) -> str:
    """Et resultatsæt som en justeret tabel.

    Kolonnebredden følger det bredeste FAKTISKE indhold, ikke en fast bredde:
    en tabel med korte værdier skal ikke fylde en skærm i mellemrum.
    """
    try:
        cols = [str(c) for c in (columns or [])]
        data = [r for r in (rows or []) if isinstance(r, dict)]
    except Exception:
        return "[kunne ikke læse resultatsæt]"
    if not cols:
        return "[ingen kolonner]"
    if not data:
        return f"0 rækker  ({', '.join(cols)})"

    cells = [[_cell(r.get(c)) for c in cols] for r in data]
    widths = [
        min(max(len(c), *(len(row[i]) for row in cells)), _CELL)
        for i, c in enumerate(cols)
    ]
    head = "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    sep = "  ".join("-" * widths[i] for i in range(len(cols)))
    body = ["  ".join(row[i].ljust(widths[i]) for i in range(len(cols))) for row in cells]
    note = f"{len(data)} rækker" + ("  [AFKORTET ved 200 — der er flere]" if capped else "")
    return "\n".join([note, "", head, sep, *body])
