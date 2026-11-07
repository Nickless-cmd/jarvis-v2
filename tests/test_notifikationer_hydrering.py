# tests/test_notifikationer_hydrering.py
from __future__ import annotations


def test_godkendelse_afgjort_et_andet_sted_lukker_sig_selv(isolated_runtime, monkeypatch) -> None:
    """Godkender man paa telefonen, skal desk-feeden helbrede sig selv."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1",
            titel="Vil du tillade bash?")
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "approved"})

    assert h.feed("bjorn", er_owner=True) == []
    assert n.aabne("bjorn", er_owner=True) == []


def test_ventende_godkendelse_bliver_staaende_og_kan_afgoeres(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gammel titel")
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "pending", "tool_name": "bash_session"})
    # `feed()` afstemmer nu ogsaa (spec 2026-09-21). Denne test maaler KUN
    # hydreringen af raekken over — den forudsaetning var uudtalt foer
    # afstemningen fandtes, og skal vaere eksplicit nu: ingen ANDEN ventende
    # godkendelse for ejeren. Afstemningen laeser `alle_pending_for_owner`
    # (K2, 2026-09-22) — IKKE `pending_for_owner`, som stadig bruges andre
    # steder og derfor er urørt.
    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", lambda uid: [])

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["kan_afgoere"] is True
    # Ejeren er sandheden: titlen kommer fra ham, ikke fra den gemte kopi.
    assert "bash_session" in poster[0]["titel"]


def test_aktivt_kort_uden_status_faar_ikke_feedet_til_at_lukke_og_genaabne(isolated_runtime, monkeypatch) -> None:
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    import core.services.visible_runs as vr

    kort = {"owner_user_id": "bjorn", "tool_name": "bash_session",
            "session_id": "chat-1", "created_at": "2026-09-26T15:00:00+00:00"}
    monkeypatch.setattr(vr, "godkendelser_nu", lambda: {"a-1": kort})
    monkeypatch.setattr(vr, "_get_visible_approval_state",
                        lambda _aid: {**kort, "status": "pending"})
    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="Vil du tillade bash_session?")

    for _ in range(3):
        poster = h.feed("bjorn", er_owner=True)
        assert [p["id"] for p in poster] == [nid]
        assert poster[0]["kan_afgoere"] is True

    event_bus.flush()
    with connect() as conn:
        for kind in ("notifikation.klaret", "notifikation.genaabnet"):
            assert conn.execute("SELECT COUNT(*) FROM events WHERE kind=?", (kind,)).fetchone()[0] == 0


def test_afgjort_kort_i_filen_genaabner_ikke_lukket_post(isolated_runtime, monkeypatch) -> None:
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    import core.services.visible_runs as vr

    kort = {"owner_user_id": "bjorn", "tool_name": "bash_session",
            "session_id": "chat-1", "created_at": "2026-09-26T15:00:00+00:00"}
    monkeypatch.setattr(vr, "godkendelser_nu", lambda: {"a-1": kort})
    monkeypatch.setattr(vr, "_get_visible_approval_state",
                        lambda _aid: {**kort, "status": "approved"})
    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="Vil du tillade bash_session?")
    n.luk(nid, "godkendt")

    for _ in range(3):
        assert h.feed("bjorn", er_owner=True) == []

    event_bus.flush()
    with connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='notifikation.genaabnet'"
        ).fetchone()[0] == 0


def test_hydrering_der_fejler_lukker_IKKE_raekken(isolated_runtime, monkeypatch) -> None:
    """En utilgaengelig ejer maa ikke se ud som en klaret opgave.

    Denne udgave monkeypatcher `approval_runtime.state` DIREKTE til at kaste.
    Det sker aldrig i produktion siden `state()` selv fangede internt (roden
    til den fejl denne test skulle finde, men ikke gjorde). Den staar her som
    en grov konsistens-check paa hydreringens EGEN `except`-net, uafhaengigt
    af hvad der ligger under `state()`. `test_db_utilgaengelig_...` nedenfor
    er den der maaler den AEGTE soem.
    """
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gemt titel")

    def sprang(_aid):
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(approval_runtime, "state", sprang)
    # `feed()` afstemmer nu ogsaa (spec 2026-09-21). Denne test maaler KUN
    # hydreringen af raekken over — den forudsaetning var uudtalt foer
    # afstemningen fandtes, og skal vaere eksplicit nu: ingen ANDEN ventende
    # godkendelse for ejeren. Afstemningen laeser `alle_pending_for_owner`
    # (K2, 2026-09-22) — IKKE `pending_for_owner`, som stadig bruges andre
    # steder og derfor er urørt.
    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", lambda uid: [])

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["titel"] == "Gemt titel"
    assert poster[0]["foraeldet"] is True
    assert poster[0]["kan_afgoere"] is False
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_db_utilgaengelig_ved_hydrering_lukker_IKKE_raekken(isolated_runtime, monkeypatch) -> None:
    """Den AEGTE soem: DB-opslaget bag `approval_runtime.state()` fejler.

    `state()` har IKKE laengere sit eget `except Exception: return None` —
    fjernet fordi det gjorde en DB-fejl til den SAMME vaerdi som «kortet
    findes ikke», og lukkede raekken tavst (se
    docs/superpowers/specs/2026-09-21-notifikations-feed-design.md).

    Kortet laegges KUN i det DB-baarne lag (`_set_visible_approval_state`),
    ikke i `_PENDING_APPROVALS` — det tvinger `state()` til rent faktisk at
    ramme `_get_visible_approval_state()` -> `get_runtime_state_value()`,
    ligesom naar en anden proces har oprettet kortet.

    Monkeypatchen sidder paa `get_runtime_state_value` i modulet der rent
    faktisk KALDER navnet —
    `core.services.visible_runs_sections.run_control_state` — ikke i
    `core.runtime.db_core`, hvor navnet oprindeligt bor: en `from X import Y`
    kopierer referencen ved import, saa en monkeypatch paa `db_core` selv IKKE
    naar det kald der reelt sker (maalt: patchede `db_core` og saa kortet
    stadig blive fundet upaavirket).
    """
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    import core.services.visible_runs as VR
    from core.services.visible_runs_sections import run_control_state as rcs

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="Gemt titel")
    VR._set_visible_approval_state("a-1", {"status": "pending", "tool_name": "bash_session"})
    assert "a-1" not in VR._PENDING_APPROVALS

    def sprang(*_a, **_kw):
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(rcs, "get_runtime_state_value", sprang)

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["titel"] == "Gemt titel"
    assert poster[0]["foraeldet"] is True
    assert poster[0]["kan_afgoere"] is False
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_egen_raekke_er_sin_egen_sandhed(isolated_runtime) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="bjorn", slags="reminder", kilde="egen",
            titel="Husk mælk", tekst="Du bad mig minde dig om det i morges.")
    poster = h.feed("bjorn", er_owner=True)
    assert poster[0]["titel"] == "Husk mælk"
    assert poster[0]["kan_afgoere"] is False


def test_anden_brugers_raekke_naar_aldrig_owners_feed(isolated_runtime) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="mikkel", slags="reminder", kilde="egen", titel="Mikkels ting")
    assert h.feed("bjorn", er_owner=True) == []
    assert len(h.feed("mikkel", er_owner=False)) == 1


def test_tidligere_hydrerer_ikke(isolated_runtime, monkeypatch) -> None:
    """En afgjort raekke maa ikke slaa op hos ejeren — den ER svaret.

    Slog den op alligevel, ville en utilgaengelig ejer faa en KLARET post til
    at se foraeldet ud, og et svar der er givet ville kunne se ubesvaret ud.
    """
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    n.luk(nid, "godkendt")

    def maa_ikke_kaldes(aid):
        raise AssertionError("historikken maa ikke hydrere")

    monkeypatch.setattr(approval_runtime, "state", maa_ikke_kaldes)

    poster = h.tidligere("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["udfald_tekst"] == "Godkendt af dig"
    assert poster[0]["kan_afgoere"] is False


def test_ukendt_udfald_bliver_ikke_tavst(isolated_runtime) -> None:
    """Et nyt udfald skal kunne SES med det samme nogen skriver det — ikke
    skjules indtil nogen husker at opdatere tabellen. En tavs historik er
    vaerre end en upraecis en."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    n.luk(nid, "et-helt-nyt-udfald")

    assert h.tidligere("bjorn", er_owner=True)[0]["udfald_tekst"] == "Klaret"


