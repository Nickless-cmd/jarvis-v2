"""Read-only research-agent tool with runtime/Desk execution routing."""
from __future__ import annotations

import re

from typing import Any

_EXPLORE_MAKS_RUNDER = 3


def _facade():
    import core.tools.simple_tools_native as module
    return module


def _execution_context(args: dict[str, Any]) -> tuple[str, dict[str, object], str]:
    requested = str(args.get("target") or "auto").strip().lower()
    if requested not in {"auto", "runtime", "workstation"}:
        return "", {}, "target must be auto, runtime, or workstation"
    session_id = str(args.get("_runtime_session_id") or "").strip()
    try:
        from core.services.chat_sessions import get_chat_session
        session = get_chat_session(session_id) if session_id else None
    except Exception:
        session = None
    kind = str((session or {}).get("workspace_kind") or "").strip().lower()
    root = str((session or {}).get("workspace_root") or "").strip()
    target = "workstation" if requested == "auto" and kind == "workstation" and root else requested
    if target == "auto":
        target = "runtime"
    if target == "runtime":
        return target, {"execution_target": target}, ""
    if kind != "workstation" or not root or not session_id:
        return "", {}, "workstation target requires an active Desk workstation-workspace"
    user_id = str(args.get("_runtime_user_id") or "").strip()
    if not user_id:
        try:
            from core.identity.workspace_context import current_user_id
            user_id = str(current_user_id() or "").strip()
        except Exception:
            pass
    if not user_id:
        return "", {}, "workstation target requires an authenticated Desk user"
    return target, {"execution_target": target, "workspace_root": root,
                    "user_id": user_id, "session_id": session_id}, ""


def _explore_spawn(*, query: str, vejledning: str, provider: str = "", model: str = "",
                   target: str = "runtime", context: dict[str, object] | None = None) -> dict:
    from core.services.agent_runtime import spawn_agent_task
    from core.services.agent_runtime_base import tools_for_policy
    policy = "read-only-workstation" if target == "workstation" else "read-only-runtime"
    target_prompt = (
        "Du arbejder i Jarvis Desk-workspacet på brugerens maskine. Brug kun "
        "operator_read_file, operator_glob, operator_grep og operator_list_dir. "
        "Alle filstier skal være absolutte og ligge under workspace_root i din context. "
        "operator_grep giver korrekte linjenumre."
        if target == "workstation" else
        "Du arbejder i Jarvis' runtime-container. `search` giver korrekte linjenumre."
    )
    return spawn_agent_task(
        role="researcher", goal=f"{query}\n\n{vejledning}",
        system_prompt=(
            "Du er en undersoegende agent. Du LAESER — du aendrer ingenting. "
            "Svar med hvad du FANDT, med filsti og linjenummer hvor det giver mening. "
            "Gaet aldrig: har du ikke set det i en kilde, saa skriv at du ikke ved det.\n\n"
            "ET TOMT SOEG ER IKKE ET SVAR. Foer du siger at noget IKKE findes, "
            "skal du have proevet mindst to forskellige veje. Fejler et vaerktoej, "
            "saa proev en anden vej i stedet for at konkludere. Skriv altid hvilke "
            "soegninger du faktisk koerte.\n\n"
            "Tillid: hoej kraever at du har SET kilden. Har du kun tomme soegninger, "
            "er tilliden lav.\n\n"
            "LINJENUMRE: taeller du dem ALDRIG selv. Brug et soegevaerktoej der "
            "returnerer linjenummeret; ellers skriv filstien uden nummer.\n\n"
            f"{target_prompt}"
        ),
        tool_policy=policy, allowed_tools=tools_for_policy(policy), budget_tokens=0,
        persistent=False, ttl_seconds=0, auto_execute=True, provider=provider,
        model=model, context=dict(context or {"execution_target": target}),
        # Explores rotation har ALLEREDE filtreret paa egnethed OG paa om
        # modellen kan kalde vaerktoejer. En capability-vagt ovenpaa er ikke
        # ekstra sikkerhed — den kasserede valget og gav os nemotron tilbage
        # tre runder i traek.
        respekter_model=bool(provider and model),
    )


