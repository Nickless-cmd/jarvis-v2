"""Workspace skal resolves per bruger — ikke hardcodes til ``default``.

MÅLT 2/11-2026 (GDPR-undersøgelsen side-f921bcaacd): syv prompt-byggende
kaldesteder sendte ``workspace_id="default"`` uanset hvem der talte.
``default`` er den DELTE workspace hvor uautentificerede webchat-brugere
historisk lander. Så længe feltet læses derfra, former den der lander i
``default`` Bjørns temperature-rationale og dream-bias — samme fejlform som
6/10-lækagen (``db_fts.py:216``).

Testen måler to ting, og de er ikke den samme:

1. **At den AKTUELLE workspace følger med ned i kaldet.** En test der kun
   læser kilden ville bestå af en streng-sammenligning og intet bevise om
   hvad der sker når to brugere taler i hver sin tur.
2. **At et medlem ser INTET af Bjørns felt** — heller ikke som et tomt
   fald-tilbage. Et fix der peger på ``bjorn`` men falder tilbage til
   ``default`` når rækken mangler, ville se rigtigt ud og lække videre.

Datamigreringen (``default`` → ``bjorn``) er en forudsætning for punkt 1:
uden den ville feltet blive tavst fordi rækkerne stadig ligger i ``default``.
"""

from __future__ import annotations

import pytest


# ── 1. Kaldestederne sender den aktuelle workspace ────────────────────────


def _fang_kald(monkeypatch, modul_sti: str, funktions_navn: str) -> list[str]:
    """Erstat en engine-funktion og optag hvilke workspace_id'er den får."""
    sette: list[str] = []

    def _fake(*, workspace_id: str, **_kw):
        sette.append(workspace_id)
        return ""

    monkeypatch.setattr(f"{modul_sti}.{funktions_navn}", _fake)
    return sette


def test_temperature_hint_foelger_den_aktuelle_workspace(monkeypatch):
    """`build_unconscious_temperature_hint` må ikke sende en konstant.

    RØD FØR FIXET: sender ``"default"`` uanset kontekst.
    """
    from core.identity.workspace_context import reset_context, set_context
    from core.services import unconscious_temperature_field as U

    sette = _fang_kald(
        monkeypatch,
        "core.services.user_temperature_engine",
        "format_temperature_field_for_heartbeat",
    )
    tok = set_context(workspace_name="michelle", user_id="999")
    try:
        U.build_unconscious_temperature_hint()
    finally:
        reset_context(tok)

    assert sette == ["michelle"], (
        "temperature-hinten læser stadig en fast workspace — et medlem ville "
        f"få Bjørns felt. Kaldet sendte: {sette}"
    )


def test_temperature_surface_foelger_den_aktuelle_workspace(monkeypatch):
    from core.identity.workspace_context import reset_context, set_context
    from core.services import unconscious_temperature_field as U

    sette = _fang_kald(
        monkeypatch,
        "core.services.user_temperature_engine",
        "get_active_field_surface",
    )
    tok = set_context(workspace_name="mikkel", user_id="888")
    try:
        U.build_unconscious_temperature_field_surface()
    finally:
        reset_context(tok)

    assert sette == ["mikkel"], f"surface-kaldet sendte: {sette}"


def test_dream_bias_i_self_review_foelger_den_aktuelle_workspace(monkeypatch):
    from core.identity.workspace_context import reset_context, set_context
    from core.services import self_review_outcome_tracking as S

    sette = _fang_kald(
        monkeypatch, "core.services.dream_bias_engine", "get_active_dream_bias"
    )
    tok = set_context(workspace_name="michelle", user_id="999")
    try:
        S.build_runtime_self_review_outcome_surface(limit=8)
    finally:
        reset_context(tok)

    assert sette and set(sette) == {"michelle"}, (
        f"self-review-dream-bias sendte: {sette} — ingen af kaldene maa vaere default"
    )


