"""`core/cli/visible_output` — normalisering af de flader CLI'en viser.

Dækningen her blev krævet af coverage-gaten 25/11-2026, da
`normalize_last_outcome` blev rettet: den gav `text_preview` videre råt, så
chiffertekst fra et medlems-run kunne nå CLI'en som om det var svaret.

Værnet er `visible_preview_crypto.laesbaar_preview`: klartekst passerer
uændret, chiffer dekrypteres når nøglen kan bevises, og bliver
`PLADSHOLDER_KRYPTERET` når den ikke kan. Testene her holder begge retninger
fast — både at chifferen standses og at visningen ikke koster noget.
"""
from __future__ import annotations

from core.services.visible_preview_crypto import PLADSHOLDER_KRYPTERET

CHIFFER = "enc:v1:" + "A" * 80
KLAR = "et helt almindeligt svar"


def _outcome(preview: str | None, **extra) -> dict:
    base = {
        "run_id": "r-1",
        "lane": "visible",
        "provider": "deepseek",
        "model": "m",
        "status": "completed",
        "finished_at": "2026-11-25T17:00:00+00:00",
        "text_preview": preview,
    }
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# normalize_last_outcome
# ---------------------------------------------------------------------------


def test_last_outcome_standser_chiffertekst() -> None:
    from core.cli.visible_output import normalize_last_outcome

    svar = normalize_last_outcome(_outcome(CHIFFER))
    assert svar is not None
    assert svar["text_preview"] == PLADSHOLDER_KRYPTERET, (
        "chiffertekst slap ud til CLI'en som om det var svaret: "
        f"{str(svar['text_preview'])[:40]!r}"
    )


def test_last_outcome_lader_klartekst_passere() -> None:
    from core.cli.visible_output import normalize_last_outcome

    svar = normalize_last_outcome(_outcome(KLAR))
    assert svar is not None
    assert svar["text_preview"] == KLAR, (
        "værnet kostede visningen: klartekst skal ud uændret"
    )


def test_last_outcome_bevarer_de_oevrige_felter() -> None:
    from core.cli.visible_output import normalize_last_outcome

    svar = normalize_last_outcome(_outcome(KLAR, error="noget gik galt"))
    assert svar is not None
    assert svar["run_id"] == "r-1"
    assert svar["status"] == "completed"
    assert svar["error"] == "noget gik galt"


def test_last_outcome_er_none_for_tom_input() -> None:
    from core.cli.visible_output import normalize_last_outcome

    assert normalize_last_outcome(None) is None
    assert normalize_last_outcome({}) is None


def test_last_outcome_taaler_manglende_preview() -> None:
    from core.cli.visible_output import normalize_last_outcome

    svar = normalize_last_outcome(_outcome(None))
    assert svar is not None
    assert svar["text_preview"] is None


# ---------------------------------------------------------------------------
# normalize_active_run — søsteren der ikke bærer preview
# ---------------------------------------------------------------------------


def test_active_run_er_none_for_tom_input() -> None:
    from core.cli.visible_output import normalize_active_run

    assert normalize_active_run(None) is None


def test_active_run_bevarer_kanselleret_flag() -> None:
    from core.cli.visible_output import normalize_active_run

    svar = normalize_active_run({"run_id": "r-2", "cancelled": True})
    assert svar is not None
    assert svar["run_id"] == "r-2"
    assert svar["cancelled"] is True


# ---------------------------------------------------------------------------
# normalize_visible_work — preview-feltet hedder noget andet her
# ---------------------------------------------------------------------------


def test_visible_work_giver_en_tom_flade_for_tom_input() -> None:
    """Modsat `normalize_last_outcome` må denne IKKE give None.

    Work-fladen vises altid i CLI'en; en manglende kilde skal give en tom
    flade med `active: False`, ikke en der forsvinder fra visningen.
    """
    from core.cli.visible_output import normalize_visible_work

    svar = normalize_visible_work(None)
    assert svar is not None
    assert svar["active"] is False


def test_visible_work_bevarer_aktiv_flag() -> None:
    from core.cli.visible_output import normalize_visible_work

    svar = normalize_visible_work({"active": True, "run_id": "r-3"})
    assert svar is not None
    assert svar["active"] is True
    assert svar["run_id"] == "r-3"
