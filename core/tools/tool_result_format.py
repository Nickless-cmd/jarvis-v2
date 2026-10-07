"""Formatering af vaerktoejsresultater til modellen + verify-hints.

Udskilt fra core/tools/simple_tools.py (Boy Scout, 2026-10-07) foer agent-vaerktoejerne
blev registreret dér. Rene funktioner uden tilstand; re-eksporteret fra `simple_tools`,
saa `format_tool_result_for_model` og de oevrige finder den uaendret.
"""
from __future__ import annotations

import json
from typing import Any

from core.services.text_clip import clip_head_tail as _clip_head_tail


def _verify_hint_for(tool: str, result: dict[str, Any]) -> str | None:
    """Build a brief, contextual verify-hint to attach to a mutation's result.

    Phase 2 of the verification-gate honesty work (2026-05-14). Hints appear
    INSIDE the tool result Jarvis just sees, in the same breath as the
    mutation — instead of post-hoc in awareness 10 min later when focus
    has moved on.

    Returns None for non-mutation tools or for tools that don't have a
    natural verify pairing (bash, memory writes etc — Jarvis decides).
    """
    if str(result.get("status") or "") != "ok":
        return None
    path = str(result.get("path") or "")
    if tool in ("write_file", "edit_file", "publish_file", "stage_edit_file"):
        # 10. sep 2026: write_file/edit_file bærer nu deres EGEN read-back fra
        # disken (core/tools/file_tools_exec._disk_readback). Hintet må ikke
        # længere sende Jarvis ud i et ekstra læs for at se noget han allerede
        # har fået — det var samme «forbundet, men blind»-klasse: et hint der
        # pegede væk fra beviset.
        if result.get("readback"):
            return (
                "💡 Readback'en ovenfor er læst fra disken EFTER skrivningen — "
                "er den ikke som du regnede med, så ret den nu."
            )
        if path:
            return (
                f"💡 Verify-hint: kør verify_file_contains(path='{path}', ...) "
                "med en streng du forventer der står — eller bare read_file "
                "for at se hvad du faktisk skrev."
            )
        return (
            "💡 Verify-hint: read_file den fil du lige ændrede for at bekræfte "
            "diff'en blev som du regnede med."
        )
    if tool in ("control_daemon", "restart_overdue_daemons"):
        return (
            "💡 Verify-hint: verify_service_active eller process_list for at "
            "tjekke at servicen faktisk kører — restart-kommandoer fejler tit "
            "stille."
        )
    if tool == "propose_git_commit":
        return (
            "💡 Verify-hint: git_log eller bash 'git status' for at bekræfte "
            "commit'en landede og din working tree er som forventet."
        )
    if tool == "memory_upsert_section":
        return (
            "💡 Verify-hint: read_file MEMORY.md eller search_memory for at "
            "bekræfte sektionen blev skrevet i den form du ville."
        )
    if tool == "send_discord_dm":
        return (
            "💡 Verify-hint: send_discord_dm bekræfter kun at API'et "
            "accepterede beskeden. Selve leveringen verificeres af brugeren."
        )
    return None


def _json_safe_default(o: Any) -> str:
    """json.dumps default= — GARANTERER at serialisering af et tool-resultat
    aldrig kaster. bytes → utf-8/base64, alt andet → str(). Uden dette crashede
    et enkelt BLOB-felt (fx db_query) hele det synlige run med 'Object of type
    bytes is not JSON serializable' (2026-07-10). Sidste forsvarslinje: ethvert
    tool kan returnere hvad som helst uden at vælte streamet."""
    if isinstance(o, (bytes, bytearray)):
        b = bytes(o)
        try:
            return b.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            import base64
            return f"<{len(b)} bytes base64:{base64.b64encode(b).decode('ascii')[:88]}>"
    return str(o)


def _signal_linjer(result: dict[str, Any]) -> str:
    """Korte linjer for signaler der ellers forsvinder naar ``text`` findes.

    MAALT 5/10-2026: ``_exec_bash`` laegger baade ``kanal.note`` (operator-
    kanalen faldt af sig selv og blev IKKE genoprettet) og ``confinement``
    (koerte kommandoen indespærret?) paa svaret. Formateringen returnerer
    ``text`` naar den findes og kaster ALLE andre noegler vaek — saa begge
    beskeder naaede aldrig modellen. Beskeden VAR der; den blev kastet vaek et
    lag laengere fremme. Det er praecis den fejlform Bjørn bad om at faa lukket
    («fiks kanalen saa du faar besked med det samme den ryger»): uden den koerer
    kommandoen paa serveren i det stille, og «filen findes ikke» kan i
    virkeligheden betyde «du maalte det forkerte sted».

    Rammer KUN tekst-grenen: dumps resultatet som JSON, er noeglerne i
    forvejen synlige og linjerne ville vaere gentagelser.
    """
    linjer: list[str] = []
    kanal = result.get("kanal")
    if isinstance(kanal, dict):
        note = str(kanal.get("note") or "").strip()
        if note:
            linjer.append(note)
        elif kanal.get("genaabnet"):
            linjer.append("[operator-kanal] kanalen var udloebet og blev "
                          "genaabnet af dette kald.")
    # Kun naar indespærring var ØNSKET men IKKE håndhævet. Er den håndhævet,
    # er der intet at sige — og en linje paa hvert eneste bash-kald ville
    # begrave de signaler der faktisk betyder noget.
    conf = result.get("confinement")
    if isinstance(conf, dict) and conf.get("requested") and not conf.get("honored", True):
        aarsag = str(conf.get("reason") or "").strip()
        linjer.append("[indespaerring] ønsket, men IKKE håndhævet"
                      + (f": {aarsag}" if aarsag else ""))
    return ("\n" + "\n".join(linjer)) if linjer else ""


