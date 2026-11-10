"""Per-request cache-telemetri for den synlige DeepSeek-lane (2026-06-30).

Hvorfor: costs-bordet optager kun ÉN aggregeret række pr. tur (first-pass under
lane=primary, agentiske ture under lane=visible) — de individuelle agentiske
RUNDER er usynlige. Det gjorde det umuligt at verificere om prefix-cachen holder
RUNDE FOR RUNDE (fx tool_choice-fixet der skal holde [system,tools] byte-stabilt).

Denne modul skriver ÉN JSONL-linje pr. synligt DeepSeek-kald med:
  - run_id + round_index + autonomous → isolér ÉN brugers ÉN tur, runde for runde
  - prefix_sha + prefix_len → hash af det cachebare [system + tools]; SAMME hash
    over runder = prefixet er stabilt (cachen kan holde); skift = en breaker
  - cache_hit / cache_miss → DeepSeeks faktiske native tal (10× pris-forskel)

Aflæs: ~/.jarvis-v2/logs/cache_telemetry.jsonl. Self-safe — må ALDRIG kaste ind i
stream-stien.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#: Loft foer rotation. Samme tal som `scripts/primary_cache_warmer.LOG_MAKS_BYTES`
#: — de to filer skrives af samme slags kode og skal have samme levetid.
#:
#: MAALT 28/10-2026: `cache_telemetry.jsonl` var 115 MB og havde ALDRIG vaeret
#: roteret, mens soesterfilerne (`cache_rate.jsonl` 8,7 MB, `cache_warmer.jsonl`
#: 2,0 MB) holdt sig smaa fordi deres skrivere roterer. `prune_rotated_logs` i
#: `state_file_retention` sletter roterede filer — men den roterer ikke, saa en
#: fil uden en roterende skriver vokser til den fylder disken.
LOG_MAKS_BYTES = 8 * 1024 * 1024

#: Antal roterede generationer. Rettere: hvor mange døgn telemetrien kan rumme.
#:
#: MAALT 10/11-2026: skrivehastigheden er 4,19 MB/døgn, så ÉN generation på
#: 8 MB daekkede 1,9 døgn — og med den daværende `.1`-fil i alt 4,7 døgn. Et
#: «7-dages» tal fra telemetrien var derfor i praksis 44 timer, og det var
#: usynligt: overfladen rapporterede en procentsats uden at sige hvilket
#: tidsrum den daekkede.
#:
#: 4 x 8 MB = 32 MB ≈ 7,6 døgn ved den maalte hastighed. `prune_rotated_logs`
#: rydder foerst efter 14 dage, så generationerne overlever deres eget formaals
#: vindue. Loftet pr. FIL holdes bevidst paa 8 MB, så en enkelt laesning af den
#: nyeste fil forbliver billig — det er antallet af filer der giver historikken.
ROTATION_GENERATIONER = 4


def _rotér(sti: Path) -> None:
    """Rul filen ned gennem generationerne: `.3`→`.4`, `.2`→`.3`, `.1`→`.2`, fil→`.1`.

    Selv-sikker: telemetri maa aldrig vaelte stream-stien.
    """
    try:
        if not (sti.exists() and sti.stat().st_size > LOG_MAKS_BYTES):
            return
        # Aeldste foerst, ellers overskriver vi den naste generation med dens
        # egen forgænger. `.4` falder bort uden at blive flyttet: der er intet
        # `.5` at skubbe til, og det er praecis meningen med et loft.
        for n in range(ROTATION_GENERATIONER - 1, 0, -1):
            aeldre = sti.with_suffix(sti.suffix + f".{n}")
            nyere = sti.with_suffix(sti.suffix + f".{n + 1}")
            if aeldre.exists():
                aeldre.replace(nyere)
        sti.replace(sti.with_suffix(sti.suffix + ".1"))
    except Exception:  # rotation må aldrig vælte stream-stien — telemetri er ikke kritisk
        pass


def _generationer(sti: Path) -> list[Path]:
    """Alle telemetri-filer, aeldste generation foerst."""
    filer = [sti.with_suffix(sti.suffix + f".{n}")
             for n in range(ROTATION_GENERATIONER, 0, -1)]
    return [f for f in filer if f.exists()] + ([sti] if sti.exists() else [])


def telemetri_spaend(*, sti: Path | None = None) -> dict[str, Any]:
    """Det tidsrum telemetrien FAKTISK daekker — paa tvaers af alle generationer.

    Findes fordi fravaeret af dette svar kostede en forkert konklusion
    (10/11-2026): en procentsats blev laest som et 7-doegns-tal, mens filen
    daekkede 44 timer. Et tal uden sit tidsrum er ikke et maal.

    Laeser kun hver fils foerste og sidste `timestamp` — ikke hele filen.
    Returnerer `daekker_7_doegn=False` naar historikken ikke raekker, saa
    kalderen kan se det frem for at gætte.
    """
    home = Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))
    sti = sti or (home / "logs" / "cache_telemetry.jsonl")
    foerste = sidste = ""
    filer: list[dict[str, Any]] = []
    for f in _generationer(sti):
        try:
            storrelse = f.stat().st_size
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                t0 = ""
                for ln in fh:
                    if '"timestamp"' in ln:
                        try:
                            t0 = str(json.loads(ln).get("timestamp") or "")
                        except ValueError:  # afkortet/korrupt linje — proev den naeste
                            continue
                        if t0:
                            break
            # Sidste linje: laes halen, ikke hele filen.
            t1 = ""
            with f.open("rb") as fh:
                fh.seek(max(0, storrelse - 8192))
                hale = fh.read().decode("utf-8", "replace").splitlines()
            for ln in reversed(hale):
                if '"timestamp"' in ln:
                    try:
                        t1 = str(json.loads(ln).get("timestamp") or "")
                    except ValueError:  # afkortet/korrupt linje — proev den forrige
                        continue
                    if t1:
                        break
            if t0 and not foerste:
                foerste = t0
            if t1:
                sidste = t1
            filer.append({"navn": f.name, "bytes": storrelse, "fra": t0, "til": t1})
        except OSError:  # filen kan ikke laeses (rettigheder, forsvundet) — naeste generation
            continue
    timer: float | None = None
    if foerste and sidste:
        try:
            d0 = datetime.fromisoformat(foerste.replace("Z", "+00:00"))
            d1 = datetime.fromisoformat(sidste.replace("Z", "+00:00"))
            timer = round((d1 - d0).total_seconds() / 3600.0, 1)
        except ValueError:
            timer = None
    return {
        "filer": filer,
        "generationer": len(filer),
        "fra": foerste, "til": sidste,
        "timer": timer,
        "doegn": round(timer / 24.0, 1) if timer is not None else None,
        "daekker_7_doegn": bool(timer is not None and timer >= 24 * 7),
        "log_maks_bytes": LOG_MAKS_BYTES,
        "rotation_generationer": ROTATION_GENERATIONER,
    }


def prefix_signature(system_content: str, tools: Any) -> tuple[str, int]:
    """Beregn (sha-prefix, længde) for det cachebare [system + tools].

    Det er PRÆCIS den del DeepSeek-templaten lægger forrest (system så tools);
    ændrer ÉN byte sig her, brækker prefix-cachen fra det punkt. Deterministisk
    serialisering (sort_keys) så identisk indhold giver identisk hash."""
    try:
        sys_part = str(system_content or "")
        tools_part = json.dumps(tools or [], sort_keys=True, ensure_ascii=False)
        blob = sys_part + "\n--tools--\n" + tools_part
        sha = hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()[:16]
        return sha, len(blob)
    except Exception:
        return "", 0


#: Hvor mange beskeder vi signerer pr. linje. En lang agentisk tur kan have
# hundredvis; ved 600 er vi paa ~8 KB ekstra pr. event, og `msg_count` roeber
# hvis loftet ramte, saa en afkortet liste aldrig laeses som en hel.
_MSG_MAX = 600

#: Kort nok til at vaere billigt, langt nok til at en positionsvis
# sammenligning ikke kolliderer (1 ud af 16 mio. pr. plads).
_MSG_SHA_LEN = 6


def message_signatures(messages: list[dict[str, Any]]) -> tuple[list[str], list[int], int]:
    """Ét fingeraftryk og én laengde pr. besked, i den raekkefoelge de sendes.

    ## Hvorfor beskeder og ikke bare system+hale

    Praefiks-cachen matcher paa hele besked-arrayet. Da hittet faldt fra
    148.352 til 67.840 i runde 12 af ét run (28/9-2026), laa bruddet **dybt
    inde i samtalen** — system_sha og tools_sha var uaendrede, saa de
    eksisterende felter kunne ikke pege paa noget. Med ét aftryk pr. besked er
    braeddet bare den foerste plads hvor to runder er uenige, og summen af
    laengderne foer den plads er omtrent hvor mange tegn cachen naaede.

    Hele beskeden serialiseres, ikke kun `content`: en aendring i `tool_calls`
    eller `tool_call_id` braekker cachen praecis lige saa haardt, og ville
    vaere usynlig hvis vi kun saa paa teksten.

    Kun aftryk og tal — aldrig indhold. Det er telemetri, ikke en kopi af
    samtalen.
    """
    shas: list[str] = []
    lens: list[int] = []
    if not isinstance(messages, (list, tuple)):
        return [], [], 0
    for i_alt, message in enumerate(messages, start=1):
        if len(shas) >= _MSG_MAX:
            continue
        try:
            blob = json.dumps(message, sort_keys=True, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            # Et userialiserbart felt maa ikke koste os hele linjen. `str()`
            # er stabilt nok til at opdage en aendring, og alternativet — at
            # tabe maalingen — er praecis det vi forsoeger at raade bod paa.
            blob = str(message)
        shas.append(hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()[:_MSG_SHA_LEN])
        lens.append(len(blob))
    return shas, lens, len(messages)


#: Værktøjsnavne bag deres `tools_sha`, pr. proces.
#:
#: `component_signatures` kender ikke lanen; `record_visible_cache` gør. Navnene
#: lægges derfor her, hvor de kan slås op på den hash der følger videre i
#: telemetri-linjen — så skift-detektionen kan ligge hvor lanen er kendt.
#:
#: Hvorfor overhovedet (målt 30/9-2026): `tools_sha` skiftede 193 gange på én
#: dag, og i ALLE 193 tilfælde ændrede `tools_len` sig — altså SÆTTET, aldrig
#: en enkelt definitions indhold. De 15 skift i `visible`-lanen bar 1.028.484
#: miss-tokens (14,3 % af lanens samlede miss) fra 1,3 % af linjerne, med 40×
#: højere median-miss (62.672 mod 1.196). Vi kunne se AT det skiftede — ikke
#: HVAD. Det er hele grunden til at dette findes.
#:
#: VærktøjsNAVNE er metadata, ikke samtale. Derfor kun ved skift, aldrig pr.
#: linje: 1.200 linjer/dag ville ellers blive ~3 MB/dag for et svar vi kun
#: skal bruge ~15 gange.
_TOOL_NAMES_BY_SHA: dict[str, list[str]] = {}

#: Sidste sete navneliste PR. LANE. Nødvendigt: `visible` og `visible-call`
#: kalder begge hertil i samme proces med vidt forskellige sæt (51-82 KB mod
#: 29 KB), så de skifter på skift. Uden lane-nøglen ville hvert sådant flip
#: skrive en linje — ~193 støjlinjer for 15 ægte hændelser.
_LAST_TOOL_NAMES: dict[str, list[str]] = {}


def _tool_name(tool: Any) -> str:
    """Navnet ud af en OpenAI-formet tool-definition — tolerant over for formen."""
    if not isinstance(tool, dict):
        return str(tool)[:40]
    fn = tool.get("function")
    if isinstance(fn, dict) and fn.get("name"):
        return str(fn["name"])
    return str(tool.get("name") or tool.get("type") or "?")


def _remember_tool_names(tools_sha: str, tools: Any) -> None:
    """Gem navnene bag deres hash, saa `record_visible_cache` kan slaa dem op."""
    try:
        if not tools_sha:
            return
        names = [_tool_name(t) for t in tools] if isinstance(tools, (list, tuple)) else []
        _TOOL_NAMES_BY_SHA[tools_sha] = names
        if len(_TOOL_NAMES_BY_SHA) > 64:  # bundet: en proces lever i uger
            for gammel in list(_TOOL_NAMES_BY_SHA)[:-64]:
                _TOOL_NAMES_BY_SHA.pop(gammel, None)
    except Exception:  # self-safe: en navne-stash maa ikke kaste ind i stream-stien
        pass


def _note_tools_churn(lane: str, tools_sha: str) -> None:
    """Skriv ÉN linje naar værktøjssættet ændrer sig: hvad kom, hvad gik.

    Self-safe — maa aldrig kaste ind i stream-stien. Foerste kald pr. lane
    skriver IKKE (der er intet at sammenligne med); det saetter kun baseline.
    """
    try:
        names = _TOOL_NAMES_BY_SHA.get(tools_sha)
        if names is None:
            return
        noegle = str(lane or "-")
        foer = _LAST_TOOL_NAMES.get(noegle)
        _LAST_TOOL_NAMES[noegle] = names
        if foer is None or foer == names:
            return
        import os
        from pathlib import Path
        home = Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))
        log_dir = home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        foer_s, nu_s = set(foer), set(names)
        line = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "lane": noegle,
            "tools_sha": tools_sha,
            "tools_n_foer": len(foer), "tools_n_nu": len(names),
            "tilfoejet": sorted(nu_s - foer_s),
            "fjernet": sorted(foer_s - nu_s),
            # Rækkefølgen er en del af hashen: et rent ombyt flytter `tools_sha`
            # uden at noget kom eller gik. Uden dette felt ville et saadant
            # skift se ud som «ingen ændring» og blive laest som en fejl i
            # maalingen i stedet for som svaret.
            "kun_raekkefoelge": (nu_s == foer_s) and (names != foer),
            "names": names,
        }
        with (log_dir / "tools_churn.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:  # self-safe: churn-loggen maa ikke kaste ind i stream-stien
        pass


def component_signatures(messages: list[dict[str, Any]], tools: Any) -> dict[str, str | int | list[str]]:
    """Fingerprint prompt regions separately, without recording their contents.

    The first system message is the stable prefix. A system message after the
    conversation begins is the live tail; its expected changes must not be
    mistaken for a break in the stable prefix.
    """
    system = ""
    tail = ""
    seen_conversation = False
    for message in messages:
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        if role == "system" and not seen_conversation and not system:
            system = content
        elif role == "system" and seen_conversation:
            tail = content
        elif role != "system":
            seen_conversation = True
    tools_text = json.dumps(tools or [], sort_keys=True, ensure_ascii=False)
    _t_sha = hashlib.sha256(tools_text.encode("utf-8", "replace")).hexdigest()[:16] if tools_text else ""
    _remember_tool_names(_t_sha, tools)

    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:16] if value else ""

    msg_shas, msg_lens, msg_count = message_signatures(messages)
    return {
        "system_sha": digest(system), "system_len": len(system),
        "system_chunks": [digest(system[i:i + 1024]) for i in range(0, len(system), 1024)],
        "tools_sha": _t_sha, "tools_len": len(tools_text),
        "tools_n": len(tools) if isinstance(tools, (list, tuple)) else 0,
        "tail_sha": digest(tail), "tail_len": len(tail),
        "msg_shas": msg_shas, "msg_lens": msg_lens, "msg_count": msg_count,
    }


def record_visible_cache(
    *,
    run_id: str = "",
    round_index: int = -1,
    autonomous: bool = False,
    lane: str = "",
    provider: str = "",
    model: str = "",
    prefix_sha: str = "",
    prefix_len: int = 0,
    cache_hit: int = 0,
    cache_miss: int = 0,
    session_id: str = "",
    system_sha: str = "",
    tools_sha: str = "",
    tail_sha: str = "",
    system_len: int = 0,
    tools_len: int = 0,
    tools_n: int = 0,
    tail_len: int = 0,
    system_chunks: list[str] | None = None,
    msg_shas: list[str] | None = None,
    msg_lens: list[int] | None = None,
    msg_count: int = 0,
) -> None:
    """Append én telemetri-linje. Self-safe (sluger alt)."""
    try:
        home = Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))
        log_dir = home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / "cache_telemetry.jsonl"
        _rotér(path)
        _in = int(cache_hit) + int(cache_miss)
        line = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "session_id": session_id,
            "round": round_index,
            "auto": bool(autonomous),
            "lane": lane,
            "provider": provider,
            "model": model,
            "prefix_sha": prefix_sha,
            "prefix_len": prefix_len,
            "system_sha": system_sha,
            "tools_sha": tools_sha,
            "tail_sha": tail_sha,
            "system_len": int(system_len),
            "system_chunks": list(system_chunks or []),
            "tools_len": int(tools_len),
            "tools_n": int(tools_n),
            "tail_len": int(tail_len),
            "msg_shas": list(msg_shas or []),
            "msg_lens": [int(n) for n in (msg_lens or [])],
            "msg_count": int(msg_count),
            "hit": int(cache_hit),
            "miss": int(cache_miss),
            "pct": round(100.0 * int(cache_hit) / _in, 1) if _in else 0.0,
        }
        # Værktøjssættet er den volatile del af det cachede præfiks — se noten
        # ved `_TOOL_NAMES_BY_SHA`. Kaldes her, hvor `lane` er kendt.
        _note_tools_churn(lane, tools_sha)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
        # Cache→Central (spec §3.2/§3.3): fodr Centralen med prefix-cache-helbred, så
        # central_watch kan flagge når caching brækker (kold hit-rate = ~10x omkostning).
        # Kun ved reel cache-aktivitet (_in>0) — første/tomme kald er ikke et signal.
        if _in > 0:
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish("cache.telemetry", line)
            except Exception:
                pass
            try:
                from core.services import central_timeseries
                from core.services.central_core import central
                central().observe({
                    "cluster": "cost", "nerve": "prefix_cache", "kind": "telemetry",
                    "run_id": run_id, "pct": line["pct"], "prefix_sha": prefix_sha,
                    "lane": lane, "provider": provider,
                    "hit": int(cache_hit), "miss": int(cache_miss),
                })
                central_timeseries.record("cost", "prefix_cache", value=float(line["pct"]),
                                          meta={"prefix_sha": prefix_sha, "lane": lane})
            except Exception:
                pass
    except Exception:
        pass


def build_cache_telemetry_surface(*, tail_bytes: int = 2 * 1024 * 1024) -> dict[str, Any]:
    """Mission Control-surface: holder prefix-cachen, og hvornaar brød den sidst?

    READ-ONLY: laeser kun de seneste `tail_bytes` af `cache_telemetry.jsonl`
    (filen kan fylde 8 MB). Hit-raten er vaegtet efter tokens (sum hit / sum
    hit+miss), ikke et gennemsnit af procenter.
    """
    home = Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))
    path = home / "logs" / "cache_telemetry.jsonl"
    base = {"mode": "cache-telemetry", "path": str(path)}
    if not path.exists():
        return {**base, "active": False, "reason": "cache_telemetry.jsonl findes ikke",
                "signals": {}, "summary": "ingen cache-telemetri skrevet"}
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > tail_bytes:
                fh.seek(size - tail_bytes)
                fh.readline()  # første linje i halen er afskaaret
            raw = fh.read().decode("utf-8", "replace")
    except OSError as exc:  # filen findes men kan ikke laeses — meld aarsagen frem for et tomt svar
        return {**base, "active": False, "reason": f"{type(exc).__name__}: {exc}"[:300],
                "signals": {}, "summary": "cache-telemetri ulaeselig"}
    lines: list[dict[str, Any]] = []
    broken = 0
    for ln in raw.splitlines():
        try:
            row = json.loads(ln)
        except ValueError:  # afkortet/korrupt linje taelles, saa den ikke forsvinder tavst
            broken += 1
            continue
        if isinstance(row, dict):
            lines.append(row)
    if not lines:
        return {**base, "active": False, "reason": f"ingen laesbare linjer ({broken} korrupte)",
                "signals": {"unreadable_lines": broken}, "summary": "ingen brugbar cache-telemetri"}
    hit = sum(int(r.get("hit") or 0) for r in lines)
    miss = sum(int(r.get("miss") or 0) for r in lines)
    churn = home / "logs" / "tools_churn.jsonl"
    last = lines[-1]

    # Hvilket tidsrum daekker DE LINJER vi laeste? Uden dette kunne «hit 96,9 %»
    # laeses som et 7-doegns-tal, mens halen er ~11 timer (maalt 10/11-2026:
    # 2 MB ved 179 KB/time). Et tal uden sit tidsrum er ikke et maal.
    laest_fra = str(lines[0].get("timestamp") or "")
    laest_til = str(last.get("timestamp") or "")
    laest_timer: float | None = None
    if laest_fra and laest_til:
        try:
            _a = datetime.fromisoformat(laest_fra.replace("Z", "+00:00"))
            _b = datetime.fromisoformat(laest_til.replace("Z", "+00:00"))
            laest_timer = round((_b - _a).total_seconds() / 3600.0, 1)
        except ValueError:
            laest_timer = None
    spaend = telemetri_spaend(sti=path)

    return {
        **base, "active": True,
        "signals": {"calls_read": len(lines), "unreadable_lines": broken, "log_bytes": size,
                    "hit_tokens": hit, "miss_tokens": miss,
                    "hit_pct": round(100.0 * hit / (hit + miss), 1) if (hit + miss) else None,
                    # Tidsrummet for de linjer hit_pct bygger paa — og for hele
                    # historikken. `hit_pct` maa aldrig citeres uden `read_hours`.
                    "read_from": laest_fra, "read_to": laest_til,
                    "read_hours": laest_timer,
                    "history_from": spaend.get("fra"), "history_to": spaend.get("til"),
                    "history_days": spaend.get("doegn"),
                    "history_covers_7_days": spaend.get("daekker_7_doegn"),
                    "rotated_generations": spaend.get("generationer"),
                    "distinct_prefix_sha": len({r.get("prefix_sha") for r in lines if r.get("prefix_sha")}),
                    "distinct_tools_sha": len({r.get("tools_sha") for r in lines if r.get("tools_sha")}),
                    "last_timestamp": last.get("timestamp"), "last_pct": last.get("pct"),
                    "last_lane": last.get("lane"),
                    "rotated_file_present": path.with_suffix(path.suffix + ".1").exists(),
                    "tools_churn_log_present": churn.exists()},
        "summary": (f"{len(lines)} kald over {laest_timer if laest_timer is not None else '?'} timer; "
                    f"hit {round(100.0 * hit / (hit + miss), 1) if (hit + miss) else 'ukendt'}%; "
                    f"historik {spaend.get('doegn')} doegn "
                    f"({'daekker 7' if spaend.get('daekker_7_doegn') else 'daekker IKKE 7'}); "
                    f"seneste {last.get('timestamp')}"),
    }