def _indsæt_run(run_id: str, *, status: str = "completed", svar: str = "") -> None:
    """En raekke i `visible_runs` — ejeren et `run_done`-kort peger paa."""
    from core.runtime.db import connect
    from core.runtime.db_visible import ensure_visible_tables
    with connect() as conn:
        ensure_visible_tables(conn)
        conn.execute(
            "INSERT INTO visible_runs"
            " (run_id, lane, provider, model, status, finished_at, text_preview)"
            " VALUES (?,?,?,?,?,?,?)",
            (run_id, "primary", "deepseek", "m", status,
             "2026-09-26T07:00:00+00:00", svar))
        conn.commit()


def test_svar_for_run_henter_teksten_fra_ejeren(isolated_runtime) -> None:
    """Svaret bor i `visible_runs`, ikke i notifikations-raekken."""
    from core.services.visible_runs_sections.run_finalization import svar_for_run

    _indsæt_run("r-1", svar="Jeg byggede det, og her er hvad jeg fandt.")
    assert svar_for_run("r-1") == "Jeg byggede det, og her er hvad jeg fandt."


def test_svar_for_run_er_tom_for_ukendt_koersel(isolated_runtime) -> None:
    """Ukendt run giver "" — ikke en undtagelse. Forskellen mellem «kørslen
    svarede ikke» og «jeg kunne ikke spørge» skal kunne ses."""
    from core.services.visible_runs_sections.run_finalization import svar_for_run

    assert svar_for_run("findes-ikke") == ""