def format_tool_result_for_model(
    name: str, result: dict[str, Any], *, clip: bool = True,
) -> str:
    """Format a tool result as text for the model's context.

    ``clip=False`` springer laengde-loftet over og returnerer HELE resultatet.
    Bruges kun til det der PERSISTERES i tool-result-storen, aldrig til det der
    laegges i samtalen — se `save_tool_result`-kaldet i chat_sessions.

    Baggrund (5/9-2026): et resultat uden `text`-noegle dumpes som JSON og
    klippes ved 8.000 tegn med hoved+hale bevaret. Bjoern saa gentagne gange
    "midten mangler" — maalt: 728 gemte tool-resultater har et hul, i dag ét paa
    131.200 tegn ud af 143.770. Beskeden i samtalen lover
    "Use read_tool_result ... to inspect the full output", men den KLIPPEDE
    tekst var det eneste der nogensinde blev gemt. Midten fandtes ingen steder.
    """
    status = result.get("status", "unknown")

    if status == "error":
        # `text` FOER `unknown error` (27/9-2026). 74 steder i vaerktoejerne
        # laegger deres fejlbesked i `text` og ikke i `error` — `read_attachment`
        # er en af dem. Uden dette fald tilbage viste hvert eneste af dem
        # «unknown error», og den rigtige aarsag fandtes ingen steder i
        # samtalen: beskeden VAR der, den blev kastet vaek her.
        besked = result.get("error") or result.get("text") or "unknown error"
        return f"[Tool {name} error: {besked}]"

    if status == "blocked":
        return f"[Tool {name} blocked: {result.get('error', 'blocked for safety')}]"

    if status == "approval_needed":
        return f"[Tool {name}: {result.get('message', 'requires user approval')}]"

    # `text_full` vinder naar hele resultatet skal persisteres (6/9-2026).
    # bash klipper SIG SELV inde i `_exec_bash` foer resultatet naar hertil,
    # saa clip=False fik intet at arbejde med: den "fulde" gemte udgave var
    # ogsaa klippet, og midten fandtes ingen steder. Maalt: 76.950 tegn ->
    # 16.018, med 60.932 udeladt og ingen vej tilbage til dem. Fixet fra 5/9
    # daekkede kun vaerktoejer der returnerer hele teksten og lader
    # formateringen klippe.
    text = ""
    # Sandt naar `text` blev dannet ved at dumpe HELE resultatet som JSON.
    # Saa er sidestraenge som `kanal` og `confinement` i forvejen synlige, og
    # `_signal_linjer` nedenfor skal ikke gentage dem.
    _fra_json = False
    if not clip:
        text = str(result.get("text_full") or "")
    if not text:
        text = result.get("text", "")
    if not text:
        # Human-friendly summaries for common tool results
        path = result.get("path", "")
        if name == "write_file" and path:
            size = result.get("size", "")
            text = f"Wrote {path}" + (f" ({size} bytes)" if size else "")
        elif name == "edit_file" and path:
            n = result.get("replacements", 0)
            text = f"Edited {path} ({n} replacement{'s' if n != 1 else ''})"
        else:
            _fra_json = True
            # Defense-in-depth: cap the raw JSON fallback so a tool returning a
            # fat payload can't spill thousands of tokens into visible context.
            # Raised from 1500 → 8000 so most tool results show in full.
            # When still over limit, truncate gracefully — show the actual
            # partial content rather than a useless "truncated" placeholder.
            _MAX_FALLBACK_CHARS = 8000
            _filtered = {k: v for k, v in result.items() if k != "status"}
            _dumped = json.dumps(
                _filtered, ensure_ascii=False, indent=2, default=_json_safe_default
            )
            if not clip or len(_dumped) <= _MAX_FALLBACK_CHARS:
                text = _dumped
            else:
                # Bevar HOVED+HALE (ikke kun head) ved linje-grænser — slutningen af et struktureret
                # tool-resultat er ofte det vigtigste. Se text_clip.clip_head_tail.
                _keys = ", ".join(sorted(_filtered.keys())) or "<none>"
                text = (
                    _clip_head_tail(_dumped, limit=_MAX_FALLBACK_CHARS)
                    + f"\n[keys: {_keys}. Tilføj en 'text'-nøgle i toolets exec for et rent resumé.]"
                )

    # Signaler der bor i sidestraenge (5/10-2026). Se `_signal_linjer`.
    if text and not _fra_json:
        text += _signal_linjer(result)

    # Phase 2 of verification-gate honesty (2026-05-14): attach a brief
    # verify hint to mutation results so it lands in the SAME breath as
    # the mutation, not 10 min later in post-hoc awareness.
    hint = _verify_hint_for(name, result)
    if hint:
        return f"{text}\n\n{hint}"
    return text
