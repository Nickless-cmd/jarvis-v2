"""Indbakkens visning — Opgave 2.

To slags tests her, og begge er nødvendige:

* **Adfærd** gennem injicerede kilder, med fast `nu_ts`. Forfald i dage kan
  ikke måles mod en klokke der går.
* **Kilde-vagter (AST)** om de to udelukkelser spec'en gentager tre steder:
  visningen må ikke kunne skrive, og kanalbeskeder må ikke sive ind. En
  udelukkelse uden vagt glider — og en kilde-vagt der greper efter en streng
  måler næsten ingenting, så de parser træet.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from core.runtime import db_inbox
from core.services.inbox_view import Kilder, byg_indbakke

BJORN = "bjorn"
ANDEN = "en-anden-bruger"
#: Fast klokke: 3/10-2026 12:00:00 UTC.
TID = 1791028800.0
DAG = 86400.0
_KILDE = pathlib.Path("core/services/inbox_view.py")


@pytest.fixture(autouse=True)
def _ejeren(ejeren_er_bjorn):
    """Hele filen laeser som BJORN, og BJORN skal vaere ejeren — ellers maales
    `_min_post`s regel om ejerloese poster mod maskinens egen bruger-tabel."""
    return ejeren_er_bjorn


def _iso(ts: float) -> str:
    from datetime import UTC, datetime
    return datetime.fromtimestamp(ts, UTC).isoformat()


def _kilder(**kw) -> Kilder:
    """Tomme kilder, med kun det testen taler om udfyldt."""
    tom = {
        "poster": lambda _b: [], "vaekninger": lambda _b: [],
        "jobs": lambda _b: [], "godkendelser": lambda _b: [],
        "planlagte": lambda _b: [], "gentagende": lambda _b: [],
        "proces_lever": lambda _p: True, "turens_wakeup_id": lambda: "",
        "backlog_tal": lambda: 0, "side_opgaver": lambda _b: [],
    }
    for n, v in kw.items():
        if n in ("poster", "vaekninger", "jobs", "godkendelser",
                 "planlagte", "gentagende", "side_opgaver"):
            tom[n] = (lambda vv: (lambda _b: vv))(v)
        elif n == "proces_lever":
            tom[n] = (lambda vv: (lambda _p: vv))(v)
        elif n in ("turens_wakeup_id", "backlog_tal"):
            tom[n] = (lambda vv: (lambda: vv))(v)
        else:
            raise AssertionError(f"ukendt kilde: {n}")
    return Kilder(**tom)


def _post(**kw) -> dict:
    d = {"id": "wake-1", "bruger_id": BJORN, "kildetype": "wakeup",
         "kilde_id": "wake-1", "oprettende_run_id": "", "verificeret_ejer":
         db_inbox.EJER_JARVIS, "kraever_handling": True,
         "status": db_inbox.STATUS_AABEN, "beskrivelse": "", "output_sti": "",
         "output_bytes": None, "paamindelser": 0, "sidste_paamindelse_at": "",
         "sidste_paamindelse_tur": "", "created_at": _iso(TID), "afgjort_at": "",
         "afgjort_grund": ""}
    d.update(kw)
    d["kilde_id"] = d["id"]
    return d


# ── Trin 1: forfald som et TAL ──────────────────────────────────────────────

def test_en_forfalden_post_baerer_sit_forfald_som_et_TAL():
    """Skygge-registret VIDSTE at `event_trigger` var 78 dage over sin frist.
    Ingen visning gjorde det til et tal nogen så. Det er fejlen her."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(created_at=_iso(TID - 3 * DAG), beskrivelse="foelg op paa brief")]))
    post = v["venter_paa_dig"][0]
    assert post["forfalden_dage"] == 3
    assert "3d forfalden" in post["linje"]


def test_et_UPARSABELT_tidsstempel_giver_None_ikke_NUL_dage():
    """Fald mod det der kan ses. Blev et ulæseligt tidsstempel 0 dage, ville en
    forfalden post se ud som «lige nu» og forsvinde i støjen."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(created_at="i gaar en gang")]))
    post = v["venter_paa_dig"][0]
    assert post["forfalden_dage"] is None
    assert "forfalden" not in post["linje"]


# ── Trin 4: dubletter ───────────────────────────────────────────────────────

def test_tre_identiske_vaekninger_vises_som_EN_med_et_tal():
    """Grupper kun PRÆSENTATIONEN; bevar alle tre vækningers id'er. Hver kan
    fyre eller annulleres selvstændigt, og lighed på (type, beskrivelse) er et
    forslag om dublet — ikke et bevis."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(vaekninger=[
        {"wakeup_id": f"wake-{i}", "status": "pending", "user_id": BJORN,
         "prompt": "maal cheap-lane", "scheduled_at": _iso(TID)} for i in range(3)]))
    assert len(v["paa_vej"]) == 1
    assert v["paa_vej"][0]["dubletter"] == 3
    assert len(v["paa_vej"][0]["kilde_ider"]) == 3
    linje = v["paa_vej"][0]["linje"]
    assert "booket 3 gange" in linje
    # PRAECIS én gang. Foerste udgave af denne test ledte bare efter
    # delstrengen — og den findes OGSAA i den braekkede tekst
    # «booket 2 gange booket 3 gange», fordi implementeringen TILFOEJEDE til
    # den forrige linje i stedet for at bygge den om. Med rigtige data stod
    # der «booket 2 gange booket 3 gange booket 4 gange»; med tre dubletter i
    # testen saa det rigtigt ud. Et tjek der ikke kan skelne de to maaler
    # ingenting.
    assert linje.count("booket") == 1, f"dublet-teksten akkumulerer: {linje!r}"


def test_poster_UDEN_beskrivelse_grupperes_ikke():
    """Uden beskrivelse er der intet at gruppere på. Grupperedes de alligevel,
    ville to urelaterede jobs blive én linje — og det ene forsvinde."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(vaekninger=[
        {"wakeup_id": f"wake-{i}", "status": "pending", "user_id": BJORN,
         "prompt": "", "scheduled_at": _iso(TID)} for i in range(2)]))
    assert len(v["paa_vej"]) == 2


# ── Trin 5: forældreløse poster ─────────────────────────────────────────────

def test_et_job_hvis_proces_er_vaek_staar_som_FORAELDRELOEST():
    """Uden dette står et dødt job som «kører» i dagevis — samme fejl som det
    stale `connected=True`: en tilstand ingen opdaterer, fordi den der skulle,
    selv døde."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "job-a71f3", "status": "kører", "pid": 4242,
               "sekunder": int(2 * DAG), "navn": "mobil-build"}],
        proces_lever=False))
    post = v["venter_paa_dig"][0]
    assert post["status"] == "foraeldreloes"
    assert post["id"] not in [x["id"] for x in v["i_gang"]], \
        "et doedt job stod stadig under «I GANG»"


