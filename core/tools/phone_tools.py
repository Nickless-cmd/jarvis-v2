"""Telefon-vaerktoejer — Jarvis' organer paa Bjoerns telefon.

Samme form som ``operator_tools``: en tynd async-wrapper om
``bridge_registry.dispatch``, hvor SERVEREN annoncerer vaerktoejet og
KLIENTEN udfoerer det. Broen er den samme; det nye er at den siden 7/9-2026
kan holde flere klienter pr. bruger og vaelge dem paa ``capabilities``, saa
et ``phone_*``-kald finder telefonen uden at nogen skal huske hvor det bor.

**Telefonen er ikke en lille computer.** ``operator_bash`` og ``operator_glob``
giver ingen mening dér. De organer en telefon har, er nogle andre — kamera,
mikrofon, position, stemme, udklipsholder, deling — og det er dem her.

To ting adskiller dem fra operator-saettet, ud over navnene:

* **Telefonen er ikke altid forbundet.** En computer holder en aaben socket;
  en telefon sover. Fejler et kald med ``phone_not_connected``, er det ikke
  en fejl i broen — det er en telefon i lommen. Beskeden siger det, saa den
  ikke bliver fejlsoegt som noget andet.
* **Nogle organer kraever forgrunden.** Kameraet kan ikke tage et billede
  mens appen ligger i baggrunden. Position og lyd kan. Det staar paa hvert
  enkelt vaerktoej, saa valget kan traeffes foer kaldet i stedet for efter
  en timeout.

Owner-only, som operator-saettet: det er Bjoerns telefon, hans kamera og hans
position. Ejer-id udledes med samme helper, saa der ikke opstaar to sandheder
om hvem broen tilhoerer.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Telefonen er langsommere og mere ustabil end en desktop: radioen skal vaagne,
# kameraet skal fokusere, GPS'en skal faa fix. Defaulten er derfor hoejere end
# operator-saettets 30 s — men ikke saa hoej at en tur bliver haengende paa en
# telefon der ligger i en jakkelomme.
_DEFAULT_TIMEOUT_S = 45.0

# GPS-fix kan tage laenge naar telefonen har vaeret indendoers.
_LOCATION_TIMEOUT_S = 60.0


async def _phone_call(
    *,
    tool: str,
    args: dict[str, Any],
    user_id: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> Any:
    """Send et kald til telefonen. Kaster ``RuntimeError`` med en LAESELIG grund.

    Skelner mellem «telefonen er ikke forbundet» og «kaldet fejlede», fordi de
    to kraever helt forskellige reaktioner: den foerste er normal (telefonen
    sover), den anden er noget at undersoege.
    """
    import asyncio

    from core.services.jarvisx_bridge import bridge_registry

    # Sover telefonen, bankes der paa foerst. Push-vaekningen er tavs (ingen
    # title/preview → ingen notifikations-blok), saa Bjoern ser ingenting;
    # appen vaagner, forbinder, og kaldet gaar igennem. Uden det her ville
    # ethvert telefon-kald fejle med det samme naar skaermen var slukket —
    # altsaa naesten altid.
    #
    # Ventetiden koeres i en traad, fordi den poller synkront paa delt cache
    # og ellers ville blokere hele event-loopet i op til 20 sekunder.
    try:
        from core.services import phone_wake
        if not phone_wake.telefon_er_forbundet(user_id):
            await asyncio.to_thread(phone_wake.vaek_og_vent, user_id)
    except Exception:
        logger.debug("phone_tools: vaekning fejlede, proever alligevel", exc_info=True)

    result = await bridge_registry.dispatch(
        user_id=user_id, tool=tool, args=args, timeout_s=timeout_s,
    )

    # «bridge_replaced» betyder at en NY forbindelse fra samme klient tog over
    # mens kaldet var undervejs — typisk fordi Bjoern aabnede appen midt i det.
    # Selve telefonen er der stadig, saa ét gentagsforsoeg er det rigtige svar;
    # at give op ville sende en fejl tilbage for noget der lykkedes et sekund
    # senere. Kun ÉT forsoeg: sker det igen, er der noget andet galt end en
    # tilfaeldig overlapning.
    if str(result.get("error") or "").find("bridge_replaced") >= 0:
        logger.info("phone_tools: broen blev erstattet under %s — proever igen", tool)
        await asyncio.sleep(0.5)
        result = await bridge_registry.dispatch(
            user_id=user_id, tool=tool, args=args, timeout_s=timeout_s,
        )

    if result.get("status") != "ok":
        err = str(result.get("error") or "unknown")
        if "not_connected" in err or "no_bridge" in err:
            raise RuntimeError(
                "phone_not_connected: telefonen svarede ikke, heller ikke efter "
                "en vaekning. Den kan vaere slukket, uden net, eller have "
                "batterisparing paa appen. ADB-vejen (phone_adb_*) rammes ikke "
                "af det."
            )
        raise RuntimeError(f"{tool} failed: {err}")
    return result.get("result")


# ── Sanser ──────────────────────────────────────────────────────────────


async def phone_photo_async(
    *, user_id: str, kamera: str = "back", gem_sti: str | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Tag et billede. **Kraever at appen er i forgrunden** — kameraet kan ikke
    aabnes fra baggrunden paa Android."""
    r = await _phone_call(
        tool="phone_photo",
        args={"kamera": str(kamera or "back"), "gem_sti": gem_sti},
        user_id=user_id, timeout_s=timeout_s,
    )
    return dict(r or {})


