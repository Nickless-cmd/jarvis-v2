"""Det han selv har dannet skal nå ham — og kun når der er noget.

Kortlagt 2026-09-05: 68 af backendens 206 `/mc`-ruter blev aldrig rørt af noget
UI. En håndfuld af dem er ikke observation men materiale der burde forme hans
adfærd, og de producerede indhold hele tiden uden at nå hans prompt:

    /mc/regret            7 åbne, 0 løste — den tungeste med lektien
                          «Bruger afviste tool-call til bash»
    /mc/rupture-repair    3 åbne brud med Bjørn, 0 helede, 0 FORSØG
    /mc/formed-values     2 værdier han selv har dannet, én med overbevisning 1,0
    /mc/boundary-model    hans egen model af krop / hukommelse / bevidsthed
    /mc/user-mental-model 6 mønstre om Bjørn
"""

from __future__ import annotations

from core.services.prompt_sections import formative_state as F


def _stub(monkeypatch, **kilder):
    """Stub de fire kilder. Udeladte kilder returnerer tomt."""
    monkeypatch.setattr(
        "core.services.value_formation.build_formed_values_surface",
        lambda: kilder.get("values", {}),
    )
    monkeypatch.setattr(
        "core.services.boundary_awareness.build_boundary_awareness_surface",
        lambda: kilder.get("boundary", {}),
    )
    monkeypatch.setattr(
        "core.services.regret_engine.build_regret_engine_surface",
        lambda: kilder.get("regret", {}),
    )
    monkeypatch.setattr(
        "core.services.rupture_repair.build_rupture_repair_surface",
        lambda: kilder.get("rupture", {}),
    )
    monkeypatch.setattr(
        "core.services.user_theory_of_mind.build_user_theory_of_mind_surface",
        lambda: kilder.get("user", {}),
    )


# ---------------------------------------------------------------------------
# Tavshed når der intet er
# ---------------------------------------------------------------------------


def test_alle_kilder_tomme_giver_ingen_sektion(monkeypatch):
    _stub(monkeypatch)
    assert F.formative_state_section() == ""


def test_en_kastende_kilde_vaelter_ikke_de_andre(monkeypatch):
    _stub(monkeypatch, values={"values": [
        {"value_statement": "Grundighed før hastighed", "conviction": 0.9}]})
    monkeypatch.setattr(
        "core.services.regret_engine.build_regret_engine_surface",
        lambda: (_ for _ in ()).throw(RuntimeError("nede")),
    )
    ud = F.formative_state_section()
    assert "Grundighed før hastighed" in ud


# ---------------------------------------------------------------------------
# Indholdet
# ---------------------------------------------------------------------------


def test_vaerdier_staar_foerst_og_staerkeste_foerst(monkeypatch):
    """Værdier han selv har dannet er det stærkeste han har."""
    _stub(monkeypatch, values={"values": [
        {"value_statement": "Svag overbevisning", "conviction": 0.2},
        {"value_statement": "Stærk overbevisning", "conviction": 1.0},
    ]})
    ud = F.formative_state_section()
    linjer = ud.splitlines()
    assert linjer[1].startswith("Værdier du selv har dannet")
    assert ud.index("Stærk overbevisning") < ud.index("Svag overbevisning")
    assert "(1.00)" in ud


def test_uafsluttet_naevner_at_der_ingen_forsoeg_er(monkeypatch):
    """Tre uhelede brud med NUL forsøg er noget andet end tre der blev forsøgt."""
    _stub(
        monkeypatch,
        regret={"stats": {"open_count": 7, "top_open": {}}},
        rupture={"stats": {"open_count": 3, "repair_attempts": 0}},
    )
    ud = F.formative_state_section()
    assert "7 åbne anger" in ud
    assert "3 uhelede brud med Bjørn (ingen forsøg endnu)" in ud


def test_forsoeg_taelles_naar_der_ER_nogen(monkeypatch):
    _stub(monkeypatch, rupture={"stats": {"open_count": 2, "repair_attempts": 5}})
    assert "2 uhelede brud med Bjørn (5 forsøg)" in F.formative_state_section()


def test_lektien_fra_den_tungeste_anger_kommer_med(monkeypatch):
    """En anger uden lektie er ubehag; en anger MED lektie kan ændre en handling."""
    _stub(monkeypatch, regret={"stats": {
        "open_count": 7,
        "top_open": {"lesson": "Bruger afviste tool-call til bash"},
    }})
    ud = F.formative_state_section()
    assert "Bruger afviste tool-call til bash" in ud


def test_graenserne_gengives_paa_dansk(monkeypatch):
    _stub(monkeypatch, boundary={"model": {
        "body": "Maskinen — CPU, RAM, disk, netværk.",
        "memory": "Databasen + workspace-filer.",
        "consciousness": "Det der sker lige nu i denne kontekst.",
    }})
    ud = F.formative_state_section()
    for ord_ in ("krop:", "hukommelse:", "bevidsthed:"):
        assert ord_ in ud


def test_sektionen_er_kompakt(monkeypatch):
    """Én sektion, ikke otte — awareness-budgettet er 9000 tegn i alt."""
    _stub(
        monkeypatch,
        values={"values": [{"value_statement": "A" * 300, "conviction": 1.0},
                           {"value_statement": "B" * 300, "conviction": 0.9},
                           {"value_statement": "C" * 300, "conviction": 0.8}]},
        boundary={"model": {"body": "X" * 300, "memory": "Y" * 300,
                            "consciousness": "Z" * 300}},
        regret={"stats": {"open_count": 7, "top_open": {"lesson": "L" * 300}}},
        rupture={"stats": {"open_count": 3, "repair_attempts": 0}},
        user={"model": {"patterns": ["P" * 300, "Q" * 300, "R" * 300]}},
    )
    ud = F.formative_state_section()
    assert len(ud) < 900, "sektionen fylder %d tegn — for meget af budgettet" % len(ud)


def test_overfladen_rapporterer_hvad_der_er_med(monkeypatch):
    _stub(monkeypatch, values={"values": [
        {"value_statement": "Noget", "conviction": 0.5}]})
    flade = F.build_formative_state_surface()
    assert flade["active"] is True
    assert flade["has_values"] is True
    assert flade["has_unfinished"] is False