def test_et_job_paa_en_UTILGAENGELIG_host_er_status_ukendt_ikke_doedt():
    """Forældreløs kræver pålideligt procesbevis fra den SAMME host. Et job på
    en operator-maskine vi ikke kan nå er ikke bevist dødt — og forskellen er
    «ryd op» mod «du må kigge selv»."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "job-fjern", "status": "kører", "pid": 99,
               "sekunder": int(2 * DAG), "navn": "fjernt job"}],
        proces_lever=None))
    assert v["venter_paa_dig"][0]["status"] == "status_ukendt"


def test_et_UNGT_job_med_doed_pid_er_ikke_foraeldreloest_endnu():
    """Under tærsklen kan en pid-læsning ramme hullet mellem fork og
    registrering. Et nyt job må ikke udnævnes til dødt på et kapløb."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "job-ny", "status": "kører", "pid": 1, "sekunder": 3,
               "navn": "lige startet"}],
        proces_lever=False))
    # Den maa ikke udnaevnes til foraeldreloes — men den skal stadig VISES som
    # det kilden siger. Foerste udgave af denne test forlangte at den forsvandt
    # helt; det var min fejl, og den ville have skjult et koerende job.
    assert v["venter_paa_dig"] == []
    assert [x["status"] for x in v["i_gang"]] == ["koerer"]


def test_et_LEVENDE_job_staar_under_i_gang():
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "job-b1vvm", "status": "kører", "pid": 1, "sekunder": 180,
               "navn": "suite paa branchen"}],
        proces_lever=True))
    assert [p["id"] for p in v["i_gang"]] == ["job-b1vvm"]
    assert v["venter_paa_dig"] == []


@pytest.mark.parametrize(
    "kilde",
    ["tool", "tool_operator", "agent", "shell", "shell_operator"],
)
def test_en_kilde_UDEN_pid_er_i_gang_ikke_venter(kilde):
    """En kilde uden pid er et KALD, ikke en proces.

    `lever is None` er kun et SVAR når der er en pid at spørge om. Bærer
    jobbet ingen pid, er grenen en tautologi — den svarer «kan ikke afgøres»
    på et spørgsmål der aldrig blev stillet. `proces_lever(None) == None` må
    derfor ikke læses som usikkerhed.

    Den ægte klasse er `supervisor` og `operator`, der BEGGE bærer en pid —
    se modprøven nedenfor. De pid-løse kilder er fem, alle målt 4/10-2026:

    * `tool` — `venter_paa_dig: [('bash#1791092371', 'status_ukendt')]`
    * `tool_operator` — samme form, men `== "tool"` slap den forbi, og
      `operator_bash` er netop den vej desk-broen bruger
    * `agent`, `shell`, `shell_operator` — `pid: None` i kilden

    Uden grenen lander hvert kørende kald i «VENTER PÅ DIG», og fordi id'et
    er `<værktøj>#<epoch>` skifter det hvert kald, så `drop` aldrig rammer
    det.
    """
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": f"{kilde}#1791092371", "kilde": kilde,
               "status": "running", "pid": None, "sekunder": 2,
               "navn": "Kald indbakken"}],
        proces_lever=None))
    assert [p["id"] for p in v["i_gang"]] == [f"{kilde}#1791092371"]
    assert v["venter_paa_dig"] == [], \
        f"et koerende kald (kilde={kilde}) stod i VENTER PAA DIG"


def test_en_supervisor_MED_pid_beholder_den_AEgte_behandling():
    """Modprøven: reglen må ikke sluge den klasse den er lavet ved siden af.

    En supervisor med en pid vi ikke kan nå ER «kan ikke afgøres» — det er
    præcis den forskel grenen skal bevare. Uden denne test kunne `er_kald`
    gøres sand for alt, og den anden test ville stadig bestå.
    """
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "sup-1", "kilde": "supervisor", "status": "running",
               "pid": 4242, "sekunder": 10,
               "navn": "paa en host vi ikke naar"}],
        proces_lever=None))
    assert v["i_gang"] == []
    assert [p["id"] for p in v["venter_paa_dig"]] == ["sup-1"]
    assert v["venter_paa_dig"][0]["status"] == "status_ukendt"


def test_et_job_med_exit_0_staar_slet_ikke():
    """Et færdigt job der gik godt kræver ingenting. Stod det der, ville
    panelet fyldes med det der ER i orden — og så lukker man det."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "job-ok", "status": "exited", "exit_code": 0, "navn": "ok"}]))
    alle = [x["id"] for s in ("venter_paa_dig", "i_gang", "paa_vej") for x in v[s]]
    assert alle == []


def test_et_job_med_exit_1_staar_som_FEJLET_med_sin_exit_kode():
    """`exit 1` er et andet signal end `exit 0` og skal stå uden at man åbner
    noget."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "job-bglj7", "status": "exited", "exit_code": 1,
               "navn": "hele suiten", "sekunder": 960}]))
    post = v["venter_paa_dig"][0]
    assert post["status"] == "fejlet"
    assert "exit 1" in post["linje"]


# ── Trin 6: bruger-isolation ────────────────────────────────────────────────

def test_en_anden_brugers_poster_siver_ALDRIG_ind():
    """Husstanden har flere brugere, og de andres workspaces er krypterede. En
    indbakke der blander dem er et databrud, ikke en fejl i visningen."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(vaekninger=[
        {"wakeup_id": "wake-mine", "status": "pending", "user_id": BJORN,
         "prompt": "min", "scheduled_at": _iso(TID)},
        {"wakeup_id": "wake-andens", "status": "pending", "user_id": ANDEN,
         "prompt": "andens", "scheduled_at": _iso(TID)}]))
    alle = [x["id"] for s in v.values() if isinstance(s, list) for x in s]
    assert alle == ["wake-mine"], f"en anden brugers post kom med: {alle}"


def test_en_vaekning_UDEN_ejer_gater_ikke():
    """`list_wakeups()` er global og har poster uden `user_id`. De må vises,
    men aldrig som `[dig]` — en stiltiende fallback til Bjørn ville gøre enhver
    ejerløs post til en blokering."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(vaekninger=[
        {"wakeup_id": "wake-ejerloes", "status": "pending", "user_id": "",
         "prompt": "uden ejer", "scheduled_at": _iso(TID)}]))
    post = v["paa_vej"][0]
    assert post["ejer"] == db_inbox.EJER_UKENDT
    assert post["kraever_handling"] is False
    assert "[ukendt]" in post["linje"]


