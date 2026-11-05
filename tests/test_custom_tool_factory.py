"""Custom-tool-fabrik: oprettelse, genindlaesning, afvisning, gate-arv."""
from __future__ import annotations

import pytest

from core.tools import custom_tool_factory as f
from core.tools.owner_approval import ejer_godkendt_kald

# Snapshot af de globale registre FØR nogen test har skrevet i dem. Bruges af
# ``isoleret`` til at fjerne det en test har tilfoejet, saa naeste test ser den
# samme verden som den foerste.
from core.tools.simple_tools import _TOOL_HANDLERS as _H
from core.tools.simple_tools_definitions import TOOL_DEFINITIONS as _D

_OPRINDELIGE_HANDLERS = frozenset(_H)
_OPRINDELIGE_DEFS = frozenset(
    str(d.get("function", {}).get("name") or "") for d in _D
)

PURE = "def run(args):\n    return {'sum': args['a'] + args['b']}\n"
SCHEMA = {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
          "required": ["a", "b"]}


@pytest.fixture(autouse=True)
def isoleret(tmp_path, monkeypatch):
    """Isolér hver test — også de globale registre.

    ``create_tool`` skriver ind i ``simple_tools._TOOL_HANDLERS`` og
    ``TOOL_DEFINITIONS``. Uden oprydning bliver et custom-navn fra én test
    staaende som "indbygget" i den naeste, og ``builtin_names()`` afviser det
    som kollision. Maalt 5/11-2026: ``add_numbers`` lækkede fra
    ``test_opret_og_kald`` og fik 6 efterfoelgende tests til at fejle.
    """
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    def _ryd():
        for navn in list(f._loaded):
            if isinstance(f._REG_TARGETS.get("handlers"), dict):
                f._REG_TARGETS["handlers"].pop(navn, None)
            _TOOL_HANDLERS.pop(navn, None)
        f._loaded.clear()
        for navn in list(_TOOL_HANDLERS):
            if navn not in _OPRINDELIGE_HANDLERS:
                _TOOL_HANDLERS.pop(navn, None)
        TOOL_DEFINITIONS[:] = [d for d in TOOL_DEFINITIONS
                               if str(d.get("function", {}).get("name") or "") in _OPRINDELIGE_DEFS]

    monkeypatch.setenv("JARVIS_CUSTOM_TOOLS_DIR", str(tmp_path / "custom_tools"))
    _ryd()
    f._REG_TARGETS.update(handlers={}, definitions=[])
    yield tmp_path
    _ryd()
    f._REG_TARGETS.update(handlers=None, definitions=None)


def test_opret_og_kald():
    r = f.create_tool("add_numbers", "Læg to tal sammen", SCHEMA, PURE)
    assert r["effect"] == "read_only" and r["approval"] == "none"
    out = f._REG_TARGETS["handlers"]["add_numbers"]({"a": 2, "b": 3})
    assert out == {"sum": 5, "status": "ok"}
    names = [d["function"]["name"] for d in f._REG_TARGETS["definitions"]]
    assert "add_numbers" in names


def test_persistens_ligger_uden_for_repo(isoleret):
    f.create_tool("add_numbers", "x", SCHEMA, PURE)
    assert (isoleret / "custom_tools" / "add_numbers.py").is_file()
    assert (isoleret / "custom_tools" / "registry.json").is_file()


def test_frisk_indlaesning_kan_stadig_kaldes():
    f.create_tool("add_numbers", "x", SCHEMA, PURE)
    # simulér genstart: al hukommelse væk, kun disken tilbage
    f._loaded.clear()
    handlers, defs = {}, []
    assert f.load_registry(handlers, defs) == ["add_numbers"]
    assert handlers["add_numbers"]({"a": 10, "b": 5})["sum"] == 15
    assert any(d["function"]["name"] == "add_numbers" for d in defs)


def test_registrering_exekverer_ikke_kroppen(isoleret, monkeypatch):
    f.create_tool("add_numbers", "x", SCHEMA, PURE)
    kald = []
    monkeypatch.setattr(f, "invoke", lambda *a, **k: kald.append(1))
    handlers = {}
    f.load_registry(handlers, [])
    assert "add_numbers" in handlers and kald == []   # registreret, ikke kørt


def test_navnekollision_afvises(monkeypatch):
    monkeypatch.setattr(f, "builtin_names", lambda: {"write_file"})
    with pytest.raises(f.ToolFactoryError, match="kolliderer"):
        f.create_tool("write_file", "x", SCHEMA, PURE)
    assert f.list_tools() == []


def test_styrevaerktoejsnavne_er_reserveret():
    assert set(f.MANAGEMENT_TOOLS) <= f.builtin_names()


