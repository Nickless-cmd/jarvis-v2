"""Trin 4+5 i eskaleringstrappen (besluttet 5/11-2026).

Trin 4 = «hold op, men vent på et skift». Trin 5 = «vend tilbage ved
stemningsskift». Testene her skal kunne skelne ``venter`` fra ``dismissed`` —
en grøn test der ikke kan det beviser intet, fordi forskellen mellem at give op
og holde døren åben netop ER tilstanden.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import nudge_broend as nb


@pytest.fixture()
def broend(monkeypatch):
    """Isoleret brønd i hukommelsen — ingen fil, ingen dual-write."""
    lager: list[dict] = []
    monkeypatch.setattr(nb, "_load", lambda: [dict(n) for n in lager])
    monkeypatch.setattr(nb, "_save", lambda x: lager.__setitem__(slice(None), [dict(n) for n in x]))
    monkeypatch.setattr("core.services.outbound_nudges.push_nudge", lambda **kw: None)
    return lager


def _skift(*, kind: str = "mood_shift", alder_timer: float = 0.0) -> dict:
    """Et percept i den form sensory_perception_bridge faktisk returnerer."""
    obs = datetime.now(UTC) - timedelta(hours=alder_timer)
    return {
        "change_type": "sensory-change-atmosphere",
        "salience": "high",
        "summary": "atmosfære-ændring: stemning skiftet fra roligt til mørkt",
        "observed_at": obs.isoformat(),
        "evidence": {"change_kind": kind, "mood_tone_now": "mørkt"},
    }


def test_nudge_der_rammer_loftet_ender_i_venter_og_forsvinder_ikke(broend):
    nid = nb.push(source="opvask", message="opvasken fra i går står stadig", emne="opvask")
    assert nb.mark_sent(nid) is True

    nid2 = nb.push(source="opvask", message="opvasken fra i går står stadig", emne="opvask")
    assert nb.mark_venter(nid2) is True

    n = nb.get(nid2)
    assert n["status"] == nb.STATUS_VENTER
    assert n["status"] != "dismissed"          # den er IKKE opgivet
    # Prik tælles KUN ved afsendelse (rettet 5/11-2026). Denne nudge blev aldrig
    # sagt — den blev holdt tilbage. Tæller man hvile som en prik, ser den ud
    # som en gentagelse den ikke var, og kadence-loftet laaser sig selv.
    assert n["prik"] == 0
    assert n["trin"] == 4
    assert n["venter_siden"]
    # og den er ikke længere i den kø der bliver sagt
    assert nid2 not in [x["nudge_id"] for x in nb.list_pending()]
    # men den findes stadig som hvilende
    assert nid2 in [x["nudge_id"] for x in nb.list_ventende()]


def test_kadence_loftet_er_en_prik_pr_emne_pr_dag(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_sent(nid)

    assert nb.kadence_tillader("opvask") is False
    assert nb.kadence_tillader("noget-andet") is True

    om_25_timer = datetime.now(UTC) + timedelta(hours=25)
    assert nb.kadence_tillader("opvask", nu=om_25_timer) is True


def test_ventende_nudge_genoptages_ikke_uden_et_registreret_skift(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid)

    assert nb.genoptag_ved_skift(None) == []
    assert nb.genoptag_ved_skift({}) == []
    # et percept uden sanse-change-type er ikke et skift
    assert nb.genoptag_ved_skift({"change_type": "tool-error", "observed_at": datetime.now(UTC).isoformat()}) == []
    # og nudgen står stadig i venter — intet blev flyttet
    assert nb.get(nid)["status"] == nb.STATUS_VENTER


def test_ventende_nudge_genoptages_ved_stemningsskift_som_nyt_tilbud(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid)

    flyttet = nb.genoptag_ved_skift(_skift(kind="mood_shift"))

    assert [n["nudge_id"] for n in flyttet] == [nid]
    n = nb.get(nid)
    assert n["status"] == "pending"
    assert n["trin"] == 5
    assert n["genoptaget_ved"]["change_kind"] == "mood_shift"
    # det er et TILBUD, ikke en gentagelse af den gamle besked
    assert "Skal vi tage den nu" in n["tilbud"]
    assert n["tilbud"] != n["message"]


def test_for_gammelt_skift_genoptager_ikke(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid)

    assert nb.genoptag_ved_skift(_skift(alder_timer=24 * 7)) == []
    assert nb.get(nid)["status"] == nb.STATUS_VENTER


def test_genoptagelse_respekterer_kadence_loftet(broend):
    """Et skift er ikke en fribillet: er emnet nævnt inden for et døgn, venter det."""
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_sent(nid)          # sagt nu
    nid2 = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid2)

    assert nb.genoptag_ved_skift(_skift()) == []
    assert nb.get(nid2)["status"] == nb.STATUS_VENTER

    om_25_timer = datetime.now(UTC) + timedelta(hours=25)
    flyttet = nb.genoptag_ved_skift(_skift(), nu=om_25_timer)
    assert [n["nudge_id"] for n in flyttet] == [nid2]


def test_oprydning_kaster_ikke_hvilende_nudges_vaek(broend, monkeypatch):
    """En hvilende nudge er en åben dør — oprydning må ikke gøre trin 4 til tavshed."""
    monkeypatch.setattr(nb, "_MAX_NUDGES", 3)
    hvilende = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(hvilende)
    for i in range(5):
        nid = nb.push(source=f"k{i}", message=f"noget nyt {i}", emne=f"k{i}")
        nb.mark_sent(nid)

    ids = [n["nudge_id"] for n in broend]
    assert hvilende in ids
    assert nb.get(hvilende)["status"] == nb.STATUS_VENTER


def test_emne_nogle_udledes_naar_kalderen_ikke_giver_en(broend):
    nid = nb.push(source="freetheai_checkin", message="der er nyt indhold klar til dig")
    n = nb.get(nid)
    assert n["emne"].startswith("freetheai_checkin:")
    assert "indhold" in n["emne"]


# ── Kæden, ikke enkeltfunktionerne (punkt 8, 5/11-2026) ───────────────────────
#
# En test pr. funktion beviste tidligere at hver del virkede — og alligevel var
# trin 4+5 dekoration, fordi INGEN produktionssti kaldte dem. Testene nedenfor
# maaler sammenhaengen: at send-vaerktoejet faktisk haandhaever loftet, og at
# percept-laget faktisk genoptager.


def test_kaeden_send_til_venter_til_tilbud(broend, monkeypatch):
    """push → send (afvist af kadence) → venter → skift → pending trin 5.

    Dette er den kaede Bjorn bad om bevist: den gaar gennem det RIGTIGE
    vaerktoej (_exec_nudge_send), ikke gennem service-laget direkte.
    """
    from core.tools import nudge_broend_tools as tools

    sendt: list[dict] = []
    monkeypatch.setattr(
        "core.tools.simple_tools._exec_notify_user",
        lambda args: sendt.append(args) or {"status": "ok"},
    )

    # 1. Foerste prik paa emnet — den maa sendes.
    nid1 = nb.push(source="opvask", message="opvasken staar stadig", emne="opvask")
    foerste = tools._exec_nudge_send({"nudge_id": nid1})
    assert foerste["status"] == "ok"
    assert not foerste.get("venter")
    assert nb.get(nid1)["status"] == "sent"
    assert len(sendt) == 1

    # 2. Anden prik samme emne samme dag — den maa IKKE sendes.
    nid2 = nb.push(source="opvask", message="opvasken staar stadig", emne="opvask")
    anden = tools._exec_nudge_send({"nudge_id": nid2})

    assert anden["status"] == "ok"          # ikke en fejl: den blev holdt tilbage
    assert anden["venter"] is True
    assert len(sendt) == 1                  # INTET blev sendt anden gang
    n = nb.get(nid2)
    assert n["status"] == nb.STATUS_VENTER  # ikke dismissed, ikke sendt
    assert n["prik"] == 0                   # usagt = ingen prik
    assert n["venter_grund"] == "kadence-loft"

    # 3. Verden flytter sig (et doegn senere) — saa bliver det et tilbud.
    om_25_timer = datetime.now(UTC) + timedelta(hours=25)
    flyttet = nb.genoptag_ved_skift(_skift(), nu=om_25_timer)

    assert [x["nudge_id"] for x in flyttet] == [nid2]
    n = nb.get(nid2)
    assert n["status"] == "pending"
    assert n["trin"] == 5
    assert "Skal vi tage den nu" in n["tilbud"]
    assert n["genoptaget_ved"]["emne"] == "opvask"


def test_genoptagelse_giver_kun_et_tilbud_pr_skift(broend):
    """Trin 5 er et tilbud, ikke en maskinpistol.

    To emner hvilende + ét skift = ÉT genoptaget emne, ikke to.
    """
    a = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    b = nb.push(source="tandlaege", message="ring til tandlaegen", emne="tandlaege")
    nb.mark_venter(a)
    nb.mark_venter(b)

    flyttet = nb.genoptag_ved_skift(_skift())

    assert len(flyttet) == 1, "et skift maa kun give ét tilbud"
    genoptaget = flyttet[0]["nudge_id"]
    assert genoptaget in (a, b)
    den_anden = b if genoptaget == a else a
    assert nb.get(den_anden)["status"] == nb.STATUS_VENTER


def test_percept_linjen_genoptager_hvilende_nudge(broend, monkeypatch):
    """Percept-laget er den produktionssti der faktisk kalder trin 5.

    Uden denne kobling havde genoptag_ved_skift tests men ingen kalder — det var
    praecis defekten 5/11-2026.
    """
    from core.services import perceptual_event_engine as pee

    nid = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    nb.mark_venter(nid)
    # Kadence maa ikke blokere: emnet er aldrig sagt.
    assert nb.kadence_tillader("opvask") is True

    surface = {"prompt_events": [_skift()], "events": [_skift()]}
    pee._genoptag_ventende_paa_skift(surface)

    assert nb.get(nid)["status"] == "pending"
    assert nb.get(nid)["trin"] == 5


def test_percept_linjen_ignorerer_ikke_sanse_events(broend):
    """Et tool-error er ikke et skift — kun sensory-change-* genoptager."""
    from core.services import perceptual_event_engine as pee

    nid = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    nb.mark_venter(nid)

    pee._genoptag_ventende_paa_skift({
        "events": [{"change_type": "tool-error", "summary": "x",
                    "observed_at": datetime.now(UTC).isoformat(), "evidence": {}}],
    })

    assert nb.get(nid)["status"] == nb.STATUS_VENTER


def test_trin_4_og_5_har_produktionskaldere():
    """Vagten der fangede defekten: en funktion uden kalder er dekoration.

    Grep i kilden (ikke i tests) efter hver funktion. Fejler den her, er
    mekanismen bygget men ikke baaret — praecis den fejl der blev maalt 5/11.
    """
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    kilder = [
        p for p in (repo / "core").rglob("*.py")
        if p.name != "nudge_broend.py"
    ]
    tekst = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in kilder)

    for navn in ("mark_venter", "genoptag_ved_skift", "kadence_tillader"):
        assert navn in tekst, f"{navn} har ingen produktionskalder uden for nudge_broend.py"


def test_build_perception_surface_kalder_genoptagelsen(monkeypatch):
    """Koblingen: build_perception_surface SKAL gaa gennem wrapperen.

    Fejler denne, er _genoptag_ventende_paa_skift en funktion ingen kalder —
    praecis den defekt der blev maalt 5/11-2026 (tests groenne, nul kalder).
    """
    from core.services import perceptual_event_engine as pee

    kaldt: list[dict] = []
    monkeypatch.setattr(pee, "observe_recent_changes", lambda: None)
    monkeypatch.setattr(pee, "get_timed_runtime_surface", lambda navn, ttl, fn: fn())
    monkeypatch.setattr(pee, "_build_perception_surface_uncached", lambda *, limit: {"events": []})
    monkeypatch.setattr(pee, "_genoptag_ventende_paa_skift", lambda s: kaldt.append(s))

    pee.build_perception_surface(limit=4)

    assert len(kaldt) == 1, "build_perception_surface gik uden om genoptagelsen"


# ── Trin 0-3: grovheden er en funktion af historikken (5/11-2026) ────────────

def test_trin_for_stiger_med_historikken(broend):
    """0 = usagt, 1 = sagt én gang, 2 = sagt to eller ét døgn, 3 = tre eller tre døgn."""
    assert nb.trin_for("opvask") == 0

    nid = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    nb.mark_sent(nid)
    assert nb.trin_for("opvask") == 1

    nid2 = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    nb.mark_sent(nid2)
    assert nb.trin_for("opvask") == 2

    nid3 = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    nb.mark_sent(nid3)
    assert nb.trin_for("opvask") == 3


def test_trin_stiger_med_tiden_uden_nye_prik(broend):
    nid = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    nb.mark_sent(nid)

    om_1_dag = datetime.now(UTC) + timedelta(days=1, hours=1)
    assert nb.trin_for("opvask", nu=om_1_dag) == 2
    om_4_dage = datetime.now(UTC) + timedelta(days=4)
    assert nb.trin_for("opvask", nu=om_4_dage) == 3


def test_formuleringen_aendrer_form_ikke_indhold(broend):
    tekst = "opvasken staar stadig"

    assert nb.formuler_for_trin(0, tekst, "opvask") == ""      # trin 0 siger intet
    assert nb.formuler_for_trin(1, tekst, "opvask") == tekst   # i forbifarten
    trin2 = nb.formuler_for_trin(2, tekst, "opvask")
    assert tekst in trin2 and "stået der før" in trin2
    trin3 = nb.formuler_for_trin(3, tekst, "opvask")
    assert tekst in trin3 and "Skal vi gøre noget" in trin3


def test_send_vaerktoejet_bruger_trinnet(broend, monkeypatch):
    """Koblingen: send-vaerktoejet formulerer efter historikken.

    Uden dette kald er trin 0-3 endnu et felt uden baerer — praecis den fejl
    der blev maalt 5/11-2026.
    """
    from core.tools import nudge_broend_tools as tools

    sendt: list[dict] = []
    monkeypatch.setattr(
        "core.tools.simple_tools._exec_notify_user",
        lambda args: sendt.append(args) or {"status": "ok"},
    )

    # To gange sagt => tredje afsendelse skal vaere trin 3 (direkte).
    for _ in range(2):
        nid = nb.push(source="opvask", message="opvasken staar", emne="opvask")
        tools._exec_nudge_send({"nudge_id": nid})
    # kadence blokerer den tredje; flyt tiden ved at rydde «sent»-posterne
    # Fire dage tilbage: baade kadence-loftet (24 t) og trin 3 (3 dage) er entydige.
    for n in broend:
        if n.get("status") == "sent":
            n["sent_at"] = (datetime.now(UTC) - timedelta(days=4)).isoformat()

    nid3 = nb.push(source="opvask", message="opvasken staar", emne="opvask")
    tools._exec_nudge_send({"nudge_id": nid3})

    # Pointen er FORMEN, ikke antallet: beskeden er formuleret efter trinnet.
    # (Hvor mange der naar igennem afhaenger af kadence-loftet og testes separat.)
    assert sendt, "intet blev sendt"
    assert sendt[0]["content"] == "opvasken staar", "trin 1 skal vaere den raa besked"
    sidste = sendt[-1]["content"]
    assert "Skal vi gøre noget ved det nu?" in sidste or "Det har stået der før" in sidste, \
        f"formuleringen blev ikke anvendt: {sidste!r}"
