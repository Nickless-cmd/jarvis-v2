"""Test: scoreren for frosne forudsigelser (12/11-2026).

De tre regler der værnes her, og hvorfor hver test er skrevet som den er:

1. ``probability`` må ikke kunne ændres ubemærket efter frysning — derfor en
   hash der dækker netop de felter, testet ved at ændre P og se den fyre.
2. F1/F6 er modsatrettede om SAMME hændelse. Kalibreringen skal tælle dem som
   én hændelse, ellers kan jeg puste mit datagrundlag op ved at vædde begge veje.
3. En post der ikke er moden må ikke score. En scoringsregel der kører for
   tidligt måler ikke det den påstår.

Databasen i testene er en RIGTIG sqlite-fil i ``tmp_path`` med rigtige rækker —
ikke en fake connection. En fake der svarer det samme uanset SQL kan pr.
definition ikke afsløre en forkert WHERE-gren.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import score_frozen_predictions as sfp

NU = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


@pytest.fixture()
def rigtig_db(tmp_path: Path) -> Path:
    """En aegte sqlite-fil med de raekker spoergringerne faktisk rammer."""
    sti = tmp_path / "prove.db"
    conn = sqlite3.connect(sti)
    conn.executescript(
        """
        CREATE TABLE beslutninger (id INTEGER PRIMARY KEY, status TEXT);
        INSERT INTO beslutninger (status) VALUES
            ('active'),('active'),('active'),('revoked'),('fulfilled');
        """
    )
    conn.commit()
    conn.close()
    return sti


def _post(**over: object) -> dict[str, object]:
    post: dict[str, object] = {
        "id": "T1",
        "claim": "der er mindst 3 aktive",
        "sql": "SELECT COUNT(*) FROM beslutninger WHERE status='active'",
        "op": ">=",
        "threshold": 3,
        "probability": 0.7,
        "score_at": (NU - timedelta(hours=1)).isoformat(),
        "frozen_at": "2026-11-12T20:41:00+00:00",
        "event_group": "g1",
    }
    post.update(over)
    return post


def _fil(tmp_path: Path, poster: list[dict[str, object]], forsegling: dict | None = None) -> Path:
    sti = tmp_path / "frosne.json"
    data: dict[str, object] = {"forudsigelser": poster}
    if forsegling is not None:
        data["forsegling"] = forsegling
    sti.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return sti


def test_hash_fanger_aendret_sandsynlighed() -> None:
    post = _post()
    forsegling = {"T1": sfp.frozen_hash(post)}

    post["probability"] = 0.95
    aendret = sfp.verifikation = sfp.verificer_forsegling([post], forsegling)

    assert aendret == ["T1"]


def test_hash_er_stabil_naar_intet_er_aendret() -> None:
    post = _post()
    forsegling = {"T1": sfp.frozen_hash(post)}

    # En scoring tilføjer actual/hit — det er IKKE en ændring af det frosne løfte.
    post["actual"] = 3.0
    post["hit"] = True

    assert sfp.verificer_forsegling([post], forsegling) == []


def test_event_group_taeller_som_en_haendelse(tmp_path: Path) -> None:
    """F1 og F6 væddende modsat om samme hændelse: 2 poster, 1 hændelse."""
    a = _post(id="F1", event_group="samme", probability=0.75, hit=True, frozen_at="2026-11-12T20:41:00+00:00")
    b = _post(id="F6", event_group="samme", probability=0.65, hit=False, frozen_at="2026-11-12T20:44:00+00:00")

    k = sfp.kalibrering([a, b])

    assert k["n_poster"] == 2
    assert k["n_events"] == 1
    assert k["haendelser"][0]["uenige"] is True
    # Udfaldet tages fra den først frosne post — ikke fra den der passer bedst.
    assert k["haendelser"][0]["outcome"] == 1
    # Sandsynligheden er også den først frosne. Et gennemsnit ville give en
    # vurdering lavet EFTER data 50 % vægt — så kunne en dårlig P repareres
    # ved at fryse en modsat post bagefter.
    assert k["haendelser"][0]["probability"] == pytest.approx(0.75)


def test_senere_vurdering_er_revision_ikke_kalibrering() -> None:
    """F6 er lavet efter F1 og må ikke trække den primære sandsynlighed."""
    a = _post(id="F1", event_group="samme", probability=0.75, hit=True, frozen_at="2026-11-12T20:41:00+00:00")
    b = _post(id="F6", event_group="samme", probability=0.30, hit=True, frozen_at="2026-11-12T20:44:00+00:00")

    h = sfp.kalibrering([a, b])["haendelser"][0]

    assert h["probability"] == pytest.approx(0.75)
    assert len(h["revisioner"]) == 1
    assert h["revisioner"][0]["id"] == "F6"
    assert h["revisioner"][0]["probability"] == pytest.approx(0.30)


def test_to_grupper_giver_to_haendelser() -> None:
    a = _post(id="F1", event_group="g1", hit=True)
    b = _post(id="F3", event_group="g2", hit=False)

    k = sfp.kalibrering([a, b])

    assert k["n_events"] == 2
    assert k["n_poster"] == 2


def test_brier_regnes_paa_haendelser_ikke_poster() -> None:
    """Fire poster i to grupper: Brier skal bruge de to grupper, ikke de fire."""
    a = _post(id="F1", event_group="g1", probability=0.8, hit=True)
    b = _post(id="F6", event_group="g1", probability=0.8, hit=True)
    c = _post(id="F2", event_group="g2", probability=0.2, hit=False)
    d = _post(id="F5", event_group="g2", probability=0.2, hit=False)

    k = sfp.kalibrering([a, b, c, d])

    assert k["n_events"] == 2
    # (0.8-1)^2 = 0.04 og (0.2-0)^2 = 0.04 -> middel 0.04
    assert k["brier"] == pytest.approx(0.04)


def test_ikke_moden_post_scores_ikke(rigtig_db: Path, tmp_path: Path) -> None:
    post = _post(score_at=(NU + timedelta(days=3)).isoformat())
    fil = _fil(tmp_path, [post])

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["rapport"][0]["status"] == "venter"
    assert "hit" not in post
    assert resultat["skrev"] is False


def test_hit_evalueres_mod_rigtig_sqlite(rigtig_db: Path, tmp_path: Path) -> None:
    post = _post(threshold=3)
    fil = _fil(tmp_path, [post])

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["rapport"][0] == {
        "status": "scoret",
        "actual": 3.0,
        "hit": True,
        "id": "T1",
    }


def test_miss_evalueres_mod_rigtig_sqlite(rigtig_db: Path, tmp_path: Path) -> None:
    """Samme tabel, højere tærskel — så skal den fejle. Beviser at SQL'en læses."""
    post = _post(threshold=10)
    fil = _fil(tmp_path, [post])

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["rapport"][0]["hit"] is False
    assert resultat["rapport"][0]["actual"] == 3.0