def _explore_svar(result: dict) -> tuple[str, str]:
    svar, fejl = "", ""
    for msg in reversed(result.get("messages") or []):
        if str(msg.get("direction") or "") != "agent->jarvis":
            continue
        kind = str(msg.get("kind") or "")
        if kind == "provider-error" and not fejl:
            fejl = str(msg.get("content") or "")
        elif kind in ("result", "") and not svar:
            svar = str(msg.get("content") or "")
    return svar, fejl



def _bro_kontrol(args: dict):
    """Byg de to efterproevninger der slaar op OVER BROEN, paa Bjoerns maskine.

    ÉT sted ejer bro-ruten. Foer laa den to steder: `_bro_tjek` sendte
    brugeren med, `_bro_linje` gjorde ikke — saa `_operator_user_id()`
    udledte selv og faldt gennem session -> owner_user_id -> hardkodet id.
    For EJEREN var det tilfaeldigvis rigtigt; for enhver anden gik
    indholds-tjekket til ejerens bro, fejlede, og gav `None`. Et tavst
    no-op, som er den vaerre slags: koblet paa, svarer korrekt, ser
    ingenting — fordi det spoerger den forkerte maskine. (Jarvis' fund.)

    Begge svarer `None` naar broen ikke kan afgoere det. Et vaern der
    gaetter er vaerre end intet.
    """
    bruger = str(args.get("_runtime_user_id") or "").strip()
    session = str(args.get("_runtime_session_id") or "").strip()

    def findes(sti: str):
        try:
            from core.tools.simple_tools_operator import _operator_file_exists
            return _operator_file_exists(sti, bruger)
        except Exception:
            return None

    def linje(sti: str, nr: int, fragment: str):
        """Efterproev et CITAT. Jarvis havde ret i prisen: ét `operator_grep`
        koster 0,08 s — det SAMME som eksistens-tjekket — og giver fil,
        linjenummer og tekst i ét kald.

        Findes fragmentet slet ikke, er citatet opdigtet; findes det paa en
        ANDEN linje, er linjenummeret forkert. Begge dele er en fejl vaerd
        at sige.
        """
        try:
            from core.tools.simple_tools_operator import _exec_operator_grep
            svar = _exec_operator_grep({
                "pattern": re.escape(fragment), "path": sti,
                "max_results": 20,
                "_runtime_user_id": bruger,
                "_runtime_session_id": session,
            })
        except Exception:
            return None
        if not isinstance(svar, dict) or svar.get("status") != "ok":
            return None
        traef = svar.get("result")
        if not isinstance(traef, list):
            return None
        if not traef:
            return False                        # fragmentet findes slet ikke
        return any(int(t.get("line") or 0) == int(nr)
                   for t in traef if isinstance(t, dict))

    return findes, linje

