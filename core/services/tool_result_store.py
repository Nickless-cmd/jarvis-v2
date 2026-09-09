from __future__ import annotations

import json
import logging
import os
import hashlib
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.runtime.config import TOOL_RESULTS_DIR

TOOL_RESULT_REFERENCE_RE = re.compile(r"^\[tool_result:(?P<result_id>[A-Za-z0-9_-]+)\]")
_DEFAULT_SUMMARY_LENGTH = 500
# Storen får siden 5/9-2026 hele tool-resultatet (samtalen får det klippede), så
# `read_tool_result` kan holde sit eget løfte om "the full output". Loftet er
# rundhåndet men ikke uendeligt: én fil må ikke kunne fylde disken. Ved
# overskridelse bevares hoved+hale, og noten siger det ærligt.
_MAX_STORED_CHARS = 2_000_000


logger = logging.getLogger(__name__)


def summarize_result(content: str, max_length: int = _DEFAULT_SUMMARY_LENGTH) -> str:
    normalized = " ".join(str(content or "").split()).strip()
    if len(normalized) <= max_length:
        return normalized or "[empty tool result]"
    return normalized[: max_length - 1].rstrip() + "…"


def save_tool_result(
    tool_name: str,
    arguments: dict[str, object] | None,
    result_content: str,
    *,
    created_at: str | None = None,
) -> str:
    _sikr_privat_rod()
    result_id = f"tool-result-{uuid4().hex}"
    timestamp = created_at or datetime.now(UTC).isoformat()
    raa = str(result_content or "")
    stored = raa
    klippet = len(raa) > _MAX_STORED_CHARS
    if klippet:
        from core.services.text_clip import clip_head_tail
        stored = clip_head_tail(stored, limit=_MAX_STORED_CHARS)
    # EJERSKAB (Fase 3, K11). Maalt 9/9-2026: 0 af 30.640 laesbare poster havde
    # en ejer — men 22.207 havde `_runtime_user_id` med i argumenterne. Oplysningen
    # der skal til for at autorisere en hentning, LAA der allerede; den laa bare
    # i praecis det felt der ikke burde gemmes.
    raa_args = dict(arguments or {})
    ejer = str(raa_args.get("_runtime_user_id") or "").strip()
    sess = str(raa_args.get("_runtime_session_id") or "").strip()

    payload = {
        "result_id": result_id,
        "tool_name": str(tool_name or "").strip(),
        "owner_user_id": ejer,
        "session_id": sess,
        "arguments": _redigeret(raa_args),
        "result": stored,
        # Fuldstændighed er nu et FELT, ikke kun en note inde i teksten.
        # `clip_head_tail` splejser «… [N tegn udeladt …] …» ind, så et menneske
        # kan se det — men en programmatisk læser skulle parse dansk prosa for at
        # vide om den holdt hele outputtet. Det er præcis den kontrakt
        # DeepSeek-harness-spec'ens Gap J beder om: fuldstændighed som en
        # maskinlæsbar kendsgerning, ikke en antagelse.
        "complete": not klippet,
        "original_chars": len(raa),
        "stored_chars": len(stored),
        "created_at": timestamp,
        "summary": _redact(summarize_result(result_content)),
        # Digest over det GEMTE indhold, ikke over originalen: handlen skal
        # kunne verificere det den faktisk leverer. Et digest over noget der
        # blev klippet væk, ville bevise en ting og udlevere en anden.
        "digest": _digest(stored),
    }
    target = _result_path(result_id)
    tmp_target = target.parent / f"{target.stem}.{uuid4().hex}.tmp"
    # Ejer-only OG eksklusiv: filen må ikke kunne findes af andre, og en
    # eksisterende fil må ikke overskrives i tavshed.
    fd = os.open(tmp_target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    except Exception:
        tmp_target.unlink(missing_ok=True)
        raise
    tmp_target.replace(target)
    return result_id


def get_tool_result(result_id: str, *,
                    user_id: str | None = None) -> dict[str, object] | None:
    """Hent en gemt handle.

    `user_id` er den der SPOERGER. Er den sat, og posten har en anden ejer,
    naegtes hentningen (Fase 3, K11: «authorized retrieval»).

    Legacy uden ejer slipper igennem med vilje: 30.640 poster maalt 9/9-2026
    havde ingen ejer, og at afvise dem ville goere hele arkivet ulaeseligt for
    at lukke et hul der ikke findes i dem — deres beskyttelse er den private
    rod. Nye poster faar en ejer og bliver derfor faktisk tjekket.
    """
    normalized = str(result_id or "").strip()
    if not normalized:
        return None
    try:
        path = _result_path(normalized)
    except UnsafeResultId as e:
        # Ikke tavst: et forsøg på at læse uden for storen er et signal, ikke
        # et uheld. Modellen skriver selv denne streng.
        logger.warning("tool_result_store: afviste hentning — %s", e)
        return None
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    # Poster gemt FØR fuldstændigheds-felterne fandtes har dem ikke. Et manglende
    # felt må ikke læses som «ufuldstændig» — vi ved det ikke, og at gætte ville
    # gøre gammelt, komplet output mistænkeligt. `None` siger «ukendt».
    ejer = str(data.get("owner_user_id") or "").strip()
    spoerger = str(user_id or "").strip()
    if ejer and spoerger and ejer != spoerger:
        # Ikke tavst: at en handle fra en anden brugers session bliver slaaet
        # op, er et signal — ikke et uheld.
        logger.warning("tool_result_store: naegtede hentning af %s — ejer=%r "
                       "spoerger=%r", normalized, ejer, spoerger)
        return None

    data.setdefault("complete", None)
    data.setdefault("original_chars", None)
    # HASH-TJEKKET HANDLE (Fase 3, K8). En handle der kun slås OP, beviser
    # ingenting om det den leverer. Her verificeres indholdet mod digesten.
    #
    # Poster fra før digesten fandtes har den ikke — og et manglende digest må
    # ikke læses som «forfalsket». `verified: None` siger «ukendt», præcis som
    # `complete: None` gør for fuldstændigheden.
    gemt = data.get("digest")
    if isinstance(gemt, str) and gemt:
        faktisk = _digest(str(data.get("result") or ""))
        data["verified"] = (faktisk == gemt)
        if not data["verified"]:
            logger.warning("tool_result_store: digest passer IKKE for %s — "
                           "indholdet er ændret siden det blev gemt", normalized)
    else:
        data.setdefault("verified", None)
    return data


def cleanup_old_results(max_age_days: int = 7) -> int:
    _sikr_privat_rod()
    cutoff = datetime.now(UTC) - timedelta(days=max(max_age_days, 0))
    removed = 0
    for path in TOOL_RESULTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        created_at = _parse_dt(str((data or {}).get("created_at") or ""))
        if created_at is None or created_at > cutoff:
            continue
        # LINK-SIKKER OPRYDNING (K11). Et symlink i storen ville ellers lade
        # oprydningen slette noget UDENFOR den — en sletning man ikke bad om,
        # udført af en rutine der kører af sig selv.
        try:
            if path.is_symlink() or path.resolve().parent != TOOL_RESULTS_DIR.resolve():
                logger.warning("tool_result_store: springer %s over — peger ud "
                               "af storen", path.name)
                continue
        except Exception:
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def build_tool_result_reference(result_id: str, *, tool_name: str, summary: str) -> str:
    normalized_tool = str(tool_name or "").strip() or "tool"
    normalized_summary = summarize_result(summary)
    return "\n".join(
        [
            f"[tool_result:{result_id}]",
            f"[{normalized_tool}]: {normalized_summary}",
            f'Use read_tool_result with result_id="{result_id}" to inspect the full output.',
        ]
    )


def parse_tool_result_reference(content: str) -> dict[str, str] | None:
    raw = str(content or "").strip()
    match = TOOL_RESULT_REFERENCE_RE.match(raw)
    if not match:
        return None
    result_id = str(match.group("result_id") or "").strip()
    if not result_id:
        return None
    lines = raw.splitlines()
    summary_line = lines[1].strip() if len(lines) > 1 else ""
    # tool_name is derivable from the immutable reference string itself:
    # build_tool_result_reference emits line 2 as "[{tool}]: {summary}".
    tool_match = re.match(r"^\[(?P<tool>[^\]]+)\]:\s?(?P<rest>.*)$", summary_line)
    tool_name = str(tool_match.group("tool")).strip() if tool_match else ""
    return {
        "result_id": result_id,
        "summary": summary_line,
        "tool_name": tool_name,
    }


def render_tool_result_for_prompt(
    content: str,
    *,
    expand: bool,
    max_chars: int = 1200,
    stub: bool = False,
) -> str:
    raw = str(content or "").strip()
    ref = parse_tool_result_reference(raw)

    if stub and ref:
        # COLD: pure function of the immutable reference string — NEVER disk.
        # (the disk-load fallback changes byte-form when the 7-day reaper deletes
        #  the JSON; the reference string in chat_messages.content is immutable.)
        rid = ref["result_id"]
        tool_name = str(ref.get("tool_name") or "tool").strip() or "tool"
        summary = " ".join(str(ref.get("summary") or "").split()).strip()
        # drop the "[tool]: " prefix that build_tool_result_reference prepends,
        # so the snippet doesn't duplicate the tool name.
        prefix = f"[{tool_name}]:"
        if summary.startswith(prefix):
            summary = summary[len(prefix):].strip()
        snippet = summary[:40].rstrip()
        if len(summary) > 40:
            snippet += "…"
        return (f"[tool_result:{rid} — {tool_name}: {snippet} "
                f"(read_tool_result)]")

    if not ref:
        normalized = " ".join(raw.split()).strip()
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 1].rstrip() + "…"

    data = get_tool_result(ref["result_id"])
    if not data:
        normalized = " ".join(raw.split()).strip()
        return normalized[: max_chars - 1].rstrip() + "…" if len(normalized) > max_chars else normalized

    tool_name = str(data.get("tool_name") or "tool").strip() or "tool"
    if expand:
        result_text = " ".join(str(data.get("result") or "").split()).strip()
        bounded = result_text[: max_chars - 1].rstrip() + "…" if len(result_text) > max_chars else result_text
        return _prefixed_tool_text(tool_name, bounded or "[empty tool result]")

    summary = str(data.get("summary") or ref.get("summary") or "").strip()
    normalized_summary = summarize_result(summary, max_length=max_chars)
    return _prefixed_tool_text(tool_name, normalized_summary)