def test_UDEN_bruger_id_er_svaret_en_TYPET_fejl():
    """Aldrig en liste over alle brugere. `list_pending_for_current_user()`
    læser alle ved tom kontekst — det er præcis den fælde."""
    for tom in ("", "   ", None):
        r = byg_indbakke(tom, nu_ts=TID, kilder=_kilder())
        assert r["status"] == "fejl" and "error" in r


# ── Trin 8: henvisning, aldrig payload ──────────────────────────────────────

def test_posten_baerer_en_henvisning_og_aldrig_payload():
    """Et jobs output kan være 112 kB. Lander det i visningen, lander det i
    promptens hale — og så er kontrolfladen blevet den byrde den skulle lette.
    Pinner BEGGE retninger: med fil og uden."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
        _post(id="job-bglj7", kildetype="job", beskrivelse="hele suiten",
              output_sti="tasks/bglj7.output", output_bytes=114_688),
        _post(id="wake-6e201", beskrivelse="foelg op")]))
    med, uden = v["venter_paa_dig"][0]["linje"], v["venter_paa_dig"][1]["linje"]
    # Henvisning OG stoerrelse — stoerrelsen goer valget mellem `tail -5` og
    # hele filen muligt uden at aabne noget.
    assert "tasks/bglj7.output" in med and "112 kB" in med
    assert "Traceback" not in med
    assert len(med) < 200, "en linje per post — ikke et uddrag"
    # Uden fil: typet kilde-id, ingen opdigtet sti.
    assert "wake-6e201" in uden
    assert ".output" not in uden and "None" not in uden


def test_en_FORSVUNDET_fil_siger_det_frem_for_at_skrive_0_B():
    """`0 B` og «væk» kan ikke mappes sammen: stod der `0 B`, ville man åbne en
    fil der ikke findes og tro at jobbet ikke skrev noget."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
        _post(id="job-vaek", output_sti="tasks/vaek.output", output_bytes=None)]))
    linje = v["venter_paa_dig"][0]["linje"]
    assert "tasks/vaek.output" in linje
    assert "stoerrelse ukendt" in linje
    assert "0 B" not in linje


def test_en_fil_paa_NUL_bytes_er_et_aegte_svar():
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
        _post(id="job-tom", output_sti="tasks/tom.output", output_bytes=0)]))
    assert "0 B" in v["venter_paa_dig"][0]["linje"]


def test_en_sti_UDEN_FOR_workspacet_vises_IKKE_men_posten_goer():
    """Global Constraint: en sti må ikke læses uden for brugerens autoriserede
    workspace. Posten vises stadig — ellers kunne gaten omgås ved at lægge
    artefaktet et forbudt sted."""
    for sti in ("/etc/shadow", "/home/bs/.jarvis-v2/workspaces/anden/x.output",
                "../../../etc/passwd"):
        v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
            _post(id="job-uden", output_sti=sti, output_bytes=10)]))
        post = v["venter_paa_dig"][0]
        assert post["id"] == "job-uden"
        assert post["output_sti"] == "", f"{sti} blev vist"
        assert sti not in post["linje"]


def test_en_MEGET_LANG_beskrivelse_afkortes_i_LINJEN_men_ikke_i_posten():
    lang = "x" * 500
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
        _post(beskrivelse=lang)]))
    post = v["venter_paa_dig"][0]
    assert len(post["linje"]) < 200
    assert post["beskrivelse"] == lang, "den GEMTE post blev afkortet"


# ── «VAKTE DENNE TUR» ───────────────────────────────────────────────────────

def test_vakte_er_TOM_i_en_tur_han_selv_startede():
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(beskrivelse="noget")], turens_wakeup_id=""))
    assert v["vakte"] == []


def test_vakte_har_PRAECIS_EN_linje_naar_en_vaekning_udloeste_turen():
    """Når en vækning starter en tur, skal turen vide HVILKEN — ellers står
    Jarvis med en opgave uden at vide hvorfor han er i gang."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(id="wake-6e201", beskrivelse="foelg op paa brief"),
                _post(id="wake-andet", beskrivelse="noget andet")],
        turens_wakeup_id="wake-6e201"))
    assert [p["id"] for p in v["vakte"]] == ["wake-6e201"]


# ── Sektionernes adskillelse ────────────────────────────────────────────────

def test_engangs_og_GENTAGENDE_opgaver_staar_i_HVER_SIN_sektion():
    """`scheduled_tasks` fyrer ÉN gang; kun `recurring_tasks` gentager sig.
    Blandedes de, ville indbakken overdrive hvor meget der venter — og så
    bliver den noget man lukker i stedet for at læse."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        planlagte=[{"id": "sched-c81d4", "beskrivelse": "skygge-review"}],
        gentagende=[{"id": "rec-67e42", "beskrivelse": "morgenbrief",
                     "interval_minutes": 1440}]))
    assert [p["id"] for p in v["paa_vej"]] == ["sched-c81d4"]
    assert [p["id"] for p in v["planlagte"]] == ["rec-67e42"]
    assert "hver 1440m" in v["planlagte"][0]["linje"]


def test_en_beslutnings_post_baerer_MIT_maerke_uden_at_paastaa_gating():
    """Ejer-mærket og gate-flaget er to forskellige spørgsmål.

    `_post` udledte `kraever_handling` af EJEREN alene, mens skriveren
    (`inbox_state.registrer_kilde`) også kræver at kildetypen ikke står i
    `IKKE_GATENDE_KILDETYPER`. Da beslutnings-posterne blev mærket `[dig]`,
    ville visningen derfor påstå at de krævede handling — mens gaten, der læser
    rækkens EGET flag, aldrig kunne nægte på dem. To svar om samme post.
    """
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
        _post(id="dec_krit", kildetype="decision",
              verificeret_ejer=db_inbox.EJER_JARVIS, kraever_handling=False,
              beskrivelse="[kritisk 0%] en kritisk",
              created_at=_iso(TID - DAG))]))
    post = v["venter_paa_dig"][0]
    assert post["id"] == "dec_krit"
    assert post["ejer_maerke"] == "[dig]", "min EGEN beslutning staar ikke som min"
    assert post["kraever_handling"] is False, (
        "visningen paastaar at en beslutning gater — gaten kan ikke naegte paa den")


