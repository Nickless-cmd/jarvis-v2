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

# Fanges FØR autouse-fixturen patcher den væk, så arkiv-testen kan kalde den ægte.
_AEGTE_ARKIVER = sfp.arkiver_forsegling
_AEGTE_UDFALDS_ARKIVER = sfp.arkiver_udfald


@pytest.fixture(autouse=True)
def _ingen_produktions_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Testene må ALDRIG skrive til den rigtige governance-ledger.

    (13/11-2026) `score()` arkiverer som standard, så hver test der kaldte den
    skrev sine test-id'er ind i produktionsledgeren — og efterlod dermed en
    hash som de efterfølgende tests blev målt imod. Det gjorde ni tests røde
    af en årsag der lå i en helt anden test. Arkivering testes eksplicit i
    `test_arkiv_*` med monkeypatch, så den ægte funktion dækkes dér.

    (13/11-2026, Bjoerns femte fund) Også UDFALDS-arkivet holdes ude af testene:
    uden det skrev en tidligere test sin `T1`-raekke i den delte shield-DB, og
    den naeste test — der skulle se en post som uforsikret — saa den som
    arkiveret. Testen maalte sin nabo. Standard her er en TOM ledger; de tests
    der vil maale mod et arkiv peger `_arkiv_udfald` paa deres eget dict.
    """
    monkeypatch.setattr(sfp, "arkiver_forsegling", lambda poster: 0)
    monkeypatch.setattr(sfp, "arkiver_udfald", lambda poster, ids: 0)
    monkeypatch.setattr(sfp, "_arkiv_udfald", lambda: {})


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
    aendret = sfp.verificer_forsegling([post], forsegling)

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

    # Den autouse-fixture slår arkiveringen fra for at beskytte den rigtige
    # ledger; her testes netop den funktion, så originalen kaldes eksplicit.
    aegte = _AEGTE_ARKIVER
    nye = aegte([_post(id="F1"), _post(id="F3")])

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


# ── (13/11-2026) Maalereglen skal vaere forseglet, og en brudt forsegling ──────
# ── skal BLOKERE — ikke bare rapporteres. Bjørns to fund. ─────────────────────


def test_aendret_sql_bryder_forseglingen(rigtig_db: Path, tmp_path: Path) -> None:
    """Maalereglen er en del af forudsigelsen, ikke en detalje ved siden af.

    Foer daekkede hashen kun id+claim+op+threshold+probability+score_at. Saa
    kunne spoergringen der afgoer udfaldet skiftes ud mens P stod stille — og
    forseglingen ville ikke se det. Det er praecis den slags bagdoer der goer
    en kalibrering vaerdiloes.
    """
    post = _post(threshold=3)
    forsegling = {"T1": sfp.frozen_hash(post)}

    post["sql"] = "SELECT COUNT(*) FROM beslutninger WHERE status='revoked'"

    assert sfp.verificer_forsegling([post], forsegling) == ["T1"]


def test_aendret_kilde_bryder_forseglingen(rigtig_db: Path, tmp_path: Path) -> None:
    """Samme for `kilde`: en JSON-kilde er ogsaa en maaleregel."""
    post = _post(
        sql=None,
        kilde={
            "noegle": "tick_quality_evaluations",
            "dato_felt": "evaluated_at",
            "dato": "2026-11-20",
            "vaerdi_felt": "score",
            "min_n": 2,
        },
    )
    forsegling = {"T1": sfp.frozen_hash(post)}

    post["kilde"] = dict(post["kilde"], min_n=1)

    assert sfp.verificer_forsegling([post], forsegling) == ["T1"]


def test_brudt_forsegling_blokerer_scoring_og_kalibrering(
    rigtig_db: Path, tmp_path: Path
) -> None:
    """En aendring der OPDAGES maa ikke samtidig paavirke Brier.

    Foer blev `tampered` beregnet og derefter ignoreret: posten blev scoret,
    skrevet som hit og taget med i kalibreringen. En forsegling der ikke
    standser noget er dekoration.
    """
    post = _post(threshold=3)
    forsegling = {"T1": sfp.frozen_hash(post)}
    post["probability"] = 0.99  # aendret efter frysning
    fil = _fil(tmp_path, [post], forsegling=forsegling)

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["tampered"] == ["T1"]
    assert resultat["rapport"][0]["status"] == "forsegling_brudt"
    # Ingen dom, ingen skrivning, og intet datapunkt i kalibreringen.
    assert "hit" not in post
    assert resultat["skrev"] is False
    assert resultat["kalibrering"]["n_events"] == 0
    assert resultat["kalibrering"]["brier"] is None


def test_brudt_forsegling_uden_arkiv_blokerer_ogsaa(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ogsaa naar kun ledger-arkivet ser aendringen — filen selv er konsistent."""
    post = _post(probability=0.9)
    oprindelig = sfp.frozen_hash(post)
    post["probability"] = 0.3
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    from core.runtime import db_governance_ledger

    monkeypatch.setattr(
        db_governance_ledger,
        "read_ledger",
        lambda area=None, limit=50: [
            {"key": "T1", "ts": "2026-11-12T20:41:00+00:00", "value": {"frozen_hash": oprindelig}}
        ],
    )

    resultat = sfp.score(fil, rigtig_db, nu=NU, arkiver=False)

    assert resultat["tampered"] == []
    assert resultat["arkiv_tampered"] == ["T1"]
    assert resultat["rapport"][0]["status"] == "forsegling_brudt"
    assert resultat["kalibrering"]["n_events"] == 0