def _redact(tekst: str) -> str:
    """Maskér hemmeligheder i METADATA. Kaster aldrig."""
    try:
        from core.services.secret_redaction import redact
        return redact(str(tekst or ""))
    except Exception:
        return str(tekst or "")


def _redigeret(args: dict) -> dict:
    """Argumenterne som de skal LIGGE PAA DISKEN.

    To ting fjernes. `_`-noeglerne er runtime-tilstand, ikke modellens kald —
    de hoerer ikke til i en post om hvad der blev gjort, og `_runtime_user_id`
    er netop loeftet ud til `owner_user_id` ovenfor.

    Og hemmelighederne maskeres. Maalt 9/9-2026: 84 gemte resultater matchede
    et token-moenster, og 62 af dem havde det i ARGUMENTERNE — typisk en
    `curl -H "Authorization: Bearer …"` paa en bash-kommandolinje.

    SELVE resultatet roeres ikke. Det er nyttelasten, ikke metadata, og Jarvis
    skal kunne laese tilbage praecis det vaerktoejet svarede; nyttelasten
    beskyttes af den private rod og 0600 i stedet.
    """
    ud = {}
    for k, v in (args or {}).items():
        if str(k).startswith("_"):
            continue
        ud[k] = _redact(v) if isinstance(v, str) else v
    return ud


