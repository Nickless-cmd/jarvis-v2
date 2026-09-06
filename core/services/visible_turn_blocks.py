"""Den kanoniske content-blok-array for en assistent-tur (spec §4).

Udskilt fra ``visible_runs.py`` (7.078 linjer) 2026-09-02 efter Boy Scout-reglen,
før rækkefølge-fejlen nedenfor blev rettet. Enheden er naturlig: én funktion med
ét ansvar — at oversætte en turs tekst, værktøjskald og resultater til den
rækkefølge klienten skal vise dem i.

## Fejlen der udløste udskillelsen (Bjørn 2026-09-02)

«Under streaming vises synteser og resultater korrekt, men når streaming
slutter falder hans synteser sammen og tool results bliver flyttet op i toppen
af beskeden.»

Målt på en ægte tur: content_json havde 22 blokke — 7 tool_use, 7 tool_result,
**1** text og 7 tomme progress. Alle værktøjer lå på index 0-13, teksten på 14.

Årsagen var at builderen kun fik ÉN samlet tekst-streng. Interleave-loggen
kendte godt rækkefølgen, men når al tekst er smeltet til én blob, kan den kun
placeres ét sted — og valget faldt på den SIDSTE text-markør (for at undgå at
hele svaret hoppede op foran kortene). Resultatet: mellemsynteserne forsvandt
ind i den afsluttende blob, og værktøjerne stod alene i toppen.

Rettelsen er at bevare tekst-SEGMENTER: ét pr. sammenhængende stykke tekst
mellem værktøjskald. Så kan hvert segment lægges hvor det hører hjemme, og
tråden læses som den blev til: fortælling → værktøj → fortælling.
"""

from __future__ import annotations


def _tool_label(tool_name: str, arguments: dict | None = None) -> str:
    """Narrationen for ét værktøjskald — samme tekst som live-visningen brugte.

    Importeres dovent fra ``visible_runs`` for at undgå en cirkulær import:
    visible_runs re-eksporterer _build_turn_blocks herfra.
    """
    from core.services.visible_runs import _tool_label as _impl

    return _impl(tool_name, arguments)


def _build_progress_blocks(
    tool_calls: list[dict], tool_results: list[dict]
) -> list[dict]:
    """Byg det FLADE progress-spor for en tur (spec §5).

    Ét ``progress``-element pr. tool-kald i kald-rækkefølge. ``message`` er
    ``_tool_label(name, input)`` — nøjagtig den narration den live
    ``working_step`` viste før exec (deterministisk fra name+args). ``status``
    settles fra tool_result (error hvis fejlet, ellers done). ``parent_tool_use_id``
    er altid ``None`` (fladt — træet kræver spawn-plumbing der ikke findes endnu).
    Ren funktion; sikker at teste isoleret."""
    results_by_id: dict[str, dict] = {}
    for r in (tool_results or []):
        results_by_id[str(r.get("tool_use_id") or "")] = r
    out: list[dict] = []
    for tc in (tool_calls or []):
        tid = str(tc.get("id") or "")
        name = str(tc.get("name") or "tool")
        raw_input = tc.get("input") or {}
        if isinstance(raw_input, str):
            try:
                import json as _json
                raw_input = _json.loads(raw_input)
            except Exception:
                raw_input = {}
        args = raw_input if isinstance(raw_input, dict) else {}
        try:
            message = _tool_label(name, args)
        except Exception:
            message = name
        r = results_by_id.get(tid)
        status = "done"
        if r is not None and (
            r.get("is_error") or str(r.get("status") or "") == "error"
        ):
            status = "error"
        out.append({
            "type": "progress",
            "tool_use_id": tid,
            "parent_tool_use_id": None,
            "message": str(message or name),
            "status": status,
        })
    return out


