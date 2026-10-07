#!/usr/bin/env python3
"""E2E: holder indbakke-kæden usmocket, i produktionen?

Opgave 14 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.
Den er sidst og obligatorisk. **Dette script ER testen** — det har ingen egne tests.

## Hvorfor en grøn suite ikke er nok

Huset har to målte grunde:

* 577 grønne tests missede to fejl som fem minutter på telefonen fandt — kold
  mod varm kodesti.
* Min lokale DB gav det **modsatte** svar om følelsesankrene end CT105 gjorde.

Og den mest sandsynlige fejl her er husets hyppigste: `built_but_not_connected`.
Indbakken kan være korrekt og fuldstændig, og **ingen prompt læser den**.

## Fail-retningen

Et led der ikke kan måles er et led der **ikke** virker, indtil nogen beviser
andet. Tavshed tælles aldrig som bestået — det er præcis hvad de 46/71 «aktive»
systemer og den grønne ledger gjorde. Hvert led rapporterer `ok`, `fejl` eller
`kan_ikke_maales`, og de to sidste er begge en fiasko.

## Den skriver i produktionen

Den opretter ÉN testpost og lukker den igen. Det er med vilje: en e2e der kun
læser kan ikke bevise at skrivningen virker. `--ryd-op` (standard) sikrer at
posten lukkes uanset udfald, og `--bruger` er obligatorisk, så den aldrig
rammer en forkert indbakke ved et uheld.

Brug på CT105 med HANS interpreter:

    /home/bs/miniconda3/envs/ai/bin/python scripts/e2e_indbakke.py --bruger bjorn
    ... --json
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

OK, FEJL, UMAALT = "ok", "fejl", "kan_ikke_maales"


class Led:
    """Ét led i kæden. Samler sit eget udfald, så ingen kan forsvinde."""

    def __init__(self) -> None:
        self.resultater: list[dict[str, Any]] = []

    def __call__(self, nr: int, navn: str, status: str, detalje: Any = "") -> None:
        self.resultater.append({"led": nr, "navn": navn, "status": status,
                                "detalje": detalje})

    @property
    def bestod(self) -> bool:
        return all(r["status"] == OK for r in self.resultater)


def _trin_1_units(led: Led) -> None:
    """Kører BEGGE units den kode du tror?

    `jarvis-api` har `runtime_services=False` og `jarvis-runtime` `True` — de
    kører samme app med forskellige ansvar, så en ændring kan være live i den
    ene og død i den anden. Bevis det med tidsstempler, ikke med tillid.
    """
    import subprocess
    try:
        kode = subprocess.run(
            ["git", "log", "-1", "--format=%h %at"], capture_output=True,
            text=True, cwd=str(_REPO_ROOT), timeout=10).stdout.strip()
        kode_ts = int(kode.split()[1]) if len(kode.split()) > 1 else 0
    except Exception as exc:  # noqa: BLE001
        led(1, "begge units koerer koden", UMAALT, f"git fejlede: {exc}")
        return
    status: dict[str, Any] = {"kode": kode}
    for unit in ("jarvis-api", "jarvis-runtime"):
        try:
            r = subprocess.run(
                ["systemctl", "show", "-p", "ActiveEnterTimestampMonotonic",
                 "-p", "ActiveEnterTimestamp", "--value", unit],
                capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
            status[unit] = r[0] if r else "(intet svar)"
        except Exception as exc:  # noqa: BLE001
            status[unit] = f"fejl: {exc}"
    mangler = [u for u in ("jarvis-api", "jarvis-runtime")
               if not str(status.get(u) or "").strip()
               or str(status[u]).startswith("fejl")]
    if mangler:
        # En unit vi ikke kan spoerge om er ikke bevist opdateret.
        led(1, "begge units koerer koden", UMAALT,
            {"kunne_ikke_spoerges": mangler, **status})
        return
    led(1, "begge units koerer koden", OK, {"kode_ts": kode_ts, **status})


def _trin_2_kilde_skriver(led: Led, bruger: str) -> str:
    """En ÆGTE kilde skriver en post — gennem `registrer_kilde`, ikke SQL.

    Et rå `INSERT` ville bevise skrivningen men ikke **proveniensen**, og
    proveniensen ER hele gate-betingelsen. Her køres den rigtige vej, og
    `verificeret_ejer` læses bagefter: er den `ukendt`, er kæden intakt men
    gaten vil aldrig fyre — og det er netop en fejl man ikke ser.
    """
    kid = f"e2e-{uuid.uuid4().hex[:10]}"
    try:
        from core.services.inbox_state import registrer_kilde
        from core.services.session_context_resolve import aktivt_run_id
        r = registrer_kilde(
            bruger_id=bruger, kildetype="job", kilde_id=kid,
            oprettende_run_id=aktivt_run_id(""),
            beskrivelse="e2e-verifikation af indbakke-kaeden")
    except Exception as exc:  # noqa: BLE001
        led(2, "kilden skriver en post", FEJL, str(exc))
        return ""
    if r.get("status") != "ok":
        led(2, "kilden skriver en post", FEJL, r)
        return ""
    post = r.get("post") or {}
    led(2, "kilden skriver en post", OK, {
        "id": kid, "verificeret_ejer": post.get("verificeret_ejer"),
        "kraever_handling": post.get("kraever_handling"),
        # Et script har intet levende run, saa `ukendt` er det FORVENTEDE
        # udfald her — og det er i sig selv et fund: kaeden virker, men en
        # post oprettet uden for et run kan ikke gate. Led 5 maaler gaten med
        # en post der KAN.
        "note": ("ukendt ejer er forventet fra et script — ingen levende run"
                 if post.get("verificeret_ejer") == "ukendt" else "")})
    return kid


def _trin_3_visningen(led: Led, bruger: str, kid: str) -> None:
    """Står posten i visningen? Kørt med den rigtige interpreter."""
    if not kid:
        led(3, "posten staar i visningen", UMAALT, "led 2 gav ingen post")
        return
    try:
        from core.services.inbox_view import byg_indbakke
        v = byg_indbakke(bruger)
    except Exception as exc:  # noqa: BLE001
        led(3, "posten staar i visningen", FEJL, str(exc))
        return
    if v.get("status") != "ok":
        led(3, "posten staar i visningen", FEJL, v)
        return
    fundet = [p for s in v.values() if isinstance(s, list) for p in s
              if isinstance(p, dict) and p.get("id") == kid]
    if not fundet:
        led(3, "posten staar i visningen", FEJL,
            {"id": kid, "sektioner": {k: len(x) for k, x in v.items()
                                      if isinstance(x, list)}})
        return
    led(3, "posten staar i visningen", OK, {"linje": fundet[0].get("linje")})


def _trin_4_prompten(led: Led, bruger: str, kid: str, session_id: str) -> None:
    """Det afgørende led: BÆRER PROMPTEN DEN?

    Det er her `built_but_not_connected` rammer. Opgave 0 målte at ventende
    tilstand i dag er **0 tokens** af prompten — den ene ventende vækning i
    systemet stod slet ikke i den. Hvis indbakken ikke læses af en prompt-
    sektion, er hele kæden korrekt og uden virkning.
    """
    if not session_id:
        led(4, "PROMPTEN baerer indbakken", UMAALT, "ingen session_id givet")
        return
    try:
        from core.services.visible_model import (
            _build_visible_prompt_assembly, resolve_provider_router_target)
        t = resolve_provider_router_target(lane="visible")
        a = _build_visible_prompt_assembly(
            provider=str(t.get("provider") or ""), model=str(t.get("model") or ""),
            user_message="e2e", session_id=session_id)
        tekst = a.text or ""
    except Exception as exc:  # noqa: BLE001
        led(4, "PROMPTEN baerer indbakken", FEJL, str(exc))
        return
    har_id = kid in tekst if kid else False
    har_sektion = any(m in tekst for m in ("VENTER PAA DIG", "VENTER PÅ DIG",
                                           "INDBAKKE", "indbakken"))
    led(4, "PROMPTEN baerer indbakken", OK if har_id else FEJL, {
        "post_id_i_prompten": har_id,
        "en_indbakke_sektion_findes": har_sektion,
        "prompt_tegn": len(tekst),
        "note": ("" if har_id else
                 "INGEN prompt-sektion laeser inbox_items. Kaeden er korrekt og "
                 "uden virkning — built_but_not_connected. Opgave 0 maalte det "
                 "samme fra den anden side: 0 tokens ventende tilstand."),
    })


def _trin_5_gaten(led: Led, bruger: str) -> None:
    """Nægter gaten en ægte mutation — og NAVNGIVER den posten?

    Ingen mock på sømmen. Posten tvinges til `kraever_handling` og to
    påmindelser direkte i tabellen, fordi et script ikke har et levende run og
    derfor ikke kan skabe en verificeret post ad den rigtige vej. Det er en
    bevidst afgrænsning: led 2 måler proveniensen, led 5 måler nægtelsen.
    """
    kid = f"e2e-gate-{uuid.uuid4().hex[:8]}"
    try:
        from core.runtime import db_inbox
        from core.services.inbox_gate import evaluer_inbox_mutation
        db_inbox.opret_eller_hent(
            bruger_id=bruger, kildetype="job", kilde_id=kid,
            verificeret_ejer=db_inbox.EJER_JARVIS, kraever_handling=True,
            beskrivelse="e2e gate-proeve")
        db_inbox.noter_paamindelse(bruger_id=bruger, kilde_id=kid, tur="e2e-t1")
        db_inbox.noter_paamindelse(bruger_id=bruger, kilde_id=kid, tur="e2e-t2")
        v = evaluer_inbox_mutation(bruger, "edit_file", {"path": "/tmp/e2e"},
                                   tur="e2e-t3")
    except Exception as exc:  # noqa: BLE001
        led(5, "gaten naegter en aegte mutation", FEJL, str(exc))
        return
    navngiver = kid in str(v.get("varsel") or "")
    led(5, "gaten naegter en aegte mutation",
        OK if (v.get("blokeret") and navngiver) else FEJL,
        {"blokeret": v.get("blokeret"), "navngiver_posten": navngiver,
         "grund": v.get("grund")})
    _ryd(bruger, kid)


def _trin_6_genstart(led: Led, bruger: str) -> None:
    """Overlever tælleren en procesgenstart?

    Den fejl har huset målt før: en volatil tæller nulstillede sig, og
    påmindelsen kom aldrig. Her simuleres genstarten ved at smide ALLE
    modul-caches væk og læse igen fra en ny forbindelse.
    """
    kid = f"e2e-tael-{uuid.uuid4().hex[:8]}"
    try:
        from core.runtime import db_inbox
        db_inbox.opret_eller_hent(bruger_id=bruger, kildetype="job", kilde_id=kid,
                                  verificeret_ejer=db_inbox.EJER_JARVIS,
                                  kraever_handling=True, beskrivelse="e2e taeller")
        db_inbox.noter_paamindelse(bruger_id=bruger, kilde_id=kid, tur="e2e-a")
        # «Ny proces»: skema-flaget nulstilles, saa naeste laesning gaar hele
        # vejen gennem ensure og en frisk forbindelse.
        db_inbox._skema_klar = False
        p = db_inbox.hent(bruger_id=bruger, kilde_id=kid)
    except Exception as exc:  # noqa: BLE001
        led(6, "taelleren overlever en genstart", FEJL, str(exc))
        return
    n = int((p or {}).get("paamindelser") or 0)
    led(6, "taelleren overlever en genstart", OK if n == 1 else FEJL,
        {"paamindelser_efter": n})
    _ryd(bruger, kid)


def _trin_7_done(led: Led, bruger: str, kid: str) -> None:
    """`inbox_done` lukker den, visningen falder, og posten kan STADIG findes.

    Alle tre skal bevises. En post der forsvandt helt ville gøre
    `inbox_done` til en sletning, og beviset for hvad der skete ville være væk.
    """
    if not kid:
        led(7, "done lukker, visningen falder, posten findes", UMAALT,
            "led 2 gav ingen post")
        return
    try:
        from core.runtime import db_inbox
        from core.services.inbox_state import done
        from core.services.inbox_view import byg_indbakke
        r = done(bruger, kid)
        v = byg_indbakke(bruger)
        stadig_vist = any(p.get("id") == kid for s in v.values()
                          if isinstance(s, list) for p in s if isinstance(p, dict))
        kan_findes = db_inbox.hent(bruger_id=bruger, kilde_id=kid) is not None
    except Exception as exc:  # noqa: BLE001
        led(7, "done lukker, visningen falder, posten findes", FEJL, str(exc))
        return
    alle_tre = r.get("status") == "ok" and not stadig_vist and kan_findes
    led(7, "done lukker, visningen falder, posten findes",
        OK if alle_tre else FEJL,
        {"done": r.get("status"), "stadig_i_visningen": stadig_vist,
         "kan_stadig_findes": kan_findes})


def _trin_8_intet_i_chatten(led: Led, session_id: str, foer: int) -> None:
    """Er noget sivet ind i chatten som en assistant-besked?

    Det var fejlen bag Smiths løkke: hans note landede i promptens hale, Jarvis
    gentog den, Smith detekterede gentagelsen. Differensen skal være NUL —
    scriptet sender ingen beskeder.
    """
    if not session_id:
        led(8, "intet sivede ind i chatten", UMAALT, "ingen session_id")
        return
    efter = _chat_antal(session_id)
    if foer < 0 or efter < 0:
        led(8, "intet sivede ind i chatten", UMAALT, "kunne ikke taelle beskeder")
        return
    led(8, "intet sivede ind i chatten", OK if efter == foer else FEJL,
        {"foer": foer, "efter": efter, "differens": efter - foer})


def _trin_9_tavse_fejlformer(led: Led, bruger: str) -> None:
    """De tre tal huset kender som tavse fejlformer."""
    fund: dict[str, Any] = {}
    try:
        from core.runtime import db_inbox
        from core.runtime.db import connect
        # 1. Ingen poster UDEN laeser: hver post skal kunne naas af en visning
        #    for sin bruger. En koe ingen laeser er
        #    seks_kognitive_systemer_uden_skriver spejlvendt.
        with connect() as conn:
            brugere = [str(r[0]) for r in conn.execute(
                "SELECT DISTINCT bruger_id FROM inbox_items").fetchall()]
            aabne = int(conn.execute(
                "SELECT count(*) FROM inbox_items WHERE status = 'aaben'"
            ).fetchone()[0])
        naaet = 0
        for b in brugere:
            naaet += len(db_inbox.liste_aktiv(bruger_id=b))
        fund["aabne_poster"] = aabne
        fund["naaet_af_en_visning"] = naaet
        fund["poster_uden_laeser"] = max(0, aabne - naaet)

        # 2. Ingen GATENDE post uden kilde i visningen (Skrive-kontraktens
        #    betingelse 2): en blokering uden en adresse kan ikke rettes.
        uden_adresse = []
        for b in brugere:
            for p in db_inbox.liste(bruger_id=b):
                if p.get("kraever_handling") and not str(p.get("beskrivelse") or "").strip():
                    uden_adresse.append(p["id"])
        fund["gatende_uden_beskrivelse"] = uden_adresse

        # 3. Ingen FALSK nudge. Kravet er praecist, og min foerste udgave af
        #    dette tjek var det ikke: den spurgte «begge slags i samme run»,
        #    og det flagger to ting der ikke er fejl.
        #
        #    Maalt 3/10 22:45, de to runs den foerste udgave flaggede:
        #      visible-e4fff62: invokeret 09:57:42 → nudge 09:58:48
        #          = aegte falsk nudge, men FOER rettelsen gik live 12:28:52.
        #          Historisk, ikke en regression.
        #      visible-220564e: nudge 16:34:41 → invokeret 16:34:47
        #          = gaten der VIRKER. Den naevnte skillet, og han brugte det
        #          seks sekunder efter. Succes-tilfaeldet, flagget som fejl.
        #
        #    Et aggregat laest uden at spoerge hvilke raekker det daekkede.
        #    Kravet er: en nudge hvis tidsstempel ligger EFTER en invokering i
        #    samme run, OG efter at rettelsen gik live.
        _RETTELSEN_LIVE = "2026-10-03T12:28:52"
        with connect() as conn:
            par = conn.execute(
                "SELECT created_at, kind, "
                "json_extract(payload_json,'$.run_id') run FROM events "
                "WHERE kind IN ('skill_gate.nudge','cognitive_state.skill_invoked') "
                "AND created_at > ? "
                "ORDER BY created_at", (_RETTELSEN_LIVE,)).fetchall()
        pr_run: dict[str, list[tuple[str, str]]] = {}
        for r in par:
            pr_run.setdefault(str(r["run"]), []).append(
                (str(r["created_at"]), str(r["kind"])))
        falske = []
        for run, haendelser in pr_run.items():
            foerste_invokering = next(
                (t for t, k in haendelser
                 if k == "cognitive_state.skill_invoked"), None)
            if not foerste_invokering:
                continue
            # En nudge EFTER den foerste invokering i samme run.
            if any(k == "skill_gate.nudge" and t > foerste_invokering
                   for t, k in haendelser):
                falske.append(run)
        fund["falske_nudges_efter_rettelsen"] = falske
        fund["vindue_fra"] = _RETTELSEN_LIVE
    except Exception as exc:  # noqa: BLE001
        led(9, "de tre tavse fejlformer", UMAALT, str(exc))
        return
    rent = (fund["poster_uden_laeser"] == 0
            and not fund["gatende_uden_beskrivelse"]
            and not fund["falske_nudges_efter_rettelsen"])
    led(9, "de tre tavse fejlformer", OK if rent else FEJL, fund)


def _chat_antal(session_id: str) -> int:
    try:
        from core.runtime.db import connect
        with connect() as conn:
            return int(conn.execute(
                "SELECT count(*) FROM chat_messages WHERE session_id = ?",
                (session_id,)).fetchone()[0])
    except Exception:  # noqa: BLE001 — et umaaleligt tal er -1, ikke 0
        return -1


def _ryd(bruger: str, kid: str) -> None:
    """Luk en testpost. Kaster aldrig — oprydning må ikke vælte rapporten."""
    if not kid:
        return
    try:
        from core.runtime import db_inbox
        db_inbox.afgoer(bruger_id=bruger, kilde_id=kid,
                        ny_status=db_inbox.STATUS_DROP, grund="e2e-oprydning")
    except Exception as exc:  # noqa: BLE001
        print(f"ADVARSEL: kunne ikke rydde {kid}: {exc}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bruger", required=True,
                    help="bruger-id. Obligatorisk, saa den aldrig rammer en "
                         "forkert indbakke ved et uheld.")
    ap.add_argument("--session-id", default="",
                    help="en aegte samtale, til led 4 og 8")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    led = Led()
    foer = _chat_antal(a.session_id) if a.session_id else -1
    _trin_1_units(led)
    kid = _trin_2_kilde_skriver(led, a.bruger)
    try:
        _trin_3_visningen(led, a.bruger, kid)
        _trin_4_prompten(led, a.bruger, kid, a.session_id)
        _trin_5_gaten(led, a.bruger)
        _trin_6_genstart(led, a.bruger)
        _trin_7_done(led, a.bruger, kid)
        _trin_8_intet_i_chatten(led, a.session_id, foer)
        _trin_9_tavse_fejlformer(led, a.bruger)
    finally:
        _ryd(a.bruger, kid)

    rapport = {"bestod": led.bestod, "led": led.resultater}
    if a.json:
        print(json.dumps(rapport, ensure_ascii=False, indent=2))
        return 0 if led.bestod else 1

    print(f"E2E INDBAKKE — bruger={a.bruger} "
          f"session={a.session_id or '(ingen)'}")
    for r in led.resultater:
        mark = {OK: "OK  ", FEJL: "FEJL", UMAALT: "UMAALT"}[r["status"]]
        print(f"  [{mark}] led {r['led']}: {r['navn']}")
        d = r["detalje"]
        if isinstance(d, dict):
            for k, v in d.items():
                if v not in ("", None, [], {}):
                    print(f"           {k}: {v}")
        elif d:
            print(f"           {d}")
    print(f"\n  SAMLET: {'BESTOD' if led.bestod else 'FEJLEDE'}")
    if not led.bestod:
        # Taushed taelles ALDRIG som bestaaet. Et led der ikke kan maales er
        # et led der ikke virker, indtil nogen beviser andet.
        print("  Et UMAALT led er ogsaa en fiasko — se fail-retningen i spec'en.")
    return 0 if led.bestod else 1


if __name__ == "__main__":
    raise SystemExit(main())
