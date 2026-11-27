"""Read-only publication, liveness and tempo projections for SSE."""
from typing import Any
import json
import re
import logging

logger = logging.getLogger(__name__)

def _live_udgivne_blokke(tool_use_id: str, allerede_sendt: set[str]) -> list[dict[str, Any]]:
    """Alt turen har UDGIVET og endnu ikke sendt — klar til den levende stream.

    ## Hvorfor navnet ikke længere er «billedblokke» (7/10-2026)

    Funktionen hed `_live_billedblokke` og filtrerede hårdt:
    `if b.get("type") != "image": continue`. Den gjorde præcis hvad navnet
    sagde — men en widget er `text/html`, og `_bloktype` giver den typen
    `file`. Så fladen blev droppet her og nåede aldrig nogen klient; den
    dukkede først op når tråden blev genindlæst fra `content_json`.

    Samme hul ramte `video` og `publish_file`. Fælles for dem alle: de er
    udgivelser, ikke billeder, og strømmen skal sende dem alle.

    Noterne kommer fra `published_files` — dem værktøjet lagde fra sig under
    turen — og læses med `peek`, ikke `take`: den der persisterer svaret
    bagefter skal stadig kunne finde dem.

    ## Hvorfor der IKKE filtreres på `tool_use_id`

    Første udgave gjorde det, og den virkede i test og ikke i drift. Grunden
    stod i udsenderen: `visible_runs` har TO steder der sender
    `capability/tool_result`, og det ene (linje ~4706, den godkendte vej)
    sender kun `{"type", "tool", "status"}` — **uden `capability_id`**. Så
    faldt `tool_id` tilbage til selve værktøjsNAVNET, filteret ledte efter en
    note med `tool_use_id = "openrouter_image"`, og der var ingen. Testen
    gav eventet et `capability_id` og kunne derfor ikke se det.

    I stedet holdes der styr på hvad der ER sendt. Enhver endnu usendt
    billed-note går ud ved næste billedværktøjs-resultat. Det virker uanset om
    udsenderen har et id med, uanset om ét kald producerede flere billeder
    (`n > 1`), og uanset hvor mange billedkald turen indeholder.

    En LIVE-blok bærer `src` (en data-URL) så klienten kan tegne den med det
    samme. Er billedet for stort til en data-URL, sendes blokken alligevel med
    sin `attachment_id`: den er allerede registreret, så
    `/attachments/image/{id}` virker med det samme, og klienten henter den
    med token. Bedre et billede der kommer et øjeblik senere end intet.
    """
    if not tool_use_id:
        return []
    from core.services.published_files import as_blocks, peek_efter_tool_use
    poster = peek_efter_tool_use(tool_use_id)
    blokke = []
    for b in as_blocks(poster):
        # 7/10-2026: send ALT turen udgav, ikke kun billeder. En widget er
        # `text/html` → typen `file`, og den blev droppet netop her.
        noegle = str(b.get("attachment_id") or b.get("url") or b.get("filename") or "")
        if not noegle or noegle in allerede_sendt:
            continue
        allerede_sendt.add(noegle)
        blokke.append(b)
    if not blokke:
        return []
    from core.services.attachment_service import image_data_url
    for blok in blokke:
        # Kun billeder og videoer får en data-URL. En `file` er en REFERENCE:
        # at lægge et helt HTML-dokument ind i strømmen ville sende fladen som
        # data i stedet for at lade klienten hente den med sit token.
        if blok.get("type") not in ("image", "video"):
            continue
        aid = str(blok.get("attachment_id") or "")
        if not aid:
            continue
        try:
            url = image_data_url(aid)
        except Exception as exc:
            logger.debug("sse_v2: data-URL for %s fejlede: %s", aid, exc)
            url = None
        if url:
            blok["src"] = url
    return blokke


def _run_still_active(run_id: str) -> bool:
    """True hvis dette run stadig kører server-side. Fail-safe: antag AKTIVT ved fejl,
    så vi aldrig afslutter en levende stream for tidligt.

    ROD-FIX (Bjørn 4. aug): FØR tjekkede den KUN den globale active-visible-run-slot
    (_get_active_visible_run_state). Men ALLE runs er nu detached (server-autoritative),
    og detached-stien vedligeholder den slot UPÅLIDELIGT (detached_run.py:86-96) → den
    returnerede False for LEVENDE runs → idle-timeouten (20s uden legacy-event) brød
    _translation_loop → gen.aclose() rev det stadig-kørende run ned midt i tool-exec →
    CancelledError/vis_len=0 i ALLE sessioner på tværs af klienter. run_event_log er den
    PÅLIDELIGE autoritet (detached_run.py:144): is_open = registreret OG ikke done.
    Frame-friskhed er kun et UI-signal og må aldrig være dødsbevis for et blokerende
    provider/tool-kald. _MAX_IDLE_TICKS≈180s er sidste hæng-værn; rammes det, bogføres
    et recovery-udfald. Slot beholdes som fallback for legacy-runs."""
    try:
        from core.services import run_event_log as _rel
        if _rel.is_open(run_id):
            return True
    except Exception as exc:
        logger.warning("SSE liveness lookup unavailable; keep stream alive: %s", exc)
        return True
    try:
        from core.services.visible_runs import _get_active_visible_run_state
        st = _get_active_visible_run_state() or {}
        return bool(st.get("active")) and str(st.get("run_id") or "") == str(run_id or "")
    except Exception as exc:
        logger.warning("SSE liveness lookup unavailable; keep stream alive: %s", exc)
        return True


def _laes_tempo(run_id: str, output_tokens: int) -> dict[str, float | None]:
    """TTFT og tok/s for dette run. Tomt dict ved enhver fejl.

    Egen funktion fordi `MessageDelta` bygges to steder (normal afslutning og
    gendannelse), og en try/except kopieret begge steder ville vaere to
    definitioner af «hvad goer vi naar maalingen fejler».
    """
    try:
        from core.services import svar_tempo
        tempo = svar_tempo.afslut(run_id, output_tokens=output_tokens)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sse_v2: kunne ikke aflaese svar-tempoet: %s", exc)
        return {}
    # MÅLT 20/11-2026: tallet gik herfra og KUN i SSE-payloaden. Det blev
    # tegnet i composeren og forsvandt, så domænet «streaming og perceived
    # performance» ikke kunne måles over tid — det stod på 42 % som et rent
    # skøn gennem 1.027 vektorer. Nu gemmes det samme tal samme sted, så der
    # ikke opstår to definitioner af hvornår det aflæses.
    try:
        from core.runtime import db_tempo
        db_tempo.gem(
            run_id,
            ttft_ms=tempo.get("ttft_ms"),
            tok_per_sek=tempo.get("tok_per_sek"),
            output_tokens=output_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("sse_v2: kunne ikke gemme svar-tempoet: %s", exc)
    return tempo



_SSE_BLOCK_RE = re.compile(r"event:\s*(?P<event>[^\n]+)\n" r"data:\s*(?P<data>[^\n]+)\n\n")

def _parse_legacy_sse(chunk: str) -> tuple[str, dict] | None:
    """Parse en legacy SSE event-blok til (event_name, payload_dict).

    Returnerer None hvis chunk ikke er en fuldstændig event-blok eller
    payload ikke er valid JSON.
    """
    m = _SSE_BLOCK_RE.search(chunk)
    if not m:
        return None
    event_name = m.group("event").strip()
    data_str = m.group("data")
    try:
        payload = json.loads(data_str)
    except (ValueError, TypeError) as exc:
        logger.debug("Ignoring malformed legacy SSE JSON: %s", exc)
        return None
    return event_name, payload