def _build_turn_blocks(
    *, text: str, tool_calls: list[dict], tool_results: list[dict],
    interleave: list[str] | None = None,
    text_segments: list[str] | None = None,
) -> list[dict]:
    """Byg den kanoniske content-blok-array for en assistant-tur (spec §4).

    Når *interleave* er givet (liste af 'text'/'tool'), følges den rækkefølge —
    tekst- og tool-blokke placeres i den orden de kom under streamen.
    Uden interleave: degraderet fallback (tekst først, så tool-par jf. spec §5).

    *text_segments* er ét stykke tekst pr. sammenhængende tekst-stykke mellem
    værktøjskald, i rækkefølge. Er den givet, lægges hvert segment ved SIN egen
    text-markør, og turen kan læses som den blev til: fortælling → værktøj →
    fortælling. Uden den falder vi tilbage på den gamle adfærd (én samlet blob
    ved sidste markør), som mistede alle mellemsynteser.
    """
    blocks: list[dict] = []
    clean = str(text or "").strip()
    # Stol KUN på interleave-rækkefølgen når dens 'tool'-markører gør rede for
    # ALLE tool-kald. Native batch-tool-exec fører ikke _interleave_log (kun evt.
    # en enkelt 'text'-markør fra en streamet svar-delta) → interleave undertæller
    # tools → de resterende ville blive hængt PÅ efter teksten så kortene falder i
    # bunden (Bjørn 10. jul, 6 native kald). I det tilfælde: brug fallback der
    # lægger tools først og svaret til sidst.
    _tool_markers = sum(1 for k in (interleave or []) if k == "tool")
    _trust_interleave = bool(interleave) and _tool_markers >= len(tool_calls or [])
    if _trust_interleave:
        # Dedupliér KUN consecutive 'text' (så én tekst-blob ikke splittes i to
        # blokke). 'tool'-entries BEVARES ALLE — ellers kollapser flere tool-kald
        # i træk til ét (Bjørn 10. jul: kun sidste tool overlevede + svar forsvandt).
        deduped: list[str] = []
        for e in interleave:
            if e == "text" and deduped and deduped[-1] == "text":
                continue
            deduped.append(e)

        results_by_id: dict[str, dict] = {}
        for r in (tool_results or []):
            results_by_id[str(r.get("tool_use_id") or "")] = r
        text_placed = False
        # Basér på tool_calls (IKKE zip m. results) — zip truncerer hvis results
        # er kortere → tabt tool. Result hentes robust via results_by_id[tid].
        tool_pairs = list(tool_calls or [])
        pi = 0
        # Placér den (enkelt-akkumulerede) tekst ved SIDSTE 'text'-markør, ikke
        # den første. Reasoning-modeller streamer ofte en kort præ-tekst FØR de
        # kalder værktøjer og skriver så det egentlige svar EFTER resultaterne
        # (round 1: kort tekst + tool_calls; round 2: analysen). Vi har kun ÉN
        # samlet tekst-blob — lægges den ved første markør, hopper HELE svaret op
        # foran tool-kortene så de lander i bunden (Bjørn 10. jul). Sidste markør
        # = svaret lander efter de værktøjer det brugte. Kun-før-tool-tekst
        # (last==first) er uændret.
        last_text_idx = max(
            (i for i, k in enumerate(deduped) if k == "text"), default=-1
        )
        # Segmenter: ét pr. text-markør, i rækkefølge. Er de der, placeres hvert
        # segment hvor det hørte hjemme — det er dét der genskaber
        # fortælling → værktøj → fortælling.
        segments = [s for s in (text_segments or []) if str(s or "").strip()]
        seg_i = 0
        for idx, kind in enumerate(deduped):
            if kind == "text":
                if segments:
                    if seg_i < len(segments):
                        blocks.append({"type": "text", "text": segments[seg_i].strip()})
                        seg_i += 1
                        text_placed = True
                elif not text_placed and clean and idx == last_text_idx:
                    blocks.append({"type": "text", "text": clean})
                    text_placed = True
            elif kind == "tool":
                if pi < len(tool_pairs):
                    tc = tool_pairs[pi]
                    tid = str(tc.get("id") or "")
                    blocks.append({
                        "type": "tool_use",
                        "id": tid,
                        "name": str(tc.get("name") or ""),
                        "input": tc.get("input") or {},
                    })
                    r = results_by_id.get(tid)
                    if r is not None:
                        status = str(r.get("status") or "done")
                        blocks.append({
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "status": "error" if (r.get("is_error") or status == "error") else "done",
                            "content": str(r.get("content") or ""),
                            "is_error": bool(r.get("is_error")),
                        })
                    pi += 1
        # Robusthed: tools/svar må ALDRIG droppes selv om interleave undercounter.
        # Placer resterende tools + svar-teksten hvis den ikke blev placeret.
        while pi < len(tool_pairs):
            tc = tool_pairs[pi]
            tid = str(tc.get("id") or "")
            blocks.append({"type": "tool_use", "id": tid,
                           "name": str(tc.get("name") or ""), "input": tc.get("input") or {}})
            r = results_by_id.get(tid)
            if r is not None:
                status = str(r.get("status") or "done")
                blocks.append({
                    "type": "tool_result", "tool_use_id": tid,
                    "status": "error" if (r.get("is_error") or status == "error") else "done",
                    "content": str(r.get("content") or ""), "is_error": bool(r.get("is_error")),
                })
            pi += 1
        # Rester: segmenter der ikke fik en markør må ikke tabes.
        if segments:
            while seg_i < len(segments):
                blocks.append({"type": "text", "text": segments[seg_i].strip()})
                seg_i += 1
                text_placed = True
        if clean and not text_placed:
            blocks.append({"type": "text", "text": clean})
    else:
        # Degraderet fallback (ingen interleave — fx native batch-tool-exec-stien
        # der ikke fører _interleave_log): tool-par FØRST i kald-rækkefølge, så
        # svar-teksten TIL SIDST. Uden rækkefølge-info er teksten næsten altid det
        # afsluttende svar der opsummerer værktøjerne → skal ligge efter kortene,
        # ikke foran så de falder til bunden (Bjørn 10. jul: 6 native tool-kald
        # rendrede med tekst på index 0 → kort i bunden). Ren tekst-tur (ingen
        # tools) giver bare ét tekst-blok.
        results_by_id = {}
        for r in (tool_results or []):
            results_by_id[str(r.get("tool_use_id") or "")] = r
        for tc in (tool_calls or []):
            tid = str(tc.get("id") or "")
            blocks.append({
                "type": "tool_use",
                "id": tid,
                "name": str(tc.get("name") or ""),
                "input": tc.get("input") or {},
            })
            r = results_by_id.get(tid)
            if r is not None:
                status = str(r.get("status") or "done")
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tid,
                    "status": "error" if (r.get("is_error") or status == "error") else "done",
                    "content": str(r.get("content") or ""),
                    "is_error": bool(r.get("is_error")),
                })
        if clean:
            blocks.append({"type": "text", "text": clean})
    # Fladt progress-spor (feature 4, spec 2026-07-09 §5) — gælder BEGGE stier
    # (interleave + fallback): ét settlet element pr. tool-kald + narration.
    # Fail-open: en fejl her må aldrig vælte blok-bygningen for et live run.
    try:
        blocks.extend(_build_progress_blocks(tool_calls, tool_results))
    except Exception:
        pass
    return blocks


