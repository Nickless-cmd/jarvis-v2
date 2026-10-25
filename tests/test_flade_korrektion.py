"""Korrektionsrunden: en defekt flade rettes FØR den vises.

Målt 25/10-2026 (Bjørn): «disse fejler stadig … kan vi ikke sørge for hvis
formatet ikke er korrekt, afvises den inden den vises og du kan korrigere og
lave den der virker? istedet for runden skal slutte og så skal jeg bede dig
lave en ny … det er præcis sådan nogen fejl en bruger ikke må opleve.»

Testene her værner fire ting, og de er ikke lige vigtige:

1. En defekt blok bliver faktisk rettet (det er formålet).
2. Et svar UDEN fejl bliver ikke sendt gennem et model-kald (det ville koste
   latency på hvert eneste svar).
3. En korrektion der ikke hjælper bliver FORKASTET — den må ikke erstatte et
   svar med en anden fejl.
4. Et svar der mister sin prosa bliver forkastet. Prosaen er allerede vist.
"""

from __future__ import annotations

from core.services.flade_korrektion import korriger_flader
from core.services.visible_followup_events import (
    FollowupDelta,
    FollowupDone,
    FollowupFailed,
)


def _fake_stream(svar: str, *, fejl: bool = False):
    """En stream_followup der svarer med ``svar`` uden netværk."""

    def _stream(**_kwargs):
        if fejl:
            yield FollowupFailed(round_index=0, error="netværk nede")
            return
        yield FollowupDelta(delta=svar)
        yield FollowupDone(text=svar)

    return _stream


def _kald(tekst: str, fejlliste: list[str], svar: str, **kwargs) -> str:
    return korriger_flader(
        tekst,
        fejlliste,
        stream_followup=_fake_stream(svar, **kwargs),
        provider="test",
        model="test",
        base_messages=[],
    )


# ── 1. Den retter en defekt blok ────────────────────────────────────────────

def test_defekt_timeline_bliver_rettet() -> None:
    """En timeline uden ``title`` på et item forsvinder i rendereren. Den skal rettes."""
    defekt = (
        "Her er forløbet.\n\n"
        "```jarvis-ui\n"
        '{"type":"timeline","title":"Forløb","items":[{"time":"09:21","detail":"x"}]}\n'
        "```\n"
    )
    rettet = (
        "Her er forløbet.\n\n"
        "```jarvis-ui\n"
        '{"type":"timeline","title":"Forløb","items":[{"time":"09:21","title":"Start","detail":"x"}]}\n'
        "```\n"
    )
    ud = _kald(defekt, ["timeline: timeline item 0 mangler title"], rettet)
    assert ud == rettet.strip()
    assert '"title":"Start"' in ud


def test_uoprettelig_json_bliver_rettet() -> None:
    """``],"}"`` er den målte fejl fra 220068 — den skal kunne reddes."""
    defekt = (
        "Se her.\n\n"
        "```jarvis-ui\n"
        '{"type":"callout","tone":"info","title":"T","body":"B"],"}\n'
        "```\n"
    )
    rettet = (
        "Se her.\n\n"
        "```jarvis-ui\n"
        '{"type":"callout","tone":"info","title":"T","body":"B"}\n'
        "```\n"
    )
    ud = _kald(defekt, ["blokken kan ikke parses: Expecting ':' delimiter"], rettet)
    assert ud == rettet.strip()


# ── 2. Intet kald når der ikke er fejl ──────────────────────────────────────

def test_ingen_fejl_giver_intet_kald() -> None:
    """Et svar uden defekte flader må ikke koste et model-kald."""
    kaldt = {"n": 0}

    def _stream(**_kwargs):
        kaldt["n"] += 1
        yield FollowupDone(text="skulle ikke ske")

    tekst = "Ren prosa uden flader."
    ud = korriger_flader(
        tekst, [], stream_followup=_stream,
        provider="test", model="test", base_messages=[],
    )
    assert ud == tekst
    assert kaldt["n"] == 0


def test_tom_tekst_giver_intet_kald() -> None:
    kaldt = {"n": 0}

    def _stream(**_kwargs):
        kaldt["n"] += 1
        yield FollowupDone(text="x")

    assert korriger_flader(
        "", ["en fejl"], stream_followup=_stream,
        provider="test", model="test", base_messages=[],
    ) == ""
    assert kaldt["n"] == 0


# ── 3. En dårlig korrektion forkastes ───────────────────────────────────────

def test_korrektion_der_stadig_har_fejl_forkastes() -> None:
    """En «rettelse» der bare er en anden fejl må ikke erstatte svaret."""
    defekt = (
        "Prosa her som brugeren allerede har læst, og den skal blive stående.\n\n"
        "```jarvis-ui\n"
        '{"type":"timeline","title":"T","items":[{"time":"09:21","detail":"x"}]}\n'
        "```\n"
    )
    lige_saa_defekt = (
        "Prosa her som brugeren allerede har læst, og den skal blive stående.\n\n"
        "```jarvis-ui\n"
        '{"type":"timeline","title":"T","items":[{"time":"09:21","detail":"stadig uden title"}]}\n'
        "```\n"
    )
    ud = _kald(defekt, ["timeline: item 0 mangler title"], lige_saa_defekt)
    assert ud == defekt, "en korrektion med samme fejl skal forkastes"


