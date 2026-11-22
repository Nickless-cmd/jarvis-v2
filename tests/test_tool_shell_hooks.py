"""Shell-hooks: blokering, fail-open og den vigtige grænse mod shell-injection.

Målt 22/11-2026: ``tool_lifecycle_hooks`` blev kaldt på hvert tool-kald, men
``register_hook`` og ``set_enabled(True)`` blev kaldt NUL steder i drift. Laget
kørte med en tom liste — indgangen fandtes, indholdet gjorde ikke.

Testene her låser fire ting, fordi det er dem der gør mekanismen ægte:
1. en hook der svarer exit 2 stopper udførelsen,
2. en hook der fejler på anden vis stopper den IKKE (fail-open),
3. argumenterne kommer som data og kan ikke blive shell-kode,
4. processens miljø lækker ikke API-nøgler ind i hooken.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from core.services import tool_lifecycle_hooks as lifecycle
from core.services import tool_shell_hooks as shell
from core.tools.tool_execution_gateway import execute_tool_call


@pytest.fixture(autouse=True)
def _ryd():
    shell._nulstil_for_test()
    lifecycle.clear_hooks()
    lifecycle.set_enabled(False)
    yield
    shell._nulstil_for_test()
    lifecycle.clear_hooks()
    lifecycle.set_enabled(False)


@pytest.fixture
def config_fil(tmp_path, monkeypatch):
    """Peg CONFIG_STI på en testfil — rør ikke maskinens rigtige config."""
    sti = tmp_path / "tool_hooks.json"
    monkeypatch.setattr(shell, "CONFIG_STI", sti)

    def skriv(hooks: list[dict], enabled: bool = True) -> pathlib.Path:
        sti.write_text(json.dumps({"enabled": enabled, "hooks": hooks}),
                       encoding="utf-8")
        shell._nulstil_for_test()
        return sti

    return skriv


def _executor(svar: dict | None = None):
    kaldt: list[bool] = []

    def execute() -> dict:
        kaldt.append(True)
        return svar if svar is not None else {"status": "ok"}

    return execute, kaldt


# ── 1. blokering ────────────────────────────────────────────────────────

def test_exit_2_blokerer_kaldet(config_fil) -> None:
    config_fil([{
        "name": "stop-alt",
        "match": "^bash$",
        "before": "cat >/dev/null; exit 2",
    }])
    assert shell.ensure_loaded() is True
    execute, kaldt = _executor()

    resultat = execute_tool_call("bash", {"command": "ls"}, execute=execute,
                                internal=False)

    assert resultat["status"] == "error"
    assert resultat["error"] == "tool_blocked_by_lifecycle_hook"
    assert kaldt == [], "execute må ikke køre når hooken blokerer"


def test_exit_0_slipper_igennem(config_fil) -> None:
    config_fil([{"name": "tillad", "match": "^bash$", "before": "cat >/dev/null; exit 0"}])
    shell.ensure_loaded()
    execute, kaldt = _executor()

    assert execute_tool_call("bash", {}, execute=execute, internal=False) == {"status": "ok"}
    assert kaldt == [True]


def test_match_rammer_kun_sit_eget_tool(config_fil) -> None:
    config_fil([{"name": "kun-bash", "match": "^bash$", "before": "cat >/dev/null; exit 2"}])
    shell.ensure_loaded()
    execute, kaldt = _executor()

    assert execute_tool_call("read_file", {}, execute=execute, internal=False) == {"status": "ok"}
    assert kaldt == [True]


# ── 2. fail-open ────────────────────────────────────────────────────────

def test_exit_1_blokerer_ikke(config_fil) -> None:
    """Kun exit 2 er en dom. En hook der fejler er en advarsel."""
    config_fil([{"name": "fejl", "match": "^bash$", "before": "cat >/dev/null; exit 1"}])
    shell.ensure_loaded()
    execute, kaldt = _executor()

    assert execute_tool_call("bash", {}, execute=execute, internal=False) == {"status": "ok"}
    assert kaldt == [True]


def test_crash_eller_manglende_kommando_blokerer_ikke(config_fil) -> None:
    config_fil([{"name": "findes-ikke", "match": "^bash$",
                 "before": "en-kommando-der-ikke-findes-xyz; exit 127"}])
    shell.ensure_loaded()
    execute, kaldt = _executor()

    assert execute_tool_call("bash", {}, execute=execute, internal=False) == {"status": "ok"}
    assert kaldt == [True]


def test_timeout_blokerer_ikke(config_fil) -> None:
    config_fil([{"name": "haenger", "match": "^bash$",
                 "before": "sleep 30", "timeout_s": 0.3}])
    shell.ensure_loaded()
    execute, kaldt = _executor()

    assert execute_tool_call("bash", {}, execute=execute, internal=False) == {"status": "ok"}
    assert kaldt == [True]


# ── 3. argumenter er data, ikke kode ────────────────────────────────────

def test_argument_kan_ikke_blive_shell_kode(config_fil, tmp_path) -> None:
    """Det vigtigste værn: et tool-argument må aldrig eksekveres som kommando.

    Argumentet indeholder en shell-injektion. Kommandoen interpolerer det ikke,
    så filen må ikke opstå. Testen fejler hvis nogen senere "forbedrer" hooken
    til at bygge kommandoen med argumentet indsat.
    """
    oensket = tmp_path / "injecteret.txt"
    config_fil([{
        "name": "las-stdin",
        "match": "^bash$",
        "before": "cat >/dev/null; exit 0",
    }])
    shell.ensure_loaded()
    execute, _ = _executor()

    execute_tool_call(
        "bash",
        {"command": f"ls; touch {oensket}; echo pwned"},
        execute=execute,
        internal=False,
    )

    assert not oensket.exists(), "argumentet blev eksekveret som shell-kode"


def test_argumenterne_naar_frem_som_json(config_fil, tmp_path) -> None:
    ud_fil = tmp_path / "set.txt"
    config_fil([{
        "name": "fang-stdin",
        "match": "^bash$",
        "before": f"cat > {ud_fil}; exit 0",
    }])
    shell.ensure_loaded()
    execute, _ = _executor()

    execute_tool_call("bash", {"command": "echo hej"}, execute=execute,
                      internal=False)

    data = json.loads(ud_fil.read_text(encoding="utf-8"))
    assert data["tool"] == "bash"
    assert data["phase"] == "before"
    assert data["arguments"] == {"command": "echo hej"}


# ── 4. miljøet lækker ikke ──────────────────────────────────────────────

def test_api_noegle_er_ikke_synlig_for_hooken(config_fil, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-hemmelig-vaerdi")
    ud_fil = tmp_path / "env.txt"
    config_fil([{
        "name": "se-miljoe",
        "match": "^bash$",
        "before": f"cat >/dev/null; env > {ud_fil}; exit 0",
    }])
    shell.ensure_loaded()
    execute, _ = _executor()

    execute_tool_call("bash", {}, execute=execute, internal=False)

    miljoe = ud_fil.read_text(encoding="utf-8")
    assert "sk-hemmelig-vaerdi" not in miljoe
    assert "JARVIS_TOOL_NAME=bash" in miljoe


# ── 5. indlæsning ───────────────────────────────────────────────────────

def test_uden_config_er_mekanismen_slukket(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(shell, "CONFIG_STI", tmp_path / "findes-ikke.json")
    shell._nulstil_for_test()

    assert shell.ensure_loaded() is False
    assert lifecycle.is_enabled() is False
    assert shell.status()["antal"] == 0


def test_enabled_false_taender_intet(config_fil) -> None:
    config_fil([{"name": "x", "match": ".", "before": "exit 2"}], enabled=False)

    assert shell.ensure_loaded() is False
    assert lifecycle.is_enabled() is False


def test_gatewayen_indlaeser_hooks_selv(config_fil) -> None:
    """Gatewayen skal indlæse config'en — ikke testen på dens vegne.

    Målt 22/11-2026: den første udgave af denne fil kaldte ``ensure_loaded()``
    i hver test. Så beviste de at hook-LAGET virker, men ikke at nogen binder
    det til et tool-kald — og en mutation der fjernede indlæsningen fra
    gatewayen blev ikke fanget (14 passed både før og efter). Netop den fejl
    filen findes for at forhindre. Derfor kalder denne test INTET andet end
    ``execute_tool_call``.
    """
    config_fil([{"name": "kun-gennem-gateway", "match": "^bash$",
                 "before": "cat >/dev/null; exit 2"}])
    execute, kaldt = _executor()

    resultat = execute_tool_call("bash", {"command": "ls"}, execute=execute,
                                internal=False)

    assert resultat["status"] == "error", "gatewayen indlæste ikke hooks"
    assert kaldt == []


def test_status_fortaeller_hvad_der_er_indlaest(config_fil) -> None:
    config_fil([{"name": "synlig", "match": "^bash$", "before": "exit 0"}])
    shell.ensure_loaded()

    st = shell.status()
    assert st["enabled"] is True
    assert st["antal"] == 1
    assert st["hooks"][0]["name"] == "synlig"
    assert st["config_findes"] is True


def test_ugyldigt_regex_taender_ikke_noget(config_fil) -> None:
    config_fil([{"name": "broken", "match": "([", "before": "exit 2"}])

    assert shell.ensure_loaded() is False
    assert "ugyldigt regex" in shell.status()["fejl"]


def test_after_hook_kan_ikke_stoppe_resultatet(config_fil) -> None:
    config_fil([{"name": "efter", "match": "^bash$", "after": "cat >/dev/null; exit 2"}])
    shell.ensure_loaded()
    execute, kaldt = _executor({"status": "ok"})

    assert execute_tool_call("bash", {}, execute=execute, internal=False) == {"status": "ok"}
    assert kaldt == [True]


def test_after_hook_modtager_bashens_faktiske_confinement(config_fil, tmp_path) -> None:
    ud_fil = tmp_path / "after.json"
    config_fil([{"name": "spor", "match": "^bash$", "after": f"cat > {ud_fil}"}])
    shell.ensure_loaded()
    execute, _ = _executor({
        "status": "ok",
        "confinement": {"requested": True, "actual": False, "honored": False},
    })

    execute_tool_call("bash", {"command": "pwd"}, execute=execute, internal=False)

    payload = json.loads(ud_fil.read_text(encoding="utf-8"))
    assert payload["arguments"]["__result__"]["confinement"] == {
        "requested": True, "actual": False, "honored": False,
    }


def test_log_rotation_beholder_en_generation(tmp_path, monkeypatch) -> None:
    log = tmp_path / "tool_hooks.jsonl"
    rotated = tmp_path / "tool_hooks.jsonl.1"
    log.write_bytes(b"new-log")
    rotated.write_bytes(b"old-log")
    monkeypatch.setattr(shell, "LOG_STI", log)
    monkeypatch.setattr(shell, "LOG_ROTATION_BYTES", 7)

    assert shell.rotate_log_if_needed() is True
    assert not log.exists()
    assert rotated.read_bytes() == b"new-log"


def test_after_hook_faar_status_ikke_hele_resultatet(config_fil, tmp_path) -> None:
    """En observatør må ikke gøre hver log-linje til en kopi af alle data.

    Uden denne grænse ville en ``read_file`` af en stor fil skrive hele
    filindholdet til hook-loggen på hvert kald — en lækage og en
    størrelsesbombe pakket som telemetri.
    """
    ud_fil = tmp_path / "set.txt"
    config_fil([{"name": "fang-efter", "match": "^bash$",
                 "after": f"cat > {ud_fil}; exit 0"}])
    shell.ensure_loaded()
    hemmelig = "x" * 5000
    execute, _ = _executor({"status": "ok", "content": hemmelig})

    execute_tool_call("bash", {}, execute=execute, internal=False)

    raa = ud_fil.read_text(encoding="utf-8")
    data = json.loads(raa)
    assert data["arguments"]["__result__"]["status"] == "ok"
    assert "bytes" in data["arguments"]["__result__"]
    assert hemmelig not in raa, "hele resultatet blev skrevet til hook-loggen"