def test_ingen_data_giver_ingen_dom(rigtig_db: Path, tmp_path: Path) -> None:
    """Tom mængde må ikke ligne succes — AVG over nul rækker er NULL, ikke 0.

    En COUNT over nul rækker er derimod et gyldigt svar (0 = nul hændelser),
    så den kan og skal scores. Det er forskellen testen værner om.
    """
    post = _post(sql="SELECT AVG(id) FROM beslutninger WHERE status='finnes_ikke'")
    fil = _fil(tmp_path, [post])

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["rapport"][0]["status"] == "ingen-data"
    assert "hit" not in post


def test_count_nul_er_et_gyldigt_svar(rigtig_db: Path, tmp_path: Path) -> None:
    """Nul hændelser i vinduet er et reelt miss — ikke 'ingen data'."""
    post = _post(sql="SELECT COUNT(*) FROM beslutninger WHERE status='finnes_ikke'", threshold=1)
    fil = _fil(tmp_path, [post])

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["rapport"][0]["status"] == "scoret"
    assert resultat["rapport"][0]["actual"] == 0.0
    assert resultat["rapport"][0]["hit"] is False


def test_state_json_kilde_aggregerer_kun_dagens_raekker(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3-lignende regel: middelvaerdi af dagens evalueringer, under min_n = ingen dom."""
    from core.runtime import state_store

    raekker = [
        {"evaluated_at": "2026-11-20T08:00:00+00:00", "score": 40},
        {"evaluated_at": "2026-11-20T09:00:00+00:00", "score": 60},
        {"evaluated_at": "2026-11-19T23:00:00+00:00", "score": 99},  # anden dag
    ]
    monkeypatch.setattr(state_store, "load_json", lambda name, default: raekker)

    kilde = {
        "noegle": "tick_quality_evaluations",
        "dato_felt": "evaluated_at",
        "dato": "2026-11-20",
        "vaerdi_felt": "score",
        "min_n": 2,
    }
    post = _post(sql=None, kilde=kilde, threshold=45)
    fil = _fil(tmp_path, [post])

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    # Kun de to rækker fra 20/11 tæller: (40+60)/2 = 50, ikke (40+60+99)/3.
    assert resultat["rapport"][0]["actual"] == 50.0
    assert resultat["rapport"][0]["hit"] is True


def test_state_json_under_min_n_giver_ingen_dom(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.runtime import state_store

    raekker = [{"evaluated_at": "2026-11-20T08:00:00+00:00", "score": 90}]
    monkeypatch.setattr(state_store, "load_json", lambda name, default: raekker)

    kilde = {
        "noegle": "tick_quality_evaluations",
        "dato_felt": "evaluated_at",
        "dato": "2026-11-20",
        "vaerdi_felt": "score",
        "min_n": 5,
    }
    post = _post(sql=None, kilde=kilde, threshold=45)
    fil = _fil(tmp_path, [post])

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["rapport"][0]["status"] == "ingen-data"


def test_skrivende_sql_afvises(rigtig_db: Path, tmp_path: Path) -> None:
    post = _post(sql="DELETE FROM beslutninger")
    fil = _fil(tmp_path, [post])

    with pytest.raises(ValueError, match="laesende SQL"):
        sfp.score(fil, rigtig_db, nu=NU)


def test_scoring_skrives_kun_naar_noget_blev_scoret(rigtig_db: Path, tmp_path: Path) -> None:
    post = _post()
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["skrev"] is True
    gemt = json.loads(fil.read_text(encoding="utf-8"))
    assert gemt["forudsigelser"][0]["hit"] is True
    assert "scored_at" in gemt["forudsigelser"][0]
    # Scoren må ikke bryde sin egen forsegling.
    assert sfp.verificer_forsegling(gemt["forudsigelser"], gemt["forsegling"]) == []


def test_dry_run_skriver_ikke(rigtig_db: Path, tmp_path: Path) -> None:
    post = _post()
    fil = _fil(tmp_path, [post])
    foer = fil.read_text(encoding="utf-8")

    resultat = sfp.score(fil, rigtig_db, dry_run=True, nu=NU)

    assert resultat["rapport"][0]["status"] == "scoret"
    assert fil.read_text(encoding="utf-8") == foer


# ── Eksternt arkiv: forseglingen skal ikke kunne ændres ved at redigere filen ──


def test_arkiv_skriver_kun_poster_der_ikke_er_arkiveret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Idempotent: en post arkiveres én gang, ellers fylder gentagne kørsler ledgeren."""
    skrevne: list[tuple[str, str]] = []

    def _fake_read(area: str | None = None, limit: int = 50) -> list[dict]:
        return [{"key": "F1", "ts": "2026-11-12T20:41:00+00:00", "value": {"frozen_hash": "gammel"}}]

    def _fake_record(area: str, key: str, value: dict) -> None:
        skrevne.append((area, key))

    from core.runtime import db_governance_ledger

    monkeypatch.setattr(db_governance_ledger, "read_ledger", _fake_read)
    monkeypatch.setattr(db_governance_ledger, "record_mutation", _fake_record)

    nye = sfp.arkiver_forsegling([_post(id="F1"), _post(id="F3")])

    assert nye == 1
    assert skrevne == [("frozen_predictions", "F3")]


def test_arkiv_aeldste_tager_den_foerste_ikke_den_seneste(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ledgeren er append-only: nyeste række ligger øverst, men den ældste er sandheden."""
    from core.runtime import db_governance_ledger

    monkeypatch.setattr(
        db_governance_ledger,
        "read_ledger",
        lambda area=None, limit=50: [
            {"key": "F1", "ts": "2026-11-13T10:00:00+00:00", "value": {"frozen_hash": "ny"}},
            {"key": "F1", "ts": "2026-11-12T20:41:00+00:00", "value": {"frozen_hash": "oprindelig"}},
        ],
    )

    assert sfp._arkiv_aeldste() == {"F1": "oprindelig"}


def test_aendring_af_fil_og_hash_opdages_mod_arkivet(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Den gamle forsegling kunne omgås ved at rette både P og hash i samme fil.

    Arkivet ligger uden for filen, så den ændring fanges nu.
    """
    post = _post(probability=0.9)
    oprindelig_hash = sfp.frozen_hash(post)
    post["probability"] = 0.3
    post["frozen_hash"] = sfp.frozen_hash(post)  # angriberen retter også hashen
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    from core.runtime import db_governance_ledger

    monkeypatch.setattr(
        db_governance_ledger,
        "read_ledger",
        lambda area=None, limit=50: [
            {"key": "T1", "ts": "2026-11-12T20:41:00+00:00", "value": {"frozen_hash": oprindelig_hash}}
        ],
    )

    resultat = sfp.score(fil, rigtig_db, nu=NU, arkiver=False)

    # Filens egen forsegling er konsistent — den kan ikke se noget.
    assert resultat["tampered"] == []
    # Men arkivet afslører at P er rørt.
    assert resultat["arkiv_tampered"] == ["T1"]
