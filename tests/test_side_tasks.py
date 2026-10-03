from core.services import side_tasks


def test_flagged_task_stays_visible_when_activated_until_completed(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    task_id = side_tasks.flag(title="Ryd op", prompt="Ryd op i dokumenterne")["side_task_id"]
    assert [item["side_task_id"] for item in side_tasks.list_open()] == [task_id]

    side_tasks.resolve(task_id, decision="activated")
    assert [item["side_task_id"] for item in side_tasks.list_open()] == [task_id]
    assert task_id in side_tasks.side_tasks_prompt_section()

    side_tasks.resolve(task_id, decision="completed")
    assert side_tasks.list_open() == []
    assert side_tasks.side_tasks_prompt_section() is None
    assert side_tasks.resolve(task_id, decision="activated")["status"] == "error"
    assert state[0]["status"] == "completed"


def test_dismiss_tool_preserves_old_default_and_can_complete(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    first = side_tasks.flag(title="Én", prompt="Gør én ting")["side_task_id"]
    second = side_tasks.flag(title="To", prompt="Gør en anden ting")["side_task_id"]
    assert side_tasks._exec_dismiss_side_task({"side_task_id": first})["new_status"] == "dismissed"
    assert side_tasks._exec_dismiss_side_task({"side_task_id": second, "decision": "completed"})["new_status"] == "completed"
    assert side_tasks.list_open() == []


def test_dismiss_tool_rejects_unknown_decision_and_lists_open_only(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    tid = side_tasks.flag(title="Tre", prompt="Gør en tredje ting")["side_task_id"]
    # «activated» er ikke en afslutning — værktøjet må ikke kunne bruges til det.
    assert side_tasks._exec_dismiss_side_task({"side_task_id": tid, "decision": "activated"})["status"] == "error"
    side_tasks.resolve(tid, decision="activated")
    listed = side_tasks._exec_list_side_tasks({})
    assert listed["count"] == 1 and listed["side_tasks"][0]["status"] == "activated"
    assert "(i gang)" in side_tasks.side_tasks_prompt_section()


# ── Linket til den samtale der LOESER opgaven (3/10-2026) ─────────────────
#
# Bjoern: «op til trods loeste han opgave og saa maatte jeg minde ham om at
# markere den flaggede opgave faerdig». Maalt: desk starter opgaven i en NY
# samtale og saetter status til `activated` — men den nye sessions id blev
# aldrig gemt, saa INTET kunne bagefter vide at samtalen hoerte til opgaven.
# Hverken runtimen eller Jarvis selv kunne derfor lukke den.

import pytest


@pytest.fixture
def lager(monkeypatch):
    state: list = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _k, _d: list(state))
    monkeypatch.setattr(side_tasks, "save_json",
                        lambda _k, items: state.__setitem__(slice(None), items))
    return state


def test_arbejds_sessionen_gemmes_ved_aktivering(lager):
    tid = side_tasks.flag(title="Fix tests", prompt="Ret de to fejlende tests")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    assert lager[0]["arbejds_session"] == "chat-abc"
    fundet = side_tasks.arbejds_session_for("chat-abc")
    assert fundet is not None and fundet["side_task_id"] == tid


def test_en_anden_samtale_finder_ikke_opgaven(lager):
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    assert side_tasks.arbejds_session_for("chat-andet") is None
    assert side_tasks.arbejds_session_for("") is None


def test_en_LUKKET_opgave_binder_ikke_samtalen_laengere(lager):
    """Ellers ville lukke-instruksen staa i prompten for evigt."""
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    side_tasks.resolve(tid, decision="completed", lukket_af="jarvis")
    assert side_tasks.arbejds_session_for("chat-abc") is None
    assert lager[0]["lukket_af"] == "jarvis"


def test_lukke_instruksen_staar_KUN_i_arbejds_samtalen(lager):
    """Kernen i rettelsen: listen viste «(i gang)», men intet sagde hvis
    ansvar det var at lukke den. Nu staar instruksen — og kun dér hvor
    arbejdet foregaar, saa den ikke bliver stoej i alle andre ture."""
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")

    i_arbejdet = side_tasks.side_tasks_prompt_section("chat-abc")
    assert "DENNE samtale er arbejdet" in i_arbejdet
    assert f'side_task_id="{tid}"' in i_arbejdet
    assert 'decision="completed"' in i_arbejdet
    assert "Ingen anden lukker den for dig" in i_arbejdet

    andetsteds = side_tasks.side_tasks_prompt_section("chat-andet")
    assert tid in andetsteds, "listen skal stadig vises"
    assert "DENNE samtale er arbejdet" not in andetsteds

    uden_session = side_tasks.side_tasks_prompt_section()
    assert tid in uden_session
    assert "DENNE samtale er arbejdet" not in uden_session


def test_instruksen_siger_hvad_der_skal_ske_hvis_den_IKKE_kan_loeses(lager):
    """Et loefte uden en udvej bliver en tavs loegn: kan opgaven ikke loeses,
    skal han sige det frem for at lukke den."""
    tid = side_tasks.flag(title="Fix tests", prompt="Ret dem")["side_task_id"]
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-abc")
    t = side_tasks.side_tasks_prompt_section("chat-abc")
    assert "Kan den ikke loeses" in t and "lad den staa aaben" in t


def test_prompt_afsnittet_kaster_ikke_paa_en_halv_post(lager):
    """En post uden titel eller uden arbejds_session maa ikke vaelte afsnittet."""
    lager.append({"side_task_id": "side-xx", "status": "activated"})
    assert side_tasks.side_tasks_prompt_section("chat-abc") is not None
    assert side_tasks.arbejds_session_for("chat-abc") is None


# ── Forureningen: listen laestes som en arbejdsordre (3/10-2026) ──────────
#
# Bjoern: «noget forurener side-opgave sessionen! den starter hele tiden og det
# er samme opgave han laver i en anden session med mig».
#
# Maalt samme dag stod der i HVER sessions prompt:
#   [side-eea886e1e9] Giv vagtposterne en levende kanal — … Fixet er tre dele:
#   stop aesthetic-daemonens spam, flyt udgangen til send_session_notificati
# 240 tegn med fremgangsmaaden i, afkortet midt i et ord. Det er ikke et flag,
# det er en arbejdsordre.

def test_listen_siger_at_den_IKKE_er_opgaver_man_er_sat_til(lager):
    """Maerkningen. Samme tre egenskaber som vaerns-noterne: hvad listen ER,
    hvad den IKKE er, og et eksplicit forbud mod den forkerte laesning."""
    side_tasks.flag(title="Giv vagtposterne en levende kanal",
                    prompt="…", tldr="trigger-koeen er doed")
    t = side_tasks.side_tasks_prompt_section("en-anden-samtale")
    assert "HUSKELISTE" in t
    assert "ikke opgaver du er sat til" in t
    assert "IKKE begynde" in t
    assert "Ingen af dem er bedt om i denne samtale" in t


def test_tldr_afkortes_ved_en_ORDGRAENSE_og_ikke_midt_i_et_ord(lager):
    """`send_session_notificati` var det maalte symptom. En afkortet instruks
    er vaerre end ingen: den ser ud som et fuldt svar."""
    side_tasks.flag(
        title="Giv vagtposterne en levende kanal",
        prompt="…",
        tldr=("trigger-koeen er doed. Fixet er tre dele: stop "
              "aesthetic-daemonens spam, flyt udgangen til "
              "send_session_notification og luk koeen"))
    t = side_tasks.side_tasks_prompt_section()
    assert "send_session_notificati\n" not in t
    assert "send_session_notificati…" not in t, "afkortet midt i et ord"
    assert t.endswith("…") or "…" in t
    # Og fremgangsmaaden maa ikke staa der i sin helhed.
    assert "luk koeen" not in t


def test_korte_titler_og_tldr_er_UAENDREDE(lager):
    """Afkortningen maa ikke roere det der allerede er kort — ellers ville
    hver linje faa en vildledende ellipse."""
    side_tasks.flag(title="Fix badge", prompt="…", tldr="den er stale")
    t = side_tasks.side_tasks_prompt_section()
    assert "Fix badge — den er stale" in t
    assert "…" not in t


def test_kort_afkorter_ved_ord_og_rydder_tegnsaetning():
    assert side_tasks._kort("abc", 10) == "abc"
    assert side_tasks._kort("en to tre fire fem", 10) == "en to tre…"
    # Linjeskift og dobbelte mellemrum foldes, saa en flerlinjet tldr ikke
    # braekker bullet-listen.
    assert side_tasks._kort("en\n\n  to", 20) == "en to"
    # Et enkelt ord laengere end maks maa stadig afkortes.
    assert side_tasks._kort("a" * 30, 10) == "a" * 10 + "…"