def test_godkendelser_er_SYNLIGE_men_gater_ALDRIG():
    """Han skal kunne se at en tråd venter på Bjørn, uden at Bjørns svartid
    bliver Jarvis' blokering."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(godkendelser=[
        {"request_id": "appr-4b2", "approval_state": "pending",
         "summary": "commit til main", "created_at": _iso(TID - DAG)}]))
    post = v["venter_paa_bjorn"][0]
    assert post["id"] == "appr-4b2"
    assert post["kraever_handling"] is False
    assert post["ejer"] == db_inbox.EJER_HUSET
    assert v["venter_paa_dig"] == []


def test_BJOERNS_post_skelnes_fra_MINE():
    """Bjørn 4/10-2026: «den skal skelne dine og mine — så du ved hvad er til
    dig og hvad er til dig du skal minde mig om.»

    Uden grenen gik HVER åben post i `venter_paa_dig`, uanset ejer. Så stod
    hans egen flagging som noget JEG skyldte — og overskriften løj: i prompten
    betyder «dig» MIG, i `inbox`-værktøjet betyder den HAM.

    Testen maaler begge veje: hans post maa ikke staa i min sektion, og min
    maa ikke staa i hans. Kun den ene vej ville gaa igennem en gren der bare
    flyttede ALT over i `venter_paa_bjorn`.
    """
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
        _post(id="bug-9f2a", kildetype="flag", verificeret_ejer=db_inbox.EJER_BRUGER,
              kraever_handling=False, beskrivelse="railens farve er forkert"),
        _post(id="wake-77c1", kildetype="wakeup",
              verificeret_ejer=db_inbox.EJER_JARVIS,
              beskrivelse="foelg op paa brief"),
    ]))
    assert [p["id"] for p in v["venter_paa_bjorn"]] == ["bug-9f2a"]
    assert [p["id"] for p in v["venter_paa_dig"]] == ["wake-77c1"]
    assert v["venter_paa_bjorn"][0]["ejer_maerke"] == "[bjørn]"
    assert v["venter_paa_bjorn"][0]["kraever_handling"] is False


def test_en_vaekning_der_ALLEEREDE_staar_i_bjoern_sektionen_dubles_ikke():
    """Sektion 2 læser vækning-kilden og springer over hvad den durable post
    bærer. Undlod den `venter_paa_bjorn` i det tjek, stod samme vækning to
    steder — én gang fra rækken, én gang fra kilden."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(id="wake-3a1f", kildetype="wakeup",
                      verificeret_ejer=db_inbox.EJER_BRUGER,
                      kraever_handling=False, beskrivelse="husk at ringe")],
        vaekninger=[{"wakeup_id": "wake-3a1f", "user_id": BJORN,
                     "status": "fired", "prompt": "husk at ringe",
                     "scheduled_at": _iso(TID - DAG), "fired_at": _iso(TID)}]))
    assert [p["id"] for p in v["venter_paa_bjorn"]] == ["wake-3a1f"]
    assert v["venter_paa_dig"] == []


def test_backlog_er_ET_TAL_og_ikke_1896_linjer():
    """1.896 poster, 99 % gentagelser, ville drukne den dag ét."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(backlog_tal=1896))
    assert v["backlog_tal"] == 1896
    assert all(not isinstance(v.get(s), list) or len(v[s]) == 0
               for s in ("venter_paa_dig", "paa_vej"))


def test_alle_SEKS_sektioner_findes_altid():
    """«Første udkast skrev de fire sektioner» — og det var forkert allerede da.
    Tallet står nu med navnene, så det ikke kan drive igen."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder())
    for navn in ("vakte", "venter_paa_dig", "i_gang", "paa_vej",
                 "planlagte", "venter_paa_bjorn"):
        assert navn in v, f"sektionen {navn} mangler"
    assert "backlog_tal" in v


# ── Trin 7: visningen må IKKE kunne skrive (AST) ────────────────────────────

_FORBUDTE_KALD = (
    "enqueue", "append_chat_message", "set_runtime_state_value",
    "due_wakeups", "build_tool_intent_approval_surface",
    "mark_wakeup_consumed", "flush_session", "effective_role",
)


def test_visningen_kalder_INTET_der_skriver():
    """`a_read_surface_can_create_what_it_reads`: «bare en visning» startede
    daemonen og nulstillede dens nedluknings-ur.

    AST, ikke tekstsøgning — et kald kunne stå i en kommentar eller i et
    docstring, og denne fils docstring NÆVNER flere af navnene med vilje.
    """
    træ = ast.parse(_KILDE.read_text())
    kaldte: set[str] = set()
    for n in ast.walk(træ):
        if isinstance(n, ast.Call):
            f = n.func
            kaldte.add(f.attr if isinstance(f, ast.Attribute)
                       else (f.id if isinstance(f, ast.Name) else ""))
        elif isinstance(n, ast.ImportFrom):
            kaldte.update(a.name for a in n.names)
    for forbudt in _FORBUDTE_KALD:
        assert forbudt not in kaldte, \
            f"inbox_view kalder {forbudt} — en laeseflade der kan skrive"


def test_visningen_kalder_ikke_background_jobs_liste():
    """`liste()` kalder `_shell_sessioner()`, der nulstiller daemonens idle-ur.
    Den er ikke ren, og den blander husets shell-sessioner ind — Bjørns aftalte
    bagdør hører ikke i en flade der kan gate.

    Vagten er snæver med vilje: `liste` er et almindeligt ord, så den ser kun
    efter `background_jobs.liste`-formen og efter en import af navnet.
    """
    træ = ast.parse(_KILDE.read_text())
    for n in ast.walk(træ):
        if isinstance(n, ast.Attribute) and n.attr == "liste":
            v = n.value
            assert not (isinstance(v, ast.Name) and "background_jobs" in v.id), \
                "inbox_view kalder background_jobs.liste — den nulstiller idle-uret"
        if isinstance(n, ast.ImportFrom) and "background_jobs" in (n.module or ""):
            assert all(a.name != "liste" for a in n.names), \
                "inbox_view importerer background_jobs.liste"


# ── Trin 9: kanalbeskeder hører ikke i indbakken ────────────────────────────