def _exec_explore(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or args.get("goal") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    target, context, context_error = _execution_context(args)
    if context_error:
        return {"status": "error", "error": context_error}
    # HERKOMST (Fase 5): «`explore` appears under its parent».
    #
    # Maalt 10/9-2026: de 96 explore-boern havde durabel identitet, korrekt
    # raekkefoelge (registreret FOER deres run) og en foraelder — men foraeldren
    # var konstanten «jarvis» for dem alle, og `context_json` indeholdt kun
    # `{"spawn_depth": 0}`. Der var altsaa ingen forbindelse til den TUR der
    # foedte barnet, saa intet kunne vise dem under den.
    #
    # Oplysningen laa i `args` hele tiden — runtime injicerer den i hvert kald.
    herkomst = {k: v for k, v in (
        ("parent_session_id", str(args.get("_runtime_session_id") or "").strip()),
        ("parent_run_id", str(args.get("_runtime_turn_id") or "").strip()),
    ) if v}
    bredde = str(args.get("breadth") or "medium").strip().lower()
    vejledning = {"quick": "Kig ét sted og svar kort.",
                  "medium": "Kig flere steder og sammenhold dem.",
                  "thorough": ("Kig grundigt: flere navnekonventioner, flere mapper, og "
                               "verificér hvert fund i kilden foer du melder det.")}.get(
                                   bredde, "Kig flere steder og sammenhold dem.")
    try:
        from core.services.agent_model_fitness import egnede_modeller
        from core.services.explore_claim_check import tjek_paastande
    except Exception:
        egnede_modeller = tjek_paastande = None
    # WORKSTATION-VAERNET (10/9-2026). Foer stod her `tjek_paastande = None`:
    # vaernet blev slaaet HELT fra naar Jarvis undersoegte Bjoerns egen maskine.
    #
    # Det var RIGTIGT som det stod. `explore_claim_check._rod()` peger paa
    # CONTAINERENS repo, saa et opslag dér ville have flaget hver eneste sti paa
    # Bjoerns maskine som opdigtet — falske anklager i stedet for manglende
    # vaern. Men det efterlod netop den sti hvor en fabrikeret rapport koster
    # mest, helt uden efterproevning.
    #
    # Nu slaas stierne op DÉR HVOR DE BOR, over broen. `_operator_file_exists`
    # er billig og read-only (lister forael dre-mappen), og den svarer `None`
    # naar den ikke kan afgoere det — hvilket hverken taeller som fund eller
    # fejl. Et vaern der gaetter er vaerre end intet.
    _bro_tjek = _bro_linje = None
    if target == "workstation":
        _bro_tjek, _bro_linje = _bro_kontrol(args)
    brugt: set[tuple[str, str]] = set()
    sidste_fejl: list[str] = []
    svar, agent_id, kontrolleret = "", "", 0
    for runde in range(_EXPLORE_MAKS_RUNDER):
        prov, mod = "", ""
        if runde:
            if egnede_modeller is None:
                break
            # Explore LAESER filer — opgaven kraever vaerktoejer. En model
            # der aldrig kalder dem, fabrikerer svaret i stedet.
            kandidater = egnede_modeller(undtagen=frozenset(brugt), maks=4,
                                         kraever_vaerktoejer=True)
            if not kandidater:
                break
            prov, mod = kandidater[0]
        try:
            spawn_args: dict[str, Any] = {"query": query, "vejledning": vejledning,
                                          "provider": prov, "model": mod}
            if target == "workstation":
                spawn_args.update({"target": target,
                                   "context": {**context, **herkomst}})
            elif herkomst:
                # Ogsaa paa runtime-stien: herkomsten hoerer til barnet,
                # ikke til hvor det tilfaeldigvis koerer.
                spawn_args["context"] = {"execution_target": target, **herkomst}
            result = _facade()._explore_spawn(**spawn_args)
        except Exception as exc:
            return {"status": "error", "error": str(exc), "breadth": bredde,
                    "target": target}
        agent_id = str(result.get("agent_id") or "")
        brugt.add((str(result.get("provider") or prov), str(result.get("model") or mod)))
        svar_n, udbyder_fejl = _explore_svar(result)
        if not svar_n:
            sidste_fejl = [udbyder_fejl or str(result.get("error") or "agenten fejlede")]
            continue
        svar = svar_n
        if tjek_paastande is None:
            break
        dom = (tjek_paastande(svar, findes_fn=_bro_tjek, linje_fn=_bro_linje)
               if _bro_tjek else tjek_paastande(svar))
        kontrolleret = int(dom.get("kontrolleret") or 0)
        _substans = int(dom.get("indhold_bekraeftet") or 0)
        # NUL VAERKTOEJSKALD KAN IKKE HAVE FUNDET NOGET.
        #
        # Agenten skal LAESE noget for at kunne svare. Udfoerte den ingen kald,
        # er svaret gaettet — uanset hvor praecist det lyder. Det var praecis
        # hvad der skete: fire opdigtede citater med linjenumre, fra en model
        # der aldrig kaldte et vaerktoej.
        #
        # `_run_agent_tool_loop` taeller kaldene og lagger dem i resultatet.
        # Vi kraever kun at der var MINDST ét — ikke at det var det rigtige.
        # `tool_calls` BETYDER TO TING, og det er derfor dette braekkede.
        #
        # I koerslens `output_payload_json` er det et TAL (loekkens taelling).
        # I agent-fladen (`enrich_agent_surface`) er det en LISTE, og tallet
        # hedder `tool_call_count`. Explore faar fladen, men laeste navnet med
        # payloadens betydning: `int(<liste>)` kaster.
        #
        # Det havde ligget der hele tiden og aldrig fejlet, fordi `[] or 0`
        # er 0 — saa laenge listen var TOM. Mine to fixes i dag gjorde den
        # ikke-tom: bogfoeringen fyldte den, og rotationen soergede for at der
        # var noget at bogfoere. Jo bedre agenten opfoerte sig, jo sikrere
        # crashede det — agenten laeste filen KORREKT, og hele svaret blev
        # kastet vaek af wrappen bagefter. (Jarvis' fjerde koersel.)
        #
        # Der laeses derfor efter FORM, ikke efter navn: et navn der er
        # aerligt i to sammenhaenge og loegnagtigt i den tredje maa ikke
        # afgoeres af hvilken vej svaret kom.
        _raa = result.get("tool_call_count")
        if _raa is None:
            _raa = result.get("tool_calls")
        _kald = (len(_raa) if isinstance(_raa, (list, tuple, set))
                 else int(_raa or 0))
        _tomhaendet = _kald == 0 and _substans == 0
        if dom.get("holder") and not _tomhaendet:
            # `bevis` SKAL med ud. Uden det laeser en modtager
            # «paastande_kontrolleret: 0» som en detalje og `status: ok` som en
            # blaastempling — og en rapport hvor INTET blev efterproevet ser
            # identisk ud med en der er gennemgaaet. (Jarvis' fund.)
            return {"status": "ok", "findings": svar[:12000] or None,
                    "agent_id": agent_id, "breadth": bredde, "target": target,
                    "paastande_kontrolleret": kontrolleret,
                    "bevis": str(dom.get("bevis") or "intet-bevis"),
                    "bevis_note": (
                        "Ingen efterproevelig paastand fundet — dette svar er "
                        "IKKE verificeret, det er blot ikke modsagt."
                        if kontrolleret == 0 else
                        f"{kontrolleret} paastand(e) slaaet op og bekraeftet.")}
        sidste_fejl = [str(x) for x in (dom.get("fejl") or [])]
        if _tomhaendet and not sidste_fejl:
            # Ingen paaviselig fejl — men heller intet belaeg. Rotér frem for
            # at blaastemple. Foer returnerede vi paa runde 0, saa den
            # mekanisme der skulle skifte modellen ud koerte ALDRIG: gaten
            # blev sat ud af spil af netop den fejl den var bygget til at
            # fange.
            sidste_fejl = [
                f"agenten udfoerte {_kald} vaerktoejskald og fik intet indhold "
                "bekraeftet — svaret kan ikke hvile paa noget den har laest"
            ]
    if svar:
        payload: dict[str, Any] = {"status": "ok", "findings": svar[:12000],
                                   "agent_id": agent_id, "breadth": bredde,
                                   "target": target,
                                   "paastande_kontrolleret": kontrolleret}
        if sidste_fejl:
            payload["advarsel"] = "paastande kunne ikke bekraeftes i kilden: " + "; ".join(sidste_fejl[:4])
        return payload
    return {"status": "error", "breadth": bredde, "target": target,
            "agent_id": agent_id, "error": "undersoegelsen kom ikke igennem: "
            + ("; ".join(sidste_fejl[:3]) or "intet svar")}


__all__ = ["_EXPLORE_MAKS_RUNDER", "_exec_explore", "_explore_spawn", "_explore_svar"]