def test_ingen_hardkodet_default_workspace_i_core():
    """Klasse-vagt: hele fejlformen, ikke ét kaldested ad gangen.

    Syv steder sendte den samme konstant. Retter man kun dem man husker,
    vender fejlen tilbage ved næste prompt-felt nogen bygger. Vagten måler
    derfor på KLASSEN: der må ikke stå ``workspace_id="default"`` nogen
    steder i ``core/``.

    ``"default"`` er stadig en gyldig DEFAULT-VÆRDI i en funktionssignatur
    (den rammes kun hvis kalderen tier). Det er KALDEREN der er fejlen, og
    det er kalderen denne vagt fanger: ``workspace_id="default"`` skrevet
    ind som argument.
    """
    import pathlib
    import re

    rod = pathlib.Path(__file__).resolve().parents[1] / "core"
    moenster = re.compile(r'workspace_id\s*=\s*"default"')
    fund: list[str] = []
    for fil in rod.rglob("*.py"):
        if "__pycache__" in fil.parts:
            continue
        for nr, linje in enumerate(fil.read_text(encoding="utf-8").splitlines(), 1):
            if moenster.search(linje):
                fund.append(f"{fil.relative_to(rod.parent)}:{nr}: {linje.strip()}")

    assert fund == [], (
        "hardkodet default-workspace i prompt-kæden — den der lander i "
        "'default' former Bjørns felt:\n" + "\n".join(fund)
    )


# ── 2. Et medlem ser intet af Bjørns felt ────────────────────────────────


def test_medlem_ser_ikke_bjorns_temperature_felt(isolated_runtime):
    """Den ægte adfærd: to brugere, to felter — ingen deling.

    Bjørn har en række under ``bjorn``. Michelle har ingen. Hendes kald må
    returnere TOMT, ikke Bjørns tal.
    """
    from core.identity.workspace_context import reset_context, set_context
    from core.runtime.db import connect
    from core.services.user_temperature_engine import get_active_field

    with connect() as c:
        c.execute(
            """INSERT INTO user_temperature_active
               (field_id, workspace_id, field_valens, field_arousal,
                field_texture, field_intensity, field_conflict,
                last_structural_at, last_llm_at, baseline_built_at,
                created_at, updated_at)
               VALUES ('tf_test_bjorn', 'bjorn', 0.9, 0.9, 'warm', 1.0, 0,
                       '2026-11-02T12:00:00Z', '2026-11-02T12:00:00Z',
                       '2026-11-02T12:00:00Z', '2026-11-02T12:00:00Z',
                       '2026-11-02T12:00:00Z')"""
        )
        c.commit()

    tok = set_context(workspace_name="michelle", user_id="999")
    try:
        felt = get_active_field(workspace_id=_ws())
    finally:
        reset_context(tok)

    assert felt is None, (
        "et medlem uden eget felt fik alligevel et felt — det er Bjørns data. "
        f"Feltet siger: {felt}"
    )


def test_bjorn_ser_sit_eget_felt(isolated_runtime):
    """Modstykket: fixet må ikke gøre feltet tavst for den det tilhører."""
    from core.identity.workspace_context import reset_context, set_context
    from core.runtime.db import connect
    from core.services.user_temperature_engine import get_active_field

    with connect() as c:
        c.execute(
            """INSERT INTO user_temperature_active
               (field_id, workspace_id, field_valens, field_arousal,
                field_texture, field_intensity, field_conflict,
                last_structural_at, last_llm_at, baseline_built_at,
                created_at, updated_at)
               VALUES ('tf_test_bjorn', 'bjorn', 0.9, 0.9, 'warm', 1.0, 0,
                       '2026-11-02T12:00:00Z', '2026-11-02T12:00:00Z',
                       '2026-11-02T12:00:00Z', '2026-11-02T12:00:00Z',
                       '2026-11-02T12:00:00Z')"""
        )
        c.commit()

    tok = set_context(workspace_name="bjorn")
    try:
        felt = get_active_field(workspace_id=_ws())
    finally:
        reset_context(tok)

    assert felt is not None, "Bjørns eget felt forsvandt — fixet gjorde funktionen tavs"
    assert felt["workspace_id"] == "bjorn"