def test_kanalbeskeder_hoerer_ikke_i_indbakken():
    """En udelukkelse uden en vagt glider. Discord/Telegram/mobil er SAMTALE,
    ikke opgaver; kom de ind, ville indbakken blive en anden indbakke.

    Vagten ser på det UNPARSEDE træ (`ast.unparse`), så kommentarer og
    docstrings ikke tælles med — ellers kunne en forklaring om hvorfor de er
    udelukket selv vælte vagten.
    """
    tekst = ast.unparse(ast.parse(_KILDE.read_text())).lower()
    for forbudt in ("discord", "telegram", "chat_messages", "channel_message"):
        assert forbudt not in tekst, \
            f"inbox_view laeser {forbudt} — kanalbeskeder er samtale, ikke opgaver"


def test_en_FEJLENDE_kilde_toemmer_ikke_hele_visningen():
    """Én kilde der kaster må ikke tage de andre med. Et panel der er tomt
    fordi én læsning fejlede ser ud som «intet venter»."""
    def _kaster(_b):
        raise RuntimeError("registret er nede")

    k = _kilder(poster=[_post(beskrivelse="min post")])
    k.godkendelser = _kaster
    with pytest.raises(RuntimeError):
        # Visningen fanger IKKE for kalderen: en tavs tom sektion er vaerre end
        # en fejl. De aegte adaptere logger og returnerer tomt hver for sig —
        # det er dér fald-retningen hoerer, ikke i byg_indbakke.
        byg_indbakke(BJORN, nu_ts=TID, kilder=k)


def test_kildernes_standarder_er_SENT_bundne():
    """En dataclass-default er en KOPI af funktionsobjektet, fanget da klassen
    blev defineret. Var de bundet direkte (`= _aegte_jobs`), ville en patch af
    `inbox_view._aegte_jobs` ikke følge med — og `slots=True` gør at
    klasse-attributten heller ikke kan patches.

    Det kostede en runde: mine værktøjstests nåede de ÆGTE vækninger og jobs
    fra udviklingsmaskinen, fire poster hvor de forventede nul. En test der
    læser levende tilstand måler noget andet hver gang.
    """
    import core.services.inbox_view as iv
    k = Kilder()
    assert k.jobs("x") is not None
    _rigtig = iv._aegte_jobs
    try:
        iv._aegte_jobs = lambda _b: [{"id": "job-patchet"}]
        assert [j["id"] for j in Kilder().jobs("x")] == ["job-patchet"], \
            "standarden er bundet til en KOPI — en patch af modulet naar den ikke"
    finally:
        iv._aegte_jobs = _rigtig


# ── Opgave 10: loft og rangorden ────────────────────────────────────────────

def _mange(n: int, sektion: str = "paa_vej") -> dict:
    """n poster i `paa_vej`, med faldende alder så ordenen kan måles."""
    return _kilder(vaekninger=[
        {"wakeup_id": f"wake-{i:02d}", "status": "pending", "user_id": BJORN,
         "prompt": f"opgave nr {i}", "scheduled_at": _iso(TID - i * DAG)}
        for i in range(n)])


def test_en_sektion_over_loftet_viser_loftet_OG_en_taelling_af_resten():
    """Argumentet der udelukkede kandidat-backloggen («1.896 poster ville
    drukne den dag ét») gælder også INDE i sektionerne."""
    from core.services.inbox_view import _SEKTION_LOFT
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_mange(_SEKTION_LOFT + 5))
    assert len(v["paa_vej"]) == _SEKTION_LOFT
    assert v["paa_vej_skjult"] == 5


def test_de_viste_er_de_AELDSTE():
    """Forfald er postens vigtigste egenskab. En post der har ventet tre dage
    er mere presserende end en der kom i morges."""
    from core.services.inbox_view import _SEKTION_LOFT
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_mange(_SEKTION_LOFT + 3))
    aldre = [p["alder_dage"] for p in v["paa_vej"]]
    assert aldre == sorted(aldre, reverse=True), f"ikke aeldste foerst: {aldre}"
    assert aldre[0] == _SEKTION_LOFT + 2, "den aeldste blev skjult"


def test_PRAECIS_loftet_giver_INGEN_skjult_linje():
    """«+0 mere» er en løgn i formen af et tal."""
    from core.services.inbox_view import _SEKTION_LOFT
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_mange(_SEKTION_LOFT))
    assert len(v["paa_vej"]) == _SEKTION_LOFT
    assert "paa_vej_skjult" not in v


def test_loftet_PLUS_EN_skjuler_praecis_den_rigtige():
    from core.services.inbox_view import _SEKTION_LOFT
    n = _SEKTION_LOFT + 1
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_mange(n))
    assert v["paa_vej_skjult"] == 1
    vist = {p["id"] for p in v["paa_vej"]}
    # Den YNGSTE er den skjulte — wake-00 har alder 0.
    assert "wake-00" not in vist
    assert f"wake-{n - 1:02d}" in vist, "den aeldste blev skjult i stedet"


def test_den_BLOKERENDE_sektion_afkortes_ALDRIG():
    """En skjult blokerende post er en usynlig blokering. Testen beviser at
    loftet ikke GÆLDER dér — ikke bare at det er stort nok."""
    from core.services.inbox_view import _SEKTION_LOFT, _UDEN_LOFT
    n = _SEKTION_LOFT * 3
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[
        _post(id=f"job-{i:02d}", kildetype="job", beskrivelse=f"nr {i}",
              created_at=_iso(TID - i * DAG)) for i in range(n)]))
    assert "venter_paa_dig" in _UDEN_LOFT
    assert len(v["venter_paa_dig"]) == n, "en blokerende post blev skjult"
    assert "venter_paa_dig_skjult" not in v