async def phone_location_async(
    *, user_id: str, noejagtighed: str = "balanced",
    timeout_s: float = _LOCATION_TIMEOUT_S,
) -> dict[str, Any]:
    """Hvor telefonen er. Virker ogsaa i baggrunden."""
    r = await _phone_call(
        tool="phone_location",
        args={"noejagtighed": str(noejagtighed or "balanced")},
        user_id=user_id, timeout_s=timeout_s,
    )
    return dict(r or {})


async def phone_record_audio_async(
    *, user_id: str, sekunder: float | None = None, timeout_s: float | None = None,
) -> dict[str, Any]:
    """Optag lyd fra mikrofonen. Virker ogsaa i baggrunden.

    Timeout udledes af optagelsens laengde plus luft til opstart og overfoersel
    — en fast timeout ville skaere en lang optagelse over.
    """
    # ``None`` som sentinel, ikke falsy: ``sekunder or 5.0`` ville goere en
    # eksplicit 0 til 5 sekunder. Beder man om nul, mener man kortest muligt.
    sek = max(0.5, min(float(5.0 if sekunder is None else sekunder), 120.0))
    r = await _phone_call(
        tool="phone_record_audio", args={"sekunder": sek},
        user_id=user_id, timeout_s=timeout_s or (sek + 20.0),
    )
    return dict(r or {})


# ── Skaerm og stemme ────────────────────────────────────────────────────