def _digest(text: str) -> str:
    """sha256 over indholdet. Handlen kan dermed VERIFICERES, ikke kun slås op."""
    return "sha256:" + hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _sikr_privat_rod() -> None:
    """Roden er 0700 — kun ejeren. Værktøjsresultater indeholder alt hvad et
    værktøj så: filindhold, kommando-output, argumenter."""
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        if TOOL_RESULTS_DIR.stat().st_mode & 0o077:
            TOOL_RESULTS_DIR.chmod(0o700)
    except Exception:
        logger.warning("tool_result_store: kunne ikke stramme rettighederne paa %s",
                       TOOL_RESULTS_DIR, exc_info=True)


#: Et gyldigt result_id. Alt andet afvises FØR der bygges en sti.
_ID_MOENSTER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


class UnsafeResultId(ValueError):
    """`result_id` peger uden for storen — eller kunne gøre det."""


def _result_path(result_id: str) -> Path:
    """Stien til ét resultat. Afviser alt der kan pege ud af roden.

    MÅLT 9/9-2026: `TOOL_RESULTS_DIR / f"{result_id}.json"` uden validering var
    en ægte sti-traversering. `get_tool_result("../hemmelig")` læste en fil
    UDEN FOR roden — og `result_id` kommer fra MODELLENS eget værktøjskald
    (`read_tool_result`), altså fra en streng vi ikke kontrollerer.

    To lag, fordi ét ikke er nok:
      1. mønsteret — ingen skilletegn, ingen prikker, ingen `..`
      2. den opløste sti SKAL ligge under roden — også hvis roden selv går
         gennem et symlink, og også hvis mønsteret en dag bliver løsnet.
    """
    rid = str(result_id or "").strip()
    if not _ID_MOENSTER.match(rid):
        raise UnsafeResultId(f"ugyldigt result_id: {rid[:60]!r}")
    rod = TOOL_RESULTS_DIR.resolve()
    sti = (rod / f"{rid}.json").resolve()
    if sti.parent != rod:
        raise UnsafeResultId(f"result_id peger uden for storen: {rid[:60]!r}")
    return sti