def test_v1_forseglet_post_stemples_og_scores(
    rigtig_db: Path, tmp_path: Path
) -> None:
    """En post forseglet under den gamle, smallere regel maa ikke meldes brudt.

    Ellers ville den bredere hash goere ti sunde poster til falske alarmer —
    praecis den fejlform aftenen handler om.
    """
    post = _post(threshold=3)
    v1_hash = sfp.frozen_hash(post, 1)
    fil = _fil(tmp_path, [post], forsegling={"T1": v1_hash})

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["tampered"] == []
    assert resultat["stemplet"] == ["T1"]
    assert resultat["rapport"][0]["status"] == "scoret"
    # Stemplingen er skrevet, saa den ikke skal gentages hver koersel.
    gemt = json.loads(fil.read_text(encoding="utf-8"))
    assert gemt["forudsigelser"][0]["_forsegling_version"] == 1


def test_post_uden_match_i_nogen_version_stemples_ikke(
    rigtig_db: Path, tmp_path: Path
) -> None:
    """En aendret post maa ikke kunne maskeres som en version-opgradering."""
    post = _post(probability=0.9)
    post["probability"] = 0.2  # aendret: matcher hverken v1 eller v2
    fil = _fil(tmp_path, [post], forsegling={"T1": "deadbeefdeadbeef"})

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["stemplet"] == []
    assert resultat["uafklaret"] == ["T1"]
    assert resultat["rapport"][0]["status"] == "forsegling_brudt"


# ── Forseglingen skal dække det der BÆRER resultatet (13/11-2026) ─────────────
# Bjoerns fund: `event_group` og `frozen_at` bestemmer hvor mange uafhængige
# hændelser Brier regnes over, og hvilken post i gruppen der tæller som den
# første. Begge var uden for hashen — så resultatet kunne flyttes uden at
# forseglingen så det.


def test_aendret_event_group_bryder_forseglingen() -> None:
    """At flytte en post til en ny gruppe ændrer n_events — og dermed Brier."""
    post = _post(event_group="g1")
    forsegling = {"T1": sfp.frozen_hash(post)}

    post["event_group"] = "g2"

    assert sfp.verificer_forsegling([post], forsegling) == ["T1"]


def test_aendret_frozen_at_bryder_forseglingen() -> None:
    """`frozen_at` afgør hvem der er «den først frosne» — altså hvem der tæller."""
    post = _post()
    forsegling = {"T1": sfp.frozen_hash(post)}

    post["frozen_at"] = "2026-11-13T20:41:00+00:00"

    assert sfp.verificer_forsegling([post], forsegling) == ["T1"]


def test_gruppeflytning_ville_aendret_brier_men_fanges(rigtig_db: Path, tmp_path: Path) -> None:
    """Det konkrete forløb: Brier 0,2025 → 0,1812 ved at flytte én post.

    To poster om samme hændelse tæller som ÉN. Flyttes den anden til sin egen
    gruppe, bliver de to — og Brier falder uden at en enkelt maaling er blevet
    bedre. Det er præcis den slags «forbedring» forseglingen skal forhindre.
    """
    a = _post(id="A", event_group="g1", probability=0.55, frozen_at="2026-11-12T20:00:00+00:00")
    b = _post(id="B", event_group="g1", probability=0.60, frozen_at="2026-11-12T21:00:00+00:00")
    forsegling = {"A": sfp.frozen_hash(a), "B": sfp.frozen_hash(b)}

    # Før: én hændelse, A's P tæller.
    foer = sfp.kalibrering([dict(a, hit=True), dict(b, hit=True)])
    assert foer["n_events"] == 1
    assert foer["brier"] == 0.2025

    # Efter en uset flytning: to hændelser, lavere Brier.
    efter = sfp.kalibrering(
        [dict(a, hit=True), dict(b, hit=True, event_group="g2")]
    )
    assert efter["n_events"] == 2
    assert efter["brier"] == 0.1812

    # Men flytningen kan ikke ske ubemærket.
    b["event_group"] = "g2"
    assert sfp.verificer_forsegling([a, b], forsegling) == ["B"]