def test_netvaerksfejl_giver_oprindelig_tekst() -> None:
    defekt = "Prosa.\n\n```jarvis-ui\n{\"type\":\"timeline\",\"items\":[]}\n```\n"
    ud = _kald(defekt, ["timeline har ingen brugbare items"], "", fejl=True)
    assert ud == defekt


def test_tomt_svar_giver_oprindelig_tekst() -> None:
    defekt = "Prosa.\n\n```jarvis-ui\n{\"type\":\"timeline\",\"items\":[]}\n```\n"
    ud = _kald(defekt, ["timeline har ingen brugbare items"], "")
    assert ud == defekt


# ── 4. Prosaen må ikke forsvinde ────────────────────────────────────────────

def test_svar_uden_flade_forkastes() -> None:
    """Svarer modellen kun prosa, har den fjernet fladen — det er ikke en rettelse."""
    defekt = (
        "Lang prosa her som brugeren har læst, og som skal bevares i sin helhed.\n\n"
        "```jarvis-ui\n"
        '{"type":"timeline","title":"T","items":[{"time":"09:21","detail":"x"}]}\n'
        "```\n"
    )
    kun_prosa = "Lang prosa her som brugeren har læst, og som skal bevares i sin helhed."
    ud = _kald(defekt, ["timeline: item 0 mangler title"], kun_prosa)
    assert ud == defekt


def test_alt_for_kort_svar_forkastes() -> None:
    """Et svar der er skåret ned til en brøkdel er ikke det samme svar."""
    defekt = (
        "Meget lang prosa. " * 40
        + "\n\n```jarvis-ui\n"
        '{"type":"timeline","title":"T","items":[{"time":"09:21","detail":"x"}]}\n'
        "```\n"
    )
    stub = "```jarvis-ui\n{\"type\":\"timeline\",\"title\":\"T\",\"items\":[{\"title\":\"A\"}]}\n```"
    ud = _kald(defekt, ["timeline: item 0 mangler title"], stub)
    assert ud == defekt


# ── 5. Vinduet: et langt svar sendes ikke i sin helhed ──────────────────────

def test_langt_svar_sendes_som_vindue() -> None:
    """Et 20.000-tegns svar med én skæv blok skal ikke koste et helt nyt svar."""
    from core.services.flade_korrektion import _blok_vinduer

    lang = ("Fyldtekst. " * 2000) + "\n\n```jarvis-ui\n{\"type\":\"callout\"}\n```\n"
    vindue = _blok_vinduer(lang)
    assert len(vindue) <= 6000
    assert "```jarvis-ui" in vindue


# ── 6. Mekanisk reparation: hegn koster intet model-kald ────────────────────
# Målt 25/10-2026 (Bjørn: «disse fejler stadig»): den bar form — `jarvis-ui {…}`
# uden ```-hegn — er den der oftest rammer brugeren. Den blev sendt til
# modellen, som returnerede den SAMME bare form, og spærringen forkastede
# svaret. En hegn-fejl er mekanisk: den skal rettes deterministisk, ikke
# forklares for en model.

def test_bar_blok_faar_hegn_uden_model_kald() -> None:
    """Den form der oftest rammer brugeren, løses uden et model-kald."""
    from core.services.jarvis_ui_guard import fejl_i_flader

    defekt = (
        'jarvis-ui {"type":"timeline","title":"T","items":'
        '[{"time":"09:21","title":"A","detail":"x","status":"done"}]}'
    )
    fejl = fejl_i_flader(defekt)
    assert fejl, "testens forudsætning: den bare form skal være en fejl"

    kaldt: list[int] = []

    def _stream(**_kwargs):
        kaldt.append(1)
        yield FollowupDone(text="")

    ud = korriger_flader(
        defekt, fejl,
        stream_followup=_stream,
        provider="test", model="test", base_messages=[],
    )
    assert kaldt == [], "en hegn-fejl må ikke koste et model-kald"
    assert "```jarvis-ui" in ud
    assert fejl_i_flader(ud) == []


def test_mekanisk_reparation_roerer_ikke_korrekt_eller_prosa() -> None:
    """En vagt der retter for meget ødelægger svar der var i orden."""
    from core.services.flade_korrektion import _mekanisk_reparation

    korrekt = (
        'Se her.\n\n```jarvis-ui\n'
        '{"type":"callout","tone":"info","title":"T","body":"B"}\n```'
    )
    assert _mekanisk_reparation(korrekt) == korrekt

    # Prosa der blot NÆVNER formen er ikke en flade.
    omtale = 'Jeg skrev jarvis-ui {"type":"callout"} i mit svar.'
    assert _mekanisk_reparation(omtale) == omtale

    # En kodeblok er ikke en flade.
    kode = '```bash\ngit show 442b3bc85\n```'
    assert _mekanisk_reparation(kode) == kode


def test_bar_blok_med_datfejl_sendes_videre_til_modellen() -> None:
    """Hegnet sættes mekanisk — men en manglende title kræver stadig en model."""
    from core.services.jarvis_ui_guard import fejl_i_flader

    defekt = (
        'jarvis-ui {"type":"timeline","title":"T","items":'
        '[{"time":"09:21","detail":"x","status":"done"}]}'
    )
    fejl = fejl_i_flader(defekt)
    assert fejl

    kaldt: list[int] = []

    def _stream(**_kwargs):
        kaldt.append(1)
        yield FollowupDone(text="")

    korriger_flader(
        defekt, fejl,
        stream_followup=_stream,
        provider="test", model="test", base_messages=[],
    )
    assert kaldt == [1], "en datfejl skal stadig nå modellen"