def _prefixed_tool_text(tool_name: str, text: str) -> str:
    normalized = str(text or "").strip()
    prefix = f"[{tool_name}]:"
    if normalized.startswith(prefix):
        return normalized
    return f"{prefix} {normalized}".strip()


def _parse_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)




def repair_permissions() -> dict[str, int]:
    """Saet 0600 paa gamle handles der blev skrevet foer O_EXCL-stien fandtes.

    Maalt 9/9-2026: 30.495 af 30.650 filer laa som 0644 — laesbare for alle.
    Roden er 0700, saa de var i praksis daekket; men «i praksis daekket» holder
    kun saa laenge ingen aabner roden, og en backup der bevarer rettigheder
    baerer 0644 med sig ud.

    Springer symlinks over: en oprydning der foelger et link, aendrer noget
    andet end det den tror.
    """
    _sikr_privat_rod()
    ud = {"set": 0, "allerede": 0, "sprunget": 0, "fejl": 0}
    rod = TOOL_RESULTS_DIR.resolve()
    for sti in TOOL_RESULTS_DIR.glob("*.json"):
        try:
            if sti.is_symlink() or sti.resolve().parent != rod:
                ud["sprunget"] += 1
                continue
            if (sti.stat().st_mode & 0o777) == 0o600:
                ud["allerede"] += 1
                continue
            sti.chmod(0o600)
            ud["set"] += 1
        except Exception:
            ud["fejl"] += 1
    return ud