def test_scoring_danner_udfalds_forsegling(rigtig_db: Path, tmp_path: Path) -> None:
    """Udfaldet forsegles i det øjeblik det skrives — ikke bagefter."""
    post = _post(threshold=3)
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["rapport"][0]["status"] == "scoret"
    gemt = json.loads(fil.read_text(encoding="utf-8"))["forudsigelser"][0]
    assert gemt["hit"] is True
    assert gemt["udfalds_hash"] == sfp.udfalds_hash(gemt)


def test_aendret_hit_efter_scoring_udelades(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Et `hit` der er rettet bagefter må ikke indgå i kalibreringen.

    `evaluer` svarer «allerede-scorets» for en post der har `hit` — så uden en
    udfalds-forsegling ville en rettet værdi blive genbrugt og vejet med.

    (13/11-2026) Referencepunktet er arkivet, ikke feltet i filen: testen
    peger derfor `_arkiv_udfald` på den hash den foerste koersel skrev. Uden
    en arkiv-raekke kan et rettet `hit` ikke OPDAGES — kun markeres som
    uforsikret, og så kan det ikke udelades. Det er den ærlige grænse for de
    poster der blev scoret foer arkiveringen fandtes.
    """
    post = _post(threshold=3)
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})
    sfp.score(fil, rigtig_db, nu=NU)

    data = json.loads(fil.read_text(encoding="utf-8"))
    arkiveret = data["forudsigelser"][0]["udfalds_hash"]
    assert arkiveret
    monkeypatch.setattr(sfp, "_arkiv_udfald", lambda: {"T1": arkiveret})

    data["forudsigelser"][0]["hit"] = False  # rettet efter scoring
    fil.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["udfald_aendret"] == ["T1"]
    assert resultat["rapport"][0]["status"] == "udfald_aendret"
    assert resultat["kalibrering"]["n_events"] == 0


def test_post_scoret_foer_udfalds_forsegling_rapporteres(
    rigtig_db: Path, tmp_path: Path
) -> None:
    """En post scoret før v3 har intet udfalds-hash. Det skal STÅ, ikke skjules.

    Den kan ikke få en troværdig forsegling bagefter — den ville være dannet
    efter kendskab til udfaldet. Så den rapporteres som uforsikret og indgår
    stadig, så historikken ikke bliver ubrugelig af en ærlig mangel.
    """
    post = _post(threshold=3, hit=True, actual=3.0, scored_at="2026-11-13T20:00:00+00:00")
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["udfald_uforsikret"] == ["T1"]
    assert resultat["udfald_aendret"] == []
    assert resultat["kalibrering"]["n_events"] == 1


def test_svag_forsegling_rapporteres(rigtig_db: Path, tmp_path: Path) -> None:
    """En v1-forsegling er ikke brudt — men den er svagere, og det skal stå."""
    post = _post(threshold=3)
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post, 1)})

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["svag_forsegling"] == ["T1"]
    assert resultat["forsegling_brudt"] == []
    assert resultat["rapport"][0]["status"] == "scoret"


def test_aendret_udfald_med_genberegnet_hash_fanges_alligevel(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Udfaldet OG dets hash kan aendres sammen — det skal stadig fanges.

    (13/11-2026, Bjoerns femte fund) Foer blev ``udfalds_hash`` gemt i samme
    post som ``hit`` og sammenlignet med en genberegning af SAMME post. Saa
    kunne man rette ``hit`` og genberegne hashen, og kontrollen passede igen:
    en forsegling der kun sammenligner filen med sig selv er ikke en
    forsegling. Referencepunktet er nu ledgerens foerste raekke.
    """
    post = _post(threshold=3)
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    # Foerste koersel giver den aegte udfalds-hash; den bruges som arkiv-reference.
    sfp.score(fil, rigtig_db, nu=NU)
    data = json.loads(fil.read_text(encoding="utf-8"))
    oprindelig = data["forudsigelser"][0]["udfalds_hash"]
    assert oprindelig, "scoringen skulle have skrevet en udfalds-hash"

    monkeypatch.setattr(sfp, "_arkiv_udfald", lambda: {"T1": oprindelig})

    # Baade udfaldet og dets hash aendres: filen er selvkonsistent.
    data["forudsigelser"][0]["hit"] = False
    data["forudsigelser"][0]["udfalds_hash"] = sfp.udfalds_hash(data["forudsigelser"][0])
    fil.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["udfald_aendret"] == ["T1"]
    assert resultat["kalibrering"]["n_events"] == 0


def test_tilfoejet_udfalds_hash_forsegler_ikke_en_gammel_post(
    rigtig_db: Path, tmp_path: Path
) -> None:
    """At skrive feltet paa en gammel post maa ikke gøre den forseglet.

    Det var den retroaktive pynt: en post scoret foer udfalds-forseglingen
    fandtes kunne se forseglet ud blot ved at nogen tilfoejede feltet. Nu
    afgoer ledgerens raekke — ikke feltets tilstedeværelse — om posten er
    forseglet, saa en gammel scoring bliver ved med at staa som uforsikret.
    """
    post = _post(threshold=3, hit=True, actual=3.0, scored_at="2026-11-13T20:00:00+00:00")
    post["udfalds_hash"] = sfp.udfalds_hash(post)  # feltet tilfoejet bagefter
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["udfald_uforsikret"] == ["T1"]
    assert resultat["udfald_aendret"] == []


def test_arkiveret_udfald_forsegler_posten(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Vejen fra «uforsikret» til «forseglet» gaar gennem arkivet, ikke filen.

    Uden denne test kunne arkiveringen vaere dekoration: den skrev en raekke
    som intet senere sammenlignede med.
    """
    arkiv: dict[str, str] = {}
    monkeypatch.setattr(sfp, "_arkiv_udfald", lambda: dict(arkiv))

    def _arkiver(poster: list[dict[str, object]], ids: list[str]) -> int:
        for p in poster:
            if str(p.get("id")) in ids and p.get("hit") is not None:
                h = sfp.udfalds_hash(p)
                if h:
                    arkiv[str(p.get("id"))] = h
        return len(ids)

    monkeypatch.setattr(sfp, "arkiver_udfald", _arkiver)

    post = _post(threshold=3)
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})

    foerste = sfp.score(fil, rigtig_db, nu=NU)
    assert foerste["udfald_arkiveret"] == 1
    assert arkiv["T1"]

    anden = sfp.score(fil, rigtig_db, nu=NU)
    assert anden["udfald_uforsikret"] == []
    assert anden["udfald_aendret"] == []
    assert anden["kalibrering"]["n_events"] == 1


def test_kun_ny_scorede_poster_arkiveres(monkeypatch: pytest.MonkeyPatch) -> None:
    """Arkiveringen maa ikke give gamle scoringer en raekke med tilbagevirkende kraft.

    (13/11-2026) Blev hele post-listen arkiveret, ville de poster der blev
    scoret foer arkiveringen fandtes pludselig se forseglede ud — den
    retroaktive pynt som `udfald_uforsikret` netop findes for at forhindre.
    """
    skrevne: list[str] = []
    import core.runtime.db_governance_ledger as ledger

    monkeypatch.setattr(
        ledger, "record_mutation", lambda area, key, value: skrevne.append(key)
    )
    monkeypatch.setattr(sfp, "_arkiv_udfald", lambda: {})

    gammel = _post(id="GAMMEL", threshold=3, hit=True, actual=3.0, scored_at="2026-11-13T20:00:00+00:00")
    ny = _post(id="NY", threshold=3, hit=True, actual=3.0, scored_at="2026-11-13T20:00:00+00:00")

    antal = _AEGTE_UDFALDS_ARKIVER([gammel, ny], ["NY"])

    assert antal == 1
    assert skrevne == ["NY"]


def test_felt_der_afviger_fra_arkivets_raekke_udelades(
    rigtig_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Feltet i filen skal stemme med ledgeren — ikke kun udfaldet med ledgeren.

    (13/11-2026) Uden denne test var halvdelen af betingelsen dekoration: et
    `udfalds_hash` der var byttet ud, mens `hit`/`actual`/`scored_at` var
    intakte, slap igennem. Feltet er det en laeser ser, saa naar det modsiger
    den uafhaengige raekke er posten uenighed — ikke et tal man regner videre
    paa.
    """
    post = _post(threshold=3)
    fil = _fil(tmp_path, [post], forsegling={"T1": sfp.frozen_hash(post)})
    sfp.score(fil, rigtig_db, nu=NU)

    data = json.loads(fil.read_text(encoding="utf-8"))
    arkiveret = data["forudsigelser"][0]["udfalds_hash"]
    monkeypatch.setattr(sfp, "_arkiv_udfald", lambda: {"T1": arkiveret})

    data["forudsigelser"][0]["udfalds_hash"] = "0" * 16  # feltet byttet ud
    fil.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    resultat = sfp.score(fil, rigtig_db, nu=NU)

    assert resultat["udfald_aendret"] == ["T1"]
    assert resultat["kalibrering"]["n_events"] == 0