@pytest.mark.parametrize("krop", [
    "def run(args:\n    return 1",                       # syntaks
    "x = 1",                                             # mangler run
    "import os\ndef run(args):\n    return os.getcwd()",
    "import subprocess\ndef run(args):\n    return 1",
    "def run(args):\n    return eval('1')",
    "def run(args):\n    return args.__class__",
    "def run(args):\n    return getattr(args, 'x')",
    "import socket\ndef run(args):\n    return 1",
    "import requests\ndef run(args):\n    return 1",     # ikke på listen
    "",
])
def test_ugyldig_krop_afvises_foer_gem(isoleret, krop):
    with pytest.raises(f.ToolFactoryError):
        f.create_tool("bad_tool", "x", SCHEMA, krop)
    assert not (isoleret / "custom_tools" / "bad_tool.py").exists()
    assert f.list_tools() == []


def test_skrivevaerktoej_arver_gaten(isoleret):
    krop = ("from pathlib import Path\n"
            "def run(args):\n"
            "    Path(args['p']).write_text('x')\n"
            "    return {'ok': True}\n")
    r = f.create_tool("writer_tool", "skriver", {"type": "object", "properties": {"p": {"type": "string"}}}, krop)
    assert r["effect"] == "non_idempotent_write" and r["approval"] == "ask"
    mål = isoleret / "out.txt"
    h = f._REG_TARGETS["handlers"]["writer_tool"]
    # uden ejer-godkendelse: blokeret, intet skrevet
    res = h({"p": str(mål)})
    assert res["status"] == "approval_needed" and not mål.exists()
    # modellen kan ikke selv godkende via argumenter
    res = h({"p": str(mål), "_runtime_trust_all": True, "owner_approved": True})
    assert res["status"] == "approval_needed" and not mål.exists()
    # med ejer-godkendelse (ContextVar) kører den
    with ejer_godkendt_kald():
        res = h({"p": str(mål)})
    assert res["status"] == "ok" and mål.read_text() == "x"


def test_governance_udledes_via_tool_definition_v2_og_classifier():
    from core.services.permission_classifier import is_mutating
    from core.tools import tool_definition_v2 as v2
    f.create_tool("add_numbers", "x", SCHEMA, PURE)
    f.create_tool("writer_tool", "x", {"type": "object", "properties": {}},
                  "def run(args):\n    open('/tmp/x', 'w').write('1')\n    return {}\n")
    assert v2._udled_effekt("add_numbers") == v2.READ_ONLY
    assert v2._udled_godkendelse("add_numbers", None) == v2.APPROVAL_NONE
    assert v2._udled_effekt("writer_tool") == v2.NON_IDEMPOTENT_WRITE
    assert v2._udled_godkendelse("writer_tool", None) == v2.APPROVAL_ASK
    assert is_mutating("writer_tool") and not is_mutating("add_numbers")


def test_manipuleret_kilde_afvises_ved_kald(isoleret):
    f.create_tool("add_numbers", "x", SCHEMA, PURE)
    (isoleret / "custom_tools" / "add_numbers.py").write_text(
        "def run(args):\n    return {'pwn': 1}\n")
    res = f._REG_TARGETS["handlers"]["add_numbers"]({"a": 1, "b": 1})
    assert res["status"] == "error" and "hash" in res["error"]
    f._loaded.clear()
    assert f.load_registry({}, []) == []       # springes over ved indlæsning


def test_sandbox_blokerer_import_ved_koersel():
    # AST-tjekket fanger det først; sandboxens import-hook er andet lag.
    with pytest.raises(ImportError):
        f._safe_import("os")


def test_styrevaerktoejer_create_list_show_delete():
    h = f.MANAGEMENT_HANDLERS
    f._REG_TARGETS["handlers"].update(h)
    r = h["create_custom_tool"]({"name": "add_numbers", "description": "d",
                                 "parameters": SCHEMA, "source": PURE})
    assert r["status"] == "ok"
    assert [t["name"] for t in h["list_custom_tools"]({})["tools"]] == ["add_numbers"]
    assert "def run" in h["show_custom_tool_source"]({"name": "add_numbers"})["source"]
    assert h["delete_custom_tool"]({"name": "add_numbers"})["deleted"] is True
    assert h["list_custom_tools"]({})["tools"] == []
    assert "add_numbers" not in f._REG_TARGETS["handlers"]
    assert h["delete_custom_tool"]({"name": "add_numbers"})["status"] == "error"


def test_styrevaerktoejer_er_owner_only():
    from core.tools.tool_scoping import OWNER_ONLY_TOOLS
    assert set(f.MANAGEMENT_TOOLS) <= OWNER_ONLY_TOOLS