def _ws() -> str:
    """Den workspace kaldestedet SKAL bruge — den aktuelle, ikke en konstant."""
    from core.identity.workspace_context import current_workspace_name

    return current_workspace_name()


# ── 3. Migreringen der gør fixet sikkert ─────────────────────────────────


def test_migreringen_flytter_default_til_bjorn(isolated_runtime):
    """Uden migreringen bliver feltet TAVST — det er den fælde fixet åbner.

    Målt 2/11-2026: alle syv per-workspace-tabeller havde data under
    ``default`` og nul under ``bjorn``, mens resolveren returnerer ``bjorn``.
    Fixet i kaldestederne alene ville derfor gøre ``get_active_field`` tom
    for den bruger der EJER data. Migreringen er ikke kosmetik.
    """
    from core.runtime.db import connect
    from core.runtime.db_schema import _migrate_default_workspace_to_bjorn

    with connect() as c:
        c.execute(
            """INSERT INTO user_temperature_active
               (field_id, workspace_id, field_valens, field_arousal,
                field_texture, field_intensity, field_conflict,
                last_structural_at, last_llm_at, baseline_built_at,
                created_at, updated_at)
               VALUES ('tf_migr', 'default', 0.5, 0.5, 'warm', 0.8, 0,
                       '2026-11-02T12:00:00Z', '2026-11-02T12:00:00Z',
                       '2026-11-02T12:00:00Z', '2026-11-02T12:00:00Z',
                       '2026-11-02T12:00:00Z')"""
        )
        c.commit()
        _migrate_default_workspace_to_bjorn(c)
        c.commit()
        ws = c.execute(
            "SELECT workspace_id FROM user_temperature_active WHERE field_id='tf_migr'"
        ).fetchone()[0]

    assert ws == "bjorn", f"migreringen efterlod rækken under {ws!r}"


def test_migreringen_er_idempotent_og_overskriver_ikke_nyere_data(isolated_runtime):
    """Kører den to gange, må den ikke række en række der allerede er flyttet —
    og den må ALDRIG flette en gammel ``default``-række ind i en tabel der
    allerede har en ``bjorn``-række. Ellers kunne en gendannet backup rulle
    brugerens nyeste felt tilbage.

    MÅLEFÆLDE DER KOSTEDE EN RUNDE: første udgave brugte
    ``user_temperature_active``, som har ``workspace_id ... UNIQUE``. Uden
    ``har_bjorn``-tjekket fejler UPDATE'en på den constraint, min ``except``
    sluger den — og testen bestod alligevel. Den målte constraint'en, ikke
    migreringen. ``counterfactuals`` har ingen UNIQUE på workspace_id, så
    grenen kan faktisk testes.
    """
    from core.runtime.db import connect
    from core.runtime.db_schema import _migrate_default_workspace_to_bjorn

    def _indsæt(c, cf_id: str, cf_key: str, ws: str) -> None:
        c.execute(
            """INSERT INTO counterfactuals
               (cf_id, cf_key, workspace_id, cluster_id, trigger_event_ids_json,
                trigger_types_json, what_if, status, created_at, updated_at)
               VALUES (?, ?, ?, 'c1', '[]', '[]', 'hvad nu hvis', 'pending',
                       '2026-11-02T12:00:00Z', '2026-11-02T12:00:00Z')""",
            (cf_id, cf_key, ws),
        )

    with connect() as c:
        _indsæt(c, "cf_ny", "noegle_ny", "bjorn")
        _indsæt(c, "cf_gammel", "noegle_gammel", "default")
        c.commit()

        _migrate_default_workspace_to_bjorn(c)
        c.commit()
        _migrate_default_workspace_to_bjorn(c)  # anden kørsel
        c.commit()

        raekker = dict(
            c.execute("SELECT cf_id, workspace_id FROM counterfactuals").fetchall()
        )

    assert raekker["cf_ny"] == "bjorn", "den nyeste række blev flyttet eller ændret"
    assert raekker["cf_gammel"] == "default", (
        "en gammel default-række blev flettet ind i en tabel der allerede havde "
        "en bjorn-række — det kan overskrive nyere data"
    )