def test_TOMME_sektioner_er_tomme_lister_ikke_overskrifter():
    """En overskrift med nul linjer fylder i prompten og siger ingenting.
    Værktøjet udelader dem; visningen leverer dem som tomme lister."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder())
    for navn in ("venter_paa_dig", "i_gang", "paa_vej", "planlagte"):
        assert v[navn] == []
        assert f"{navn}_skjult" not in v


def test_SAMME_alder_giver_en_DETERMINISTISK_orden():
    """Poster med samme alder ville ellers flakke mellem ture — og en visning
    der flakker buster prompt-cachen fra sit eget sted og alt efter den."""
    kilder = _kilder(vaekninger=[
        {"wakeup_id": f"wake-{b}", "status": "pending", "user_id": BJORN,
         "prompt": f"opgave {b}", "scheduled_at": _iso(TID)}
        for b in ("c", "a", "b")])
    a = [p["id"] for p in byg_indbakke(BJORN, nu_ts=TID, kilder=kilder)["paa_vej"]]
    b = [p["id"] for p in byg_indbakke(BJORN, nu_ts=TID, kilder=kilder)["paa_vej"]]
    assert a == b == ["wake-a", "wake-b", "wake-c"], f"ordenen flakkede: {a} vs {b}"


def test_et_UPARSABELT_tidsstempel_sorterer_SIDST_ikke_foerst():
    """Alderen er `None`. Sorterede den øverst, kunne et ødelagt tidsstempel
    skubbe en reelt gammel post ud under loftet."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(vaekninger=[
        {"wakeup_id": "wake-skrald", "status": "pending", "user_id": BJORN,
         "prompt": "uden tid", "scheduled_at": "aldrig"},
        {"wakeup_id": "wake-gammel", "status": "pending", "user_id": BJORN,
         "prompt": "tre dage", "scheduled_at": _iso(TID - 3 * DAG)}]))
    assert [p["id"] for p in v["paa_vej"]] == ["wake-gammel", "wake-skrald"]


def test_dubletter_taelles_FOER_loftet():
    """Ellers kunne tre bookinger af samme vækning spise tre af de otte
    pladser og skubbe noget andet ud."""
    from core.services.inbox_view import _SEKTION_LOFT
    poster = []
    for i in range(3):
        poster.append({"wakeup_id": f"wake-dub{i}", "status": "pending",
                       "user_id": BJORN, "prompt": "SAMME TEKST",
                       "scheduled_at": _iso(TID)})
    for i in range(_SEKTION_LOFT):
        poster.append({"wakeup_id": f"wake-u{i:02d}", "status": "pending",
                       "user_id": BJORN, "prompt": f"unik {i}",
                       "scheduled_at": _iso(TID - i * DAG)})
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(vaekninger=poster))
    # 8 unikke + 1 gruppe = 9 grupper, altsaa én skjult — ikke tre.
    assert v["paa_vej_skjult"] == 1, f"loftet taalte raa poster: {v.get('paa_vej_skjult')}"


# ── Jarvis' review 4/10-2026: `drop` skrev en afgørelse visningen ikke læste ──

def test_en_AFGJORT_post_forsvinder_fra_visningen_for_HVER_kilde():
    """Jarvis fandt den, og han havde ret på alle fire punkter.

    Han lukkede tre poster. Vækningen forsvandt — fordi `mark_wakeup_consumed`
    ændrer vækningens EGEN status i kilden. De to jobs stod der stadig som
    `fejlet`, fordi job-grenen læser jobbets egen status og **aldrig**
    konsulterer `inbox_items`. `drop` skrev altså en afgørelse visningen ikke
    læste.

    Og der var ingen vagt: `grep drop tests/test_inbox_view.py` gav nul træf.
    Min egen nye test målte at OPSLAGET lykkedes — ikke at posten forsvandt.
    Præcis den fejl jeg selv lavede med chunk-testen: en grøn test der ikke kan
    fejle.

    Derfor måler denne for HVER kilde, ikke kun for jobs. En rettelse der kun
    lukker job-grenen ville efterlade den næste kilde med samme hul.
    """
    afgjort = _post(id="job-droppet", kildetype="job",
                    status=db_inbox.STATUS_DROP, beskrivelse="stale")
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[afgjort],
        jobs=[{"id": "job-droppet", "status": "exited", "exit_code": 1,
               "navn": "stale", "sekunder": 10}],
        vaekninger=[{"wakeup_id": "wake-droppet", "status": "fired",
                     "user_id": BJORN, "prompt": "lukket"}]))
    alle = [p["id"] for s in v.values() if isinstance(s, list) for p in s]
    assert "job-droppet" not in alle, \
        "et DROPPET job staar stadig i visningen — drop skrev i ingenting"


def test_en_afgjort_VAEKNING_forsvinder_ogsaa_naar_kilden_stadig_siger_fired():
    """`mark_wakeup_consumed` kan fejle eller være sprunget over (et job har
    ingen kvittering). Så afgørelsen i `inbox_items` SKAL alene være nok —
    ellers afhænger lukningen af at kilden samarbejder."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(id="wake-lukket", kildetype="wakeup",
                      status=db_inbox.STATUS_DONE)],
        vaekninger=[{"wakeup_id": "wake-lukket", "status": "fired",
                     "user_id": BJORN, "prompt": "er kvitteret"}]))
    alle = [p["id"] for s in v.values() if isinstance(s, list) for p in s]
    assert "wake-lukket" not in alle


def test_en_DIREKTE_kvitteret_vaekning_lukker_ogsaa_naar_raekken_staar_AABEN():
    """Den MODSATTE retning af testen ovenfor — og den jeg selv ramte live.

    `inbox_done` lukker begge sider, men `mark_wakeup_consumed` kaldt DIREKTE
    ændrer kun vækningens egen status. Rækken blev stående `aaben` med tomt
    `afgjort_at`, og `liste_aktiv` bevarer netop rækker UDEN lukke-tidspunkt
    for evigt: posten stod i VENTER PÅ DIG permanent, og `done` svarede
    «allerede» fordi vækningen var terminal — så den kunne ikke engang lukkes
    bagefter.

    Målt 4/10-2026 på tre rækker: `wake-0e7892004e`, `wake-9e550077c0`,
    `wake-feec8eb4ea` — alle `status='aaben'`, alle med vækningen `consumed`.
    """
    for status in ("consumed", "cancelled"):
        v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
            poster=[_post(id="wake-lukket", kildetype="wakeup",
                          status=db_inbox.STATUS_AABEN,
                          verificeret_ejer=db_inbox.EJER_UKENDT,
                          kraever_handling=False)],
            vaekninger=[{"wakeup_id": "wake-lukket", "status": status,
                         "user_id": BJORN, "prompt": "kvitteret direkte"}]))
        alle = [p["id"] for s in v.values() if isinstance(s, list) for p in s]
        assert "wake-lukket" not in alle, \
            f"raekken stod AABEN mens vaekningen var {status}"


def test_en_FYRET_vaekning_med_AABEN_raekke_bliver_staaende():
    """Modprøven. Uden den kunne fixet skjule enhver vækning der HAR en række,
    og så ville VENTER PÅ DIG tømme sig selv — en gate der aldrig gater."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(id="wake-aaben", kildetype="wakeup",
                      status=db_inbox.STATUS_AABEN)],
        vaekninger=[{"wakeup_id": "wake-aaben", "status": "fired",
                     "user_id": BJORN, "prompt": "venter"}]))
    assert "wake-aaben" in [p["id"] for p in v["venter_paa_dig"]]


