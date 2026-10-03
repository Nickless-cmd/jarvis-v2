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
        "backlog_tal": lambda: 0,
    }
    for n, v in kw.items():
        if n in ("poster", "vaekninger", "jobs", "godkendelser",
                 "planlagte", "gentagende"):
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
    assert "booket 3 gange" in v["paa_vej"][0]["linje"]


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
