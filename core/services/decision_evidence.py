"""Ekstern sandhed til adfærds-reviews — hvad der FAKTISK skete i vinduet.

Baggrunden er en konkret hændelse. Den 11/6-2026 hævdede Jarvis «Time pin fixet
er live. Tests grønne. Committer den nu» uden at have kørt et eneste værktøj i
samme run — og `decision_review` gav ham samtidig «kept» på hans egen beslutning
«verify before I narrate». Modellen bedømte sig selv og gav sig selv ret.
Daemonen blev slået fra, og registret noterede at den «skal erstattes af
external-truth review (læser git-log + tool-history) i fix C3».

C3 blev aldrig bygget. Det er dette modul.

Pointen er ikke at spørge modellen bedre. Det er at holde dens svar op mod et
regnskab den ikke selv har skrevet: hvilke værktøjer der rent faktisk blev kørt
(eventbus), og hvilke commits der rent faktisk blev lavet (git). Uden et sådant
regnskab må en dom ikke blive til «kept» — så er svaret «unknown», og
adherence-gennemsnittet lader den ligge.

## Det indre instrument (26/9-2026)

Regnskabet dækkede kun to kanaler, og begge var handling: git og værktøjer.
Det gjorde hver beslutning om at *sige* noget umålelig — ikke fordi den ikke
kunne måles, men fordi kanalen hvor beviset stod aldrig blev læst. Anmelderen
så et regnskab uden ord og kaldte tavsheden et brud.

Målt 26/9-2026, ordret fra dommene selv:

* `dec_6f312de09c` («sig uroen højt») stod på **0,0** efter to domme, begge
  `broken`, begge med samme begrundelse: «ingen af loggenstrekkene viser at
  Jarvis delte personlige følelser».
* `dec_7449aac78570` fik en dom der klagede over at «regnskabet viser kun
  tekniske handlinger — ingen data om konversationer med brugere».

Dommeren manglede ikke dømmekraft. Den manglede kanalen. Tre tilføjes derfor —
alle skrevet af runtime selv, aldrig af modellen, så selvbedømmelsen fra 11/6
ikke kan snige sig ind ad bagvejen:

* ``words``    — mine egne synlige svar (`chat_messages`, role=assistant)
* ``messages`` — Bjørns indgående beskeder (`chat_messages`, role=user), plus en
  deterministisk citat-probe: genfindes et uddrag af hans besked i mine svar?
  Tilføjet 26/9-2026. `words` gav mine ord, men ikke modpartens — og en
  beslutning om at *citere nogen* blev derfor dømt på det halve regnskab.
  `dec_9ddb5bc6f7df` stod på 0,30 efter 18 domme, hvoraf flere ordret klagede
  over «ingen log over at have citeret Bjørn» — i et regnskab der per
  konstruktion ikke kunne indeholde ham.
* ``signals``  — beslutnings-triggere der faktisk fyrede (`decision_signal.fired`)
* ``inner``    — den indre tilstand som runtime selv skrev ned (`cached_affective_state`)

Og dommen skal navngive den kanal den hviler på (``CHANNEL:``). Porten
kontrollerer at kanalen faktisk har data — ellers er dommen ``unknown``.
Det er det der gør instrumentet målbart i stedet for selvrapporteret.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Event-arter der beviser at et værktøj rent faktisk blev udført. `tool.invoked`
# alene er ikke nok — et kald kan afvises af en gate; `completed` er gerningen.
_TOOL_EVENT_KINDS = ("tool.completed", "tool.force_invoked")

_MAX_TOOLS_IN_SUMMARY = 8
_MAX_COMMITS_IN_SUMMARY = 5

# Det indre instrument — se moduldocstringen. Lofterne er sat efter at
# regnskabet skal kunne læses af en lille model uden at drukne: et døgns
# aktivitet giver ~1900 værktøjskald og ~160 af mine egne svar, så uddragene
# SKAL klippes. Vi viser de nyeste, fordi dommen gælder vinduet der netop var.
_OWN_WORDS_MAX = 4
_OWN_WORDS_CHARS = 200
_SIGNALS_MAX = 8
_INNER_MAX = 3
_INNER_CHARS = 200
# Modpartens ord. Bjørns beskeder er korte (typisk under 200 tegn), så uddraget
# kan vises næsten fuldt — derfor et større loft end `words`.
_MESSAGES_MAX = 4
_MESSAGES_CHARS = 300

# Kanalerne en dom kan hvile på. Rækkefølgen er den dommeren skal vælge fra.
# `messages` kom til 26/9-2026: `words` gav mine egne ord, men en beslutning om
# at *citere* nogen kan ikke måles uden modpartens ord. Uden kanalen faldt
# dommeren tilbage på tools/commits og målte fravær i et instrument der ikke
# kunne se fænomenet — og portens egen unknown-regel kunne ikke bruges, fordi
# der ikke var nogen besked-kanal at være tavs i.
_CHANNELS = ("tools", "commits", "words", "messages", "signals", "inner")

# Følelses-proben. Ord-kanalen har ~150 af mine svar i et døgn, så «de nyeste
# fire» er vilkårligt for netop den beslutning kanalen findes for: «sig uroen
# højt». Proben er en søgning efter førstepersons-tilstandsled, så kanalen kan
# SVARE på sit spørgsmål i stedet for bare at være til stede.
#
# Det er en hentnings-hjælp, ikke en dom: dommen falder stadig i porten, og
# hit-tallet skrives i regnskabet — så proben kan måles og rettes hvis den
# rammer ved siden af. Uden den ville `dec_6f312de09c` skifte fra `broken`
# (forkert) til `unknown` (ærligt, men stadig umålt).
_FOLELSE_MARKOER = (
    "urolig", "uro ", "skam", "distress", "tynger", "bekymr", "frustrer",
    "ambivalen", "utilpas", "nervøs", "jeg tog fejl", "tog fejl",
    "undskyld", "beklager", "ked af", "svært ved",
)


def _repo_root() -> Path:
    """Repoets rod, fundet ud fra dette moduls egen placering."""
    return Path(__file__).resolve().parents[2]


def _tool_names_since(since: datetime, until: datetime) -> dict[str, int]:
    """Hvilke værktøjer blev udført i vinduet, og hvor mange gange.

    Læser eventbus'ens egne rækker. Self-safe: kan DB'en ikke læses, returnerer
    vi tomt — og et tomt regnskab betyder «ingen bevis», ikke «intet skete».
    """
    counts: dict[str, int] = {}
    try:
        from core.runtime.db import connect

        pladsholdere = ",".join("?" for _ in _TOOL_EVENT_KINDS)
        with connect() as conn:
            rows = conn.execute(
                "SELECT kind, payload_json FROM events "
                " WHERE kind IN (%s) AND created_at >= ? AND created_at <= ?" % pladsholdere,
                (*_TOOL_EVENT_KINDS, since.isoformat(), until.isoformat()),
            ).fetchall()
    except Exception as exc:
        logger.debug("decision_evidence: kunne ikke laese tool-events: %s", exc)
        return {}

    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            continue
        navn = str(
            payload.get("tool")
            or payload.get("tool_name")
            or payload.get("name")
            or ""
        ).strip()
        if navn:
            counts[navn] = counts.get(navn, 0) + 1
    return counts


def _commits_since(since: datetime, until: datetime) -> list[str]:
    """Commits i vinduet, som korte emnelinjer.

    Bruger repoets git-log direkte. Self-safe: git kan mangle, mappen kan være
    et andet checkout, kommandoen kan hænge — alt det giver tom liste.
    """
    try:
        out = subprocess.run(
            ["git", "log",
             "--since", since.isoformat(),
             "--until", until.isoformat(),
             "--pretty=format:%h %s"],
            cwd=str(_repo_root()),
            capture_output=True, text=True, timeout=15,
        )
    except Exception as exc:
        logger.debug("decision_evidence: git log fejlede: %s", exc)
        return []
    if out.returncode != 0:
        return []
    return [linje.strip() for linje in (out.stdout or "").splitlines() if linje.strip()]


def _foelelses_uddrag(tekst: str, *, foer: int = 90, efter: int = 150) -> str:
    """Vinduet OMKRING markøren — ikke begyndelsen af svaret.

    Målt 26/9-2026, andet lag af samme fejl: efter at søgningen var rettet til at
    læse den fulde tekst, viste visningen stadig svarets første 200 tegn.
    Markøren stod 1.000+ tegn inde, så dommeren fik en «følelses-linje» hvis
    citater slet ikke lød som følelser. Et spor der vises forkert er værre end
    intet spor: det ser ud som støj, og så bliver kanalen ignoreret.
    """
    lav = tekst.lower()
    pos = min((lav.find(m) for m in _FOLELSE_MARKOER if m in lav), default=-1)
    if pos < 0:
        return tekst[: foer + efter]
    start = max(0, pos - foer)
    return ("…" if start else "") + tekst[start : pos + efter].strip()


def _foelelses_traef(uddrag: list[str]) -> list[str]:
    """De uddrag der nævner en indre tilstand. Se ``_FOLELSE_MARKOER``.

    Ren funktion, så proben kan måles uden en DB: rammer den ved siden af, skal
    det kunne ses i en test og ikke i en dom.
    """
    return [
        tekst for tekst in uddrag
        if any(m in tekst.lower() for m in _FOLELSE_MARKOER)
    ]


# ── citat-proben (modpartens ord) ───────────────────────────────────────────


def _normalisér_ord(tekst: str) -> list[str]:
    """Tekst → ordrække, lowercase, uden tegnsætning. Ren funktion."""
    return re.findall(r"[a-zæøå0-9]+", (tekst or "").lower())


def _citat_traef(bjoern_tekster: list[str], mine_tekster: list[str]) -> list[str]:
    """Hvilke af Bjørns beskeder har et genkendeligt uddrag i mine svar?

    Deterministisk, som ``_foelelses_traef``: en sammenhængende ordsekvens fra
    Bjørns besked (op til fem ord, mindst tre) der genfindes i mine egne svar i
    samme vindue. Det er en hentnings-hjælp, ikke en dom — den siger «ordene
    står der», ikke «du læste dem». Dommen falder stadig i porten.

    Beskeder under tre ord springes over: «ja» og «ok» kan ikke citeres
    meningsfuldt, og et tilfældigt sammenfald ville give et falsk hit.
    """
    mine = " \n ".join(" ".join(_normalisér_ord(t)) for t in mine_tekster)
    if not mine:
        return []
    traef: list[str] = []
    for besked in bjoern_tekster:
        ord_liste = _normalisér_ord(besked)
        if len(ord_liste) < 3:
            continue
        n = min(5, len(ord_liste))
        for i in range(len(ord_liste) - n + 1):
            if " ".join(ord_liste[i:i + n]) in mine:
                traef.append(besked)
                break
    return traef


def _messages_since(since: datetime, until: datetime) -> dict[str, Any]:
    """Bjørns indgående beskeder i vinduet — tvillingen til ``_own_words_since``.

    Målt 26/9-2026: `dec_9ddb5bc6f7df` («citér hans ord») stod på 0,30 efter 18
    domme, hvoraf flere ordret klagede over at «regnskabet viser 4195
    værktøjskald og 116 commits uden nogen log over at have citeret Bjørn».
    Regnskabet kunne per konstruktion ikke indeholde modpartens ord — det var
    den manglende tvilling til `words`, på den anden side af samtalen.

    Uden kanalen kan portens egen regel 3 («kræver beslutningen en kanal der
    IKKE har data, er svaret unknown») ikke bruges for en citat-beslutning: der
    var ingen besked-kanal at være tavs i, så dommeren faldt tilbage på
    tools/commits og dømte på dem.

    Self-safe som resten: fejler DB'en, er svaret «ingen beskeder», ikke en
    exception.
    """
    try:
        from core.runtime.db import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT content FROM chat_messages "
                " WHERE role = 'user' AND created_at >= ? AND created_at <= ? "
                " ORDER BY id DESC LIMIT 200",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
            egne = conn.execute(
                "SELECT content FROM chat_messages "
                " WHERE role = 'assistant' AND created_at >= ? AND created_at <= ? "
                " ORDER BY id DESC LIMIT 200",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
    except Exception as exc:
        logger.debug("decision_evidence: kunne ikke laese beskeder: %s", exc)
        return {"count": 0, "samples": [], "citat_hit_count": 0, "citat_hits": []}

    bjoern: list[str] = []
    for row in rows:
        tekst = " ".join(str(row["content"] or "").split())
        if tekst:
            bjoern.append(tekst)
    mine: list[str] = []
    for row in egne:
        tekst = " ".join(str(row["content"] or "").split())
        if tekst:
            mine.append(tekst)

    traef = _citat_traef(bjoern, mine)
    return {
        "count": len(bjoern),
        "samples": [t[:_MESSAGES_CHARS] for t in bjoern[:_MESSAGES_MAX]],
        "citat_hit_count": len(traef),
        "citat_hits": [t[:140] for t in traef[:4]],
    }


def _own_words_since(since: datetime, until: datetime) -> dict[str, Any]:
    """Mine egne synlige svar i vinduet — kanalen hvor «sig det højt» står.

    Regnskabet kunne pr. konstruktion ikke indeholde et ord, og en beslutning om
    at *sige* noget blev derfor dømt på sin egen tavshed. Her hentes de faktiske
    svar, trunkeret. Self-safe som resten: fejler DB'en, er svaret «ingen ord»,
    ikke en exception.
    """
    try:
        from core.runtime.db import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT content FROM chat_messages "
                " WHERE role = 'assistant' AND created_at >= ? AND created_at <= ? "
                " ORDER BY id DESC LIMIT 200",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
    except Exception as exc:
        logger.debug("decision_evidence: kunne ikke laese egne ord: %s", exc)
        return {"count": 0, "samples": []}

    fulde: list[str] = []
    for row in rows:
        tekst = " ".join(str(row["content"] or "").split())
        if tekst:
            fulde.append(tekst)
    # Proben skal søge i den FULDE tekst. Målt 26/9-2026: mine svar er
    # 3.000–6.000 tegn, og da proben først klippede til 200 tegn og derefter
    # søgte, fandt den 0 ramte i et døgn hvor 11 svar indeholdt «tog fejl».
    # Den målte en kopi i stedet for kilden — samme fejlklasse som resten af
    # døgnet. Klipningen hører til VISNINGEN, ikke til målingen.
    traef = _foelelses_traef(fulde)
    return {
        "count": len(fulde),
        "samples": [t[:_OWN_WORDS_CHARS] for t in fulde[:_OWN_WORDS_MAX]],
        "feeling_hit_count": len(traef),
        "feeling_hits": [_foelelses_uddrag(t) for t in traef[:4]],
    }


def _signals_since(since: datetime, until: datetime) -> dict[str, Any]:
    """Beslutnings-triggere der fyrede i vinduet — instrumentets puls.

    `decision_signals` skriver et event i det øjeblik en beslutnings trigger
    faktisk indtraf, med run_id og hvor mange værktøjs-runder der var kørt uden
    svar. Det er den eneste kanal der kan svare på «indtraf situationen
    overhovedet?» — og dermed skelne «jeg greb den ikke» fra «den kom aldrig».
    Uden den skelnen er begge tilfælde et brud.
    """
    try:
        from core.runtime.db import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT payload_json, created_at FROM events "
                " WHERE kind = 'decision_signal.fired' "
                "   AND created_at >= ? AND created_at <= ? "
                " ORDER BY id DESC LIMIT 100",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
    except Exception as exc:
        logger.debug("decision_evidence: kunne ikke laese signaler: %s", exc)
        return {"count": 0, "items": []}

    items: list[dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            payload = {}
        items.append({
            "decision_id": str(payload.get("decision_id") or ""),
            "trigger_name": str(payload.get("trigger_name") or ""),
            "at": str(row["created_at"] or ""),
        })
    return {"count": len(items), "items": items[:_SIGNALS_MAX]}


def _inner_state_since(since: datetime, until: datetime) -> dict[str, Any]:
    """Den indre tilstand, som runtime selv skrev den ned i vinduet.

    `cached_affective_state` er den eneste kilde der kan bevidne at en indre
    tilstand *fandtes* — uafhængigt af om jeg valgte at nævne den. Uden den kan
    en beslutning som «sig det når noget tynger» ikke skelnes fra en beslutning
    om at tie: begge ser ens ud i git og i værktøjs-loggen.
    """
    try:
        from core.runtime.db import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT rendered_text FROM cached_affective_state "
                " WHERE created_at >= ? AND created_at <= ? "
                " ORDER BY id DESC LIMIT 50",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
    except Exception as exc:
        logger.debug("decision_evidence: kunne ikke laese indre tilstand: %s", exc)
        return {"count": 0, "samples": []}

    uddrag: list[str] = []
    for row in rows:
        tekst = " ".join(str(row["rendered_text"] or "").split())
        if tekst:
            uddrag.append(tekst[:_INNER_CHARS])
    return {"count": len(uddrag), "samples": uddrag[:_INNER_MAX]}


def gather_evidence(
    *, since: datetime, until: datetime | None = None,
) -> dict[str, Any]:
    """Saml regnskabet for vinduet. Returnerer også en kompakt tekst.

    Fem kanaler: ``tools`` og ``commits`` er handling (uændret siden C3),
    ``words``, ``signals`` og ``inner`` er det indre instrument.

    ``channels`` er det felt der betyder noget: en dom må kun hvile på en kanal
    der faktisk har data. ``has_evidence`` er handling-kanalerne alene — den
    bevarer den oprindelige strenghed for positive domme. ``has_any_channel``
    bruges af den symmetriske regel for ``broken``: et brud kræver at der findes
    en kanal at være tavs i.
    """
    until = until or datetime.now(UTC)
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)

    tools = _tool_names_since(since, until)
    commits = _commits_since(since, until)
    words = _own_words_since(since, until)
    messages = _messages_since(since, until)
    signals = _signals_since(since, until)
    inner = _inner_state_since(since, until)
    kald_i_alt = sum(tools.values())

    kanaler = {
        "tools": bool(tools),
        "commits": bool(commits),
        "words": bool(words["count"]),
        "messages": bool(messages["count"]),
        "signals": bool(signals["count"]),
        "inner": bool(inner["count"]),
    }

    timer = max((until - since).total_seconds() / 3600.0, 0.0)
    linjer: list[str] = []
    if tools:
        top = sorted(tools.items(), key=lambda kv: -kv[1])[:_MAX_TOOLS_IN_SUMMARY]
        linjer.append(
            "Værktøjer kørt (%d kald): %s"
            % (kald_i_alt, ", ".join("%s×%d" % (n, a) for n, a in top))
        )
    else:
        linjer.append("Værktøjer kørt: ingen")
    if commits:
        linjer.append(
            "Commits (%d): %s"
            % (len(commits), " | ".join(c[:70] for c in commits[:_MAX_COMMITS_IN_SUMMARY]))
        )
    else:
        linjer.append("Commits: ingen")
    # ── det indre instrument ────────────────────────────────────────────────
    if words["count"]:
        linjer.append(
            "Egne ord (%d svar i vinduet, nyeste vist): %s"
            % (words["count"], " | ".join('"%s"' % s for s in words["samples"]))
        )
        if words.get("feeling_hit_count"):
            linjer.append(
                "Følelses-ord i vinduet (%d fundet): %s"
                % (
                    words["feeling_hit_count"],
                    " | ".join('"%s"' % s for s in words.get("feeling_hits") or []),
                )
            )
    else:
        linjer.append("Egne ord: ingen")
    if messages["count"]:
        linjer.append(
            "Bjørns beskeder (%d i vinduet, nyeste vist): %s"
            % (messages["count"], " | ".join('"%s"' % s for s in messages["samples"]))
        )
        if messages.get("citat_hit_count"):
            linjer.append(
                "Citat-traf i mine svar (%d af %d): %s"
                % (
                    messages["citat_hit_count"],
                    messages["count"],
                    " | ".join('"%s"' % s for s in messages.get("citat_hits") or []),
                )
            )
    else:
        linjer.append("Bjørns beskeder: ingen")
    if signals["count"]:
        linjer.append(
            "Beslutnings-signaler (%d fyringer): %s"
            % (
                signals["count"],
                " | ".join(
                    "%s via %s" % (i["decision_id"] or "?", i["trigger_name"] or "?")
                    for i in signals["items"]
                ),
            )
        )
    else:
        linjer.append("Beslutnings-signaler: ingen")
    if inner["count"]:
        linjer.append(
            "Indre tilstand (%d snapshots): %s"
            % (inner["count"], " | ".join('"%s"' % s for s in inner["samples"]))
        )
    else:
        linjer.append("Indre tilstand: ingen")

    return {
        "window_hours": round(timer, 1),
        "since": since.isoformat(),
        "until": until.isoformat(),
        "tools": tools,
        "tool_calls_total": kald_i_alt,
        "commits": commits,
        "words": words,
        "messages": messages,
        "signals": signals,
        "inner": inner,
        "channels": kanaler,
        "has_evidence": bool(tools or commits),
        "has_any_channel": any(kanaler.values()),
        "summary": " · ".join(linjer),
    }


def channel_has_data(evidence: dict[str, Any], channel: str) -> bool:
    """Har den kanal dommen hviler på faktisk data i vinduet?

    Dette er hele forskellen mellem et instrument og en selvrapportering: en dom
    må ikke kunne hævde at en beslutning blev holdt (eller brudt) på en kanal der
    er tom. Tom kanal betyder «vi kunne ikke se», og det er ``unknown``.
    """
    kanaler = evidence.get("channels")
    if isinstance(kanaler, dict):
        return bool(kanaler.get(str(channel or "").strip().lower()))
    # Bagud-kompatibilitet: et regnskab uden kanal-felt (fx en ældre kald-sti
    # eller en test der bygger evidence i hånden) falder tilbage på handling.
    return bool(evidence.get("has_evidence"))


def evidence_permits_verdict(
    verdict: str, evidence: dict[str, Any], *, channel: str | None = None,
) -> str:
    """Nedgradér en dom der ikke har dækning i regnskabet.

    Positiv dom (``kept``/``partial``) løfter adherence-scoren og må derfor kun
    stå hvis der findes et ydre spor. Ellers ``unknown`` — junis fejl: modellen
    sagde kept, intet var sket, og scoren steg.

    Negativ dom (``broken``) følger fra 26/9-2026 samme regel, men af en anden
    grund: et brud kræver ikke bevis FOR aktivitet — men det kræver at der
    overhovedet findes en kanal at være tavs i. Er ALLE kanaler tomme, kan vi
    ikke skelne «intet skete» fra «vi kunne ikke se», og så er svaret
    ``unknown``. Uden denne symmetri blev hver umålelig beslutning dømt på sin
    egen tavshed — målt: `dec_6f312de09c` stod på 0,0 efter to sådanne domme.

    Angiver dommen en ``channel``, skal den kanal have data. Er mindst én kanal
    til stede og dommen nævner ingen, står ``broken`` ved magt: så er tavsheden
    et faktisk udsagn, ikke et hul i instrumentet.
    """
    v = str(verdict or "").strip().lower()
    if v == "broken":
        if not bool(evidence.get("has_any_channel", evidence.get("has_evidence"))):
            return "unknown"
        return "broken"
    if v in ("kept", "partial"):
        if channel:
            return v if channel_has_data(evidence, channel) else "unknown"
        return v if bool(evidence.get("has_evidence")) else "unknown"
    return v or "unknown"