def test_en_vaekning_med_UKENDT_status_skjules_ikke():
    """Listen over terminale statusser er POSITIV med vilje. En status vi ikke
    kender skal lade posten stå — ellers kunne en ny status i kilden fjerne en
    post i stilhed, hvilket er den fejlform hele dette spor handler om."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        poster=[_post(id="wake-ny", kildetype="wakeup",
                      status=db_inbox.STATUS_AABEN)],
        vaekninger=[{"wakeup_id": "wake-ny", "status": "noget-nyt",
                     "user_id": BJORN, "prompt": "ukendt status"}]))
    assert "wake-ny" in [p["id"] for p in v["venter_paa_dig"]]


def test_en_TERMINAL_vaekning_uden_durabel_raekke_goer_INGEN_skade():
    """En vækning kan være terminal uden at have en række (ældre end
    skriveren). Sættet er så bare uden virkning — det må ikke kaste."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        vaekninger=[{"wakeup_id": "wake-uden-raekke", "status": "consumed",
                     "user_id": BJORN, "prompt": "gammel"}]))
    alle = [p["id"] for s in v.values() if isinstance(s, list) for p in s]
    assert "wake-uden-raekke" not in alle
    assert v["status"] == "ok"


def test_en_UDLOEBET_og_en_kilde_afsluttet_post_forsvinder_ogsaa():
    """Opgave 8 og 9's terminale tilstande er også afgørelser. Var kun
    `done`/`drop` dækket, ville en udløbet post stå for evigt."""
    for status in (db_inbox.STATUS_UDLOEBET, db_inbox.STATUS_AFSLUTTET_AF_KILDE):
        v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
            poster=[_post(id="job-t", kildetype="job", status=status)],
            jobs=[{"id": "job-t", "status": "exited", "exit_code": 1,
                   "navn": "t", "sekunder": 10}]))
        alle = [p["id"] for s in v.values() if isinstance(s, list) for p in s]
        assert "job-t" not in alle, f"{status} stod stadig i visningen"


def test_en_AABEN_post_bliver_naturligvis_staaende():
    """Modprøven. Uden den kunne rettelsen være «skjul alt fra kilderne», og
    så ville indbakken være tom — en gate der aldrig gater."""
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(
        jobs=[{"id": "job-aaben", "status": "exited", "exit_code": 1,
               "navn": "fejlet nu", "sekunder": 10}]))
    assert "job-aaben" in [p["id"] for p in v["venter_paa_dig"]]


def test_den_AEGTE_adapter_leverer_ogsaa_de_AFGJORTE_raekker(monkeypatch, tmp_path):
    """Mutations-prøve: uden den kunne `_aegte_poster` gå tilbage til kun at
    hente åbne rækker, og hele rettelsen ovenfor ville være virkningsløs.

    Alle de andre tests sender `poster=` direkte ind og springer adapteren
    over — en mock på netop den søm der kan brække. Her kører den mod en
    RIGTIG sqlite, så det er `liste_aktiv` mod `liste` der måles.
    """
    import sqlite3
    from contextlib import contextmanager

    from core.runtime import db_inbox as dbi
    from core.services import inbox_view as iv

    sti = tmp_path / "v.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(dbi, "connect", _connect)
    monkeypatch.setattr(dbi, "_skema_klar", False)
    dbi.opret_eller_hent(bruger_id=BJORN, kildetype="job", kilde_id="job-lukket",
                         beskrivelse="stale")
    dbi.afgoer(bruger_id=BJORN, kilde_id="job-lukket",
               ny_status=dbi.STATUS_DROP, grund="stale")

    hentet = {p["id"]: p["status"] for p in iv._aegte_poster(BJORN)}
    assert hentet.get("job-lukket") == dbi.STATUS_DROP, \
        "adapteren leverer ikke de afgjorte — visningen kan ikke se en lukning"

    # Og hele vejen igennem: jobbet staar stadig `exited` i sin egen kilde,
    # men posten er afgjort, saa det maa IKKE vises.
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda _b: [])
    monkeypatch.setattr(iv, "_aegte_godkendelser", lambda _b: [])
    monkeypatch.setattr(iv, "_aegte_jobs", lambda _b: [
        {"id": "job-lukket", "status": "exited", "exit_code": 1,
         "navn": "stale", "sekunder": 99}])
    v = byg_indbakke(BJORN, nu_ts=TID)
    alle = [p["id"] for s in v.values() if isinstance(s, list) for p in s]
    assert "job-lukket" not in alle


# ── En PLANLAGT vækning venter ikke på nogen ───────────────────────────────

def test_en_PLANLAGT_vaeknings_post_staar_i_PAA_VEJ():
    """`pending` = planlagt, ikke ventende.

    Målt 4/10-2026: rækken skrives ved BOOKINGEN med `kraever_handling=True`,
    og sektion 1 lagde den derfor i VENTER PÅ DIG — hvor den også gatede — før
    vækningen overhovedet havde fyret. Sektion 2's egen regel sagde det
    modsatte; den sprang bare over, fordi rækken kom først.
    """
    k = _kilder(poster=[_post(id="wake-planlagt")],
                vaekninger=[{"wakeup_id": "wake-planlagt", "user_id": BJORN,
                             "status": "pending"}])
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=k)
    assert [p["id"] for p in v["venter_paa_dig"]] == []
    assert [p["id"] for p in v["paa_vej"]] == ["wake-planlagt"], \
        "den durable post og sektion 2 maa ikke BEGGE tilfoeje den"


def test_en_FYRET_vaeknings_post_staar_i_VENTER():
    """Den anden halvdel: en vækning der ER fyret venter faktisk på ham.

    Uden denne ville rettelsen kunne være «visningen viser den ikke længere» —
    og det er ikke det samme som at den viser den det rigtige sted.
    """
    k = _kilder(poster=[_post(id="wake-fyret")],
                vaekninger=[{"wakeup_id": "wake-fyret", "user_id": BJORN,
                             "status": "fired"}])
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=k)
    assert [p["id"] for p in v["venter_paa_dig"]] == ["wake-fyret"]
    assert [p["id"] for p in v["paa_vej"]] == []