async def phone_speak_async(
    *, user_id: str, tekst: str, sprog: str = "da-DK",
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Sig noget hoejt gennem telefonens hoejttaler."""
    r = await _phone_call(
        tool="phone_speak",
        args={"tekst": str(tekst or ""), "sprog": str(sprog or "da-DK")},
        user_id=user_id, timeout_s=timeout_s,
    )
    return dict(r or {})


async def phone_bubble_async(
    *, user_id: str, tekst: str, timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Vis noget i den flydende boble oven paa andre apps."""
    r = await _phone_call(
        tool="phone_bubble", args={"tekst": str(tekst or "")},
        user_id=user_id, timeout_s=timeout_s,
    )
    return dict(r or {})


# ── Filer og deling ─────────────────────────────────────────────────────


async def phone_read_file_async(
    *, user_id: str, sti: str, timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> str:
    """Laes en fil i appens eget omraade paa telefonen."""
    r = await _phone_call(
        tool="phone_read_file", args={"sti": str(sti)},
        user_id=user_id, timeout_s=timeout_s,
    )
    return str(r or "")


async def phone_write_file_async(
    *, user_id: str, sti: str, indhold: str, timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Skriv en fil i appens eget omraade paa telefonen."""
    r = await _phone_call(
        tool="phone_write_file",
        args={"sti": str(sti), "indhold": str(indhold or "")},
        user_id=user_id, timeout_s=timeout_s,
    )
    return dict(r or {})


async def phone_list_files_async(
    *, user_id: str, sti: str = "", timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> list[str]:
    """Hvad ligger der i appens omraade."""
    r = await _phone_call(
        tool="phone_list_files", args={"sti": str(sti or "")},
        user_id=user_id, timeout_s=timeout_s,
    )
    return list(r or [])


async def phone_share_async(
    *, user_id: str, tekst: str = "", sti: str | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Send noget videre til en anden app via delings-arket.

    **Aabner et ark Bjoern selv skal traeffe et valg i** — vaerktoejet
    afleverer indholdet til systemet, det sender ikke selv noget.
    """
    r = await _phone_call(
        tool="phone_share", args={"tekst": str(tekst or ""), "sti": sti},
        user_id=user_id, timeout_s=timeout_s,
    )
    return dict(r or {})


async def phone_clipboard_read_async(
    *, user_id: str, timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> str:
    """Hvad der ligger i telefonens udklipsholder."""
    r = await _phone_call(
        tool="phone_clipboard_read", args={}, user_id=user_id, timeout_s=timeout_s,
    )
    return str(r or "")


async def phone_clipboard_write_async(
    *, user_id: str, tekst: str, timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Laeg noget i telefonens udklipsholder."""
    r = await _phone_call(
        tool="phone_clipboard_write", args={"tekst": str(tekst or "")},
        user_id=user_id, timeout_s=timeout_s,
    )
    return dict(r or {})


# Alle vaerktoejsnavne ét sted, saa baade definitionerne, exec-tabellen og
# testen kan haenge paa den samme liste i stedet for tre haandholdte kopier.
PHONE_TOOL_NAMES: tuple[str, ...] = (
    "phone_photo", "phone_location", "phone_record_audio",
    "phone_speak", "phone_bubble",
    "phone_read_file", "phone_write_file", "phone_list_files",
    "phone_share", "phone_clipboard_read", "phone_clipboard_write",
)


def _f(navn: str, beskrivelse: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": navn, "description": beskrivelse,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


PHONE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _f("phone_photo",
       "Owner-only. Tag et billede med Bjørns telefon. KRÆVER at appen er i "
       "forgrunden — kameraet kan ikke åbnes fra baggrunden. Fejler med "
       "phone_not_connected hvis telefonen sover.",
       {"kamera": {"type": "string", "enum": ["back", "front"],
                   "description": "Bagkamera (default) eller selfie."},
        "gem_sti": {"type": "string", "description": "Gem også på telefonen (valgfri)."}},
       []),
    _f("phone_location",
       "Owner-only. Hvor Bjørns telefon er lige nu. Virker også når appen "
       "ligger i baggrunden. GPS-fix kan tage op til et minut indendørs.",
       {"noejagtighed": {"type": "string", "enum": ["low", "balanced", "high"],
                         "description": "Højere kræver mere strøm og tid."}},
       []),
    _f("phone_record_audio",
       "Owner-only. Optag lyd fra telefonens mikrofon. Virker også i "
       "baggrunden. Returnerer lyden som base64.",
       {"sekunder": {"type": "number", "description": "0,5-120 sekunder (default 5)."}},
       []),
    _f("phone_speak",
       "Owner-only. Sig noget højt gennem telefonens højttaler.",
       {"tekst": {"type": "string"},
        "sprog": {"type": "string", "description": "Fx da-DK (default) eller en-US."}},
       ["tekst"]),
    _f("phone_bubble",
       "Owner-only. Vis en kort tekst i den flydende boble oven på andre apps.",
       {"tekst": {"type": "string"}}, ["tekst"]),
    _f("phone_read_file",
       "Owner-only. Læs en fil i appens eget område på telefonen.",
       {"sti": {"type": "string"}}, ["sti"]),
    _f("phone_write_file",
       "Owner-only. Skriv en fil i appens eget område på telefonen.",
       {"sti": {"type": "string"}, "indhold": {"type": "string"}}, ["sti", "indhold"]),
    _f("phone_list_files",
       "Owner-only. Vis hvad der ligger i appens område på telefonen.",
       {"sti": {"type": "string", "description": "Undermappe (valgfri)."}}, []),
    _f("phone_share",
       "Owner-only. Aflevér tekst eller en fil til telefonens delings-ark. "
       "ÅBNER et ark Bjørn selv vælger i — værktøjet sender ikke selv noget.",
       {"tekst": {"type": "string"}, "sti": {"type": "string"}}, []),
    _f("phone_clipboard_read",
       "Owner-only. Hvad der ligger i telefonens udklipsholder.", {}, []),
    _f("phone_clipboard_write",
       "Owner-only. Læg noget i telefonens udklipsholder.",
       {"tekst": {"type": "string"}}, ["tekst"]),
]


# ── exec-handlere ───────────────────────────────────────────────────────
#
# Tynde synkrone indgange, som vaerktoejs-tabellen i simple_tools kalder.
# Genbruger operator-saettets to hjaelpere med vilje: ``_operator_user_id``
# er den ENE sandhed om hvem broen tilhoerer, og en egen kopi her ville
# skabe to. ``_run_operator_async`` haandterer den samme
# sync-tool-handler → async-dispatch-overgang.


def _bruger(args: dict[str, Any]) -> str:
    from core.tools.simple_tools_operator import _operator_user_id
    return _operator_user_id(args)


def _koer(coro_fn, *, tool_name: str, timeout_s: float) -> dict[str, Any]:
    from core.tools.simple_tools_operator import _run_operator_async
    return _run_operator_async(coro_fn, tool_name=tool_name, timeout_s=timeout_s)


def _exec_phone_photo(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_photo_async(
        user_id=uid, kamera=str(args.get("kamera") or "back"),
        gem_sti=(str(args["gem_sti"]) if args.get("gem_sti") else None)),
        tool_name="phone_photo", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_location(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_location_async(
        user_id=uid, noejagtighed=str(args.get("noejagtighed") or "balanced")),
        tool_name="phone_location", timeout_s=_LOCATION_TIMEOUT_S + 15.0)


def _exec_phone_record_audio(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    raa = args.get("sekunder")
    sek = max(0.5, min(float(5.0 if raa is None else raa), 120.0))
    return _koer(lambda: phone_record_audio_async(user_id=uid, sekunder=sek),
                 tool_name="phone_record_audio", timeout_s=sek + 35.0)


def _exec_phone_speak(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_speak_async(
        user_id=uid, tekst=str(args.get("tekst") or ""),
        sprog=str(args.get("sprog") or "da-DK")),
        tool_name="phone_speak", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_bubble(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_bubble_async(user_id=uid, tekst=str(args.get("tekst") or "")),
                 tool_name="phone_bubble", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_read_file(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_read_file_async(user_id=uid, sti=str(args.get("sti") or "")),
                 tool_name="phone_read_file", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_write_file(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_write_file_async(
        user_id=uid, sti=str(args.get("sti") or ""),
        indhold=str(args.get("indhold") or "")),
        tool_name="phone_write_file", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_list_files(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_list_files_async(user_id=uid, sti=str(args.get("sti") or "")),
                 tool_name="phone_list_files", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_share(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_share_async(
        user_id=uid, tekst=str(args.get("tekst") or ""),
        sti=(str(args["sti"]) if args.get("sti") else None)),
        tool_name="phone_share", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_clipboard_read(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_clipboard_read_async(user_id=uid),
                 tool_name="phone_clipboard_read", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


def _exec_phone_clipboard_write(args: dict[str, Any]) -> dict[str, Any]:
    uid = _bruger(args)
    return _koer(lambda: phone_clipboard_write_async(user_id=uid, tekst=str(args.get("tekst") or "")),
                 tool_name="phone_clipboard_write", timeout_s=_DEFAULT_TIMEOUT_S + 15.0)


PHONE_TOOL_EXECUTORS: dict[str, Any] = {
    "phone_photo": _exec_phone_photo,
    "phone_location": _exec_phone_location,
    "phone_record_audio": _exec_phone_record_audio,
    "phone_speak": _exec_phone_speak,
    "phone_bubble": _exec_phone_bubble,
    "phone_read_file": _exec_phone_read_file,
    "phone_write_file": _exec_phone_write_file,
    "phone_list_files": _exec_phone_list_files,
    "phone_share": _exec_phone_share,
    "phone_clipboard_read": _exec_phone_clipboard_read,
    "phone_clipboard_write": _exec_phone_clipboard_write,
}