def test_run_done_baerer_svaret_ikke_kun_titlen(isolated_runtime, monkeypatch) -> None:
    """Kortet blev foedt med en titel og en TOM tekst, saa fladen kunne sige
    at der var et svar uden at vise det (Bjoern 26/9-2026)."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    _indsæt_run("r-1", svar="Her er hvad jeg gjorde.")
    n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-1",
            session_id="chat-aaa", titel="Svar klar i «hey..»")

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["titel"] == "Svar klar i «hey..»"
    assert poster[0]["tekst"] == "Her er hvad jeg gjorde."


def test_run_done_uden_svar_beholder_den_gemte_tekst(isolated_runtime) -> None:
    """En koersel kan ende uden at have skrevet noget. Et kort med en tom
    krop ser ud som en fejl — den gemte tekst staar derfor uaendret."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    _indsæt_run("r-2", svar="")
    n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-2",
            session_id="chat-aaa", titel="Svar klar i «hey..»", tekst="Gemt tekst")

    assert h.feed("bjorn", er_owner=True)[0]["tekst"] == "Gemt tekst"


def test_svar_fra_den_aktive_samtale_springes_over(isolated_runtime) -> None:
    """Man laeser dem allerede i vinduet ved siden af."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    _indsæt_run("r-1")
    _indsæt_run("r-2")
    n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-1",
            session_id="chat-her", titel="Svar klar i «her»")
    n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-2",
            session_id="chat-der", titel="Svar klar i «der»")

    poster = h.feed("bjorn", er_owner=True, aktiv_session="chat-her")
    assert [p["titel"] for p in poster] == ["Svar klar i «der»"]
    # Uden filtrering staar begge — det er den gamle adfaerd.
    assert len(h.feed("bjorn", er_owner=True)) == 2


def test_godkendelse_i_den_aktive_samtale_skjules_IKKE(isolated_runtime, monkeypatch) -> None:
    """Et svar er laesning, en godkendelse venter paa et svar. At skjule den
    ville betyde at man ikke kunne svare paa den flade man sidder i."""
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services import approval_runtime

    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", lambda uid: [])
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "pending", "tool_name": "bash"})
    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1",
            session_id="chat-her", titel="Vil du tillade bash?")

    poster = h.feed("bjorn", er_owner=True, aktiv_session="chat-her")
    assert len(poster) == 1
    assert poster[0]["kan_afgoere"] is True


# --- Foraeldede familier (maalt 7/11-2026) ---------------------------------
# Ingen kvitterer infra_security / session_inbox / reach_out / release. De
# stod aabne i op til 24 dage og blev loadet, JSON-parset og sendt til Desk
# ved HVER poll (hvert 8. sekund).

def _alder(nid: str, dage: int) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import connect
    ts = (datetime.now(UTC) - timedelta(days=dage)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET oprettet=? WHERE id=?", (ts, nid))
        conn.commit()


def _frisk_feed(h, monkeypatch):
    """Nulstil throttlen, saa feed() faktisk faar lov at lukke."""
    monkeypatch.setattr(h, "_sidst_foraeldet", None)
    return h.feed("bjorn", er_owner=True)


def test_feed_lukker_aldrende_stoejfamilier_men_ikke_friske(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import connect
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    gamle = {}
    for slags in ("infra_security", "session_inbox:genstart",
                 "session_inbox:proactivity-bridge"):
        gamle[slags] = n.opret(user_id="bjorn", slags=slags, kilde="egen",
                               ref=f"{slags}-gammel", titel=f"{slags} gammel")
        _alder(gamle[slags], 3)
    frisk = n.opret(user_id="bjorn", slags="infra_security", kilde="egen",
                    ref="infra-frisk", titel="frisk")

    poster = _frisk_feed(h, monkeypatch)

    assert [p["id"] for p in poster] == [frisk]
    # Intet gaar tabt: raekkerne ligger i historikken med udfald «foraeldet».
    with connect() as conn:
        udfald = {r[0]: (r[1], r[2]) for r in conn.execute(
            "SELECT id, klaret, udfald FROM notifikationer WHERE klaret IS NOT NULL")}
    assert set(udfald) == set(gamle.values())
    assert all(k is not None and u == "foraeldet" for k, u in udfald.values())
    assert {t["id"] for t in h.tidligere("bjorn", er_owner=True)} == set(gamle.values())


def test_reach_out_og_release_har_laengere_graense(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    tre = n.opret(user_id="bjorn", slags="reach_out", kilde="egen", ref="r3", titel="3 dage")
    otte = n.opret(user_id="bjorn", slags="reach_out", kilde="egen", ref="r8", titel="8 dage")
    rel = n.opret(user_id="bjorn", slags="release", kilde="egen", ref="v8", titel="release 8 dage")
    _alder(tre, 3)
    _alder(otte, 8)
    _alder(rel, 8)

    assert [p["id"] for p in _frisk_feed(h, monkeypatch)] == [tre]


def test_feed_lukker_aldrig_noget_der_kan_vaere_en_opgave(isolated_runtime, monkeypatch) -> None:
    """Godkendelser afgoeres hos ejeren; keymaker/reminder/approval_expired kan
    vaere noget nogen skal handle paa. Alder alene er ikke et skoen."""
    from core.services import approval_runtime
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", lambda uid: [])
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "pending", "tool_name": "bash"})
    ids = [
        n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="a"),
        n.opret(user_id="bjorn", slags="keymaker_key_pending", kilde="egen", ref="k", titel="k"),
        n.opret(user_id="bjorn", slags="reminder", kilde="egen", ref="rem", titel="rem"),
        n.opret(user_id="bjorn", slags="approval_expired", kilde="egen", ref="ae", titel="ae"),
    ]
    for nid in ids:
        _alder(nid, 30)

    assert {p["id"] for p in _frisk_feed(h, monkeypatch)} == set(ids)


def test_feed_throttler_lukningen_og_overlever_en_fejl(isolated_runtime, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    kald = []
    ægte = n.luk_foraeldede
    monkeypatch.setattr(n, "luk_foraeldede", lambda *a, **k: kald.append(1) or ægte(*a, **k))
    monkeypatch.setattr(h, "_sidst_foraeldet", None)

    h.feed("bjorn", er_owner=True)
    h.feed("bjorn", er_owner=True)
    assert kald == [1], "anden poll inden for intervallet maa ikke skrive"

    # En lukning der kaster maa ikke tomme feeden for det andet.
    frisk = n.opret(user_id="bjorn", slags="infra_security", kilde="egen",
                    ref="i-frisk", titel="frisk")
    def sprang(*_a, **_k):
        raise RuntimeError("db laast")
    monkeypatch.setattr(n, "luk_foraeldede", sprang)
    monkeypatch.setattr(h, "_sidst_foraeldet", None)
    assert [p["id"] for p in h.feed("bjorn", er_owner=True)] == [frisk]