def test_BACKLOG_tallet_er_koblet_til_en_rigtig_kilde(monkeypatch, tmp_path):
    """`Kilder.backlog_tal` stod som `lambda: 0` — den standard jeg skrev da
    jeg byggede klassen, og aldrig koblede.

    Konsekvensen: spec'ens linje «Backlog: N kandidat-forslag → …» har ALDRIG
    stået i en visning. Og et tal der altid er nul er værre end et manglende
    tal: det siger at der ikke er noget.

    Målt 4/10-2026 på CT105: 2.259 åbne instrument-fund, den ældste set
    23/6-2026. De hører ikke som POSTER — samme argument som de 1.896
    kandidater, der ville drukne fladen dag ét — men tallet skal være der.

    Fjerde gang i dette spor at en korrekt mekanisme manglede sin kilde:
    skriveren, læseren i prompten, lukkeren, og nu tælleren.
    """
    import sqlite3
    from contextlib import contextmanager

    import core.runtime.db_core as core_db
    from core.services import inbox_view as iv

    sti = tmp_path / "b.db"
    c = sqlite3.connect(sti)
    c.execute("CREATE TABLE central_instrument_findings (signature TEXT, status TEXT)")
    c.executemany("INSERT INTO central_instrument_findings VALUES (?,?)",
                  [(f"s{i}", "open") for i in range(7)] + [("lukket", "resolved")])
    c.commit()
    c.close()

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
        finally:
            k.close()

    monkeypatch.setattr(core_db, "connect", _connect)
    # KUN de aabne. En taelling der tog de lukkede med ville vokse for evigt
    # og dermed aldrig kunne falde, uanset hvad nogen ryddede.
    assert iv._aegte_backlog_tal() == 7
    assert iv.Kilder().backlog_tal() == 7, \
        "standarden er ikke bundet til kilden — tallet er tilbage paa 0"


def test_et_ULAESELIGT_backlog_tal_bliver_0_og_logges(monkeypatch, caplog):
    """Fald til 0 betyder «ingen backlog-linje», og det er ærligt. Men en
    tabel der mangler må ikke se ud som en tom backlog, så fejlen logges."""
    import logging

    import core.runtime.db_core as core_db
    from core.services import inbox_view as iv

    monkeypatch.setattr(core_db, "connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
    with caplog.at_level(logging.WARNING):
        assert iv._aegte_backlog_tal() == 0
    assert any("backloggen" in r.message for r in caplog.records), \
        "en ulaeselig backlog forsvandt i tavshed"


# ── Ejerløse kilde-rækker: husets aktivitet er IKKE alles ──────────────────

def test_en_EJERLOES_raekke_naar_kun_ejeren():
    """Målt 4/10-2026 af min egen isolations-test, som fejlede på det:
    `en-anden-bruger`s visning bar otte ægte baggrundsjob fra maskinen —
    overnight-temp-monitor, grid-bot, toku-poller og fem mere.

    `not uid` betød «hører til ALLE», og ejerløs er normen her, ikke
    undtagelsen: `visible_runs` har tomt `user_id` i alle 1037 rækker.
    `_indenfor_workspace` dækkede kun STIERNE — beskrivelserne stod frit.
    """
    ejerloest = {"id": "job-x", "navn": "grid-bot", "beskrivelse": "husets eget",
                 "status": "running", "pid": 4242}
    som_ejer = byg_indbakke(BJORN, kilder=_kilder(jobs=[ejerloest]), nu_ts=TID)
    som_anden = byg_indbakke(ANDEN, kilder=_kilder(jobs=[ejerloest]), nu_ts=TID)

    def _ider(v):
        return [p["id"] for s in v.values() if isinstance(s, list) for p in s]

    assert "job-x" in _ider(som_ejer), "ejeren mistede husets egen tilstand"
    assert _ider(som_anden) == [], (
        f"en anden brugers visning bar husets rae kker: {_ider(som_anden)}")


def test_en_raekke_med_EGEN_ejer_naar_stadig_sin_ejer():
    """Modprøven: reglen må ikke være blevet «kun ejeren ser noget»."""
    hendes = {"id": "job-h", "navn": "hendes", "beskrivelse": "hendes eget",
              "status": "running", "pid": 7, "user_id": ANDEN}
    v = byg_indbakke(ANDEN, kilder=_kilder(jobs=[hendes]), nu_ts=TID)
    assert "job-h" in [p["id"] for s in v.values() if isinstance(s, list) for p in s]
    v2 = byg_indbakke(BJORN, kilder=_kilder(jobs=[hendes]), nu_ts=TID)
    assert [p["id"] for s in v2.values() if isinstance(s, list) for p in s] == [], (
        "en fremmed ejer slap igennem til ejeren")


def test_kan_ejeren_ikke_oploeses_vises_INGEN_ejerloese(monkeypatch):
    """Den sikre retning: husets aktivitet må hellere mangle i hans indbakke
    end stå i en andens."""
    import core.services.inbox_view as iv
    monkeypatch.setattr(iv, "_ejer_id", lambda: "")
    ejerloest = {"id": "job-x", "navn": "grid-bot", "beskrivelse": "x",
                 "status": "running", "pid": 1}
    v = byg_indbakke(BJORN, kilder=_kilder(jobs=[ejerloest]), nu_ts=TID)
    assert [p["id"] for s in v.values() if isinstance(s, list) for p in s] == []


def test_en_UDLOEBET_post_er_ikke_handlingskraevende_i_visningen():
    """Visningen GENBEREGNER `kraever_handling` af ejer + kildetype.

    Uden udløbs-leddet ville den sige «kræver handling: ja» om en post hvis
    frist er passeret — mens gaten, der læser den beregnede tilstand i
    `db_inbox`, siger nej. To svar om samme post, præcis som 4/10-fejlen med
    beslutnings-posterne. Posten skal samtidig blive ved med at KUNNE LÆSES:
    udløb er en tilstand, ikke en sletning.
    """
    udloebet = _post(id="wake-udl", kilde_id="wake-udl",
                     expires_at=_iso(TID - DAG))
    v = byg_indbakke(BJORN, nu_ts=TID, kilder=_kilder(poster=[udloebet]))
    alle = [p for s in v.values() if isinstance(s, list) for p in s]
    fundet = [p for p in alle if p["id"] == "wake-udl"]
    assert fundet, "posten forsvandt — udloeb er en tilstand, ikke en sletning"
    assert fundet[0]["kraever_handling"] is False
