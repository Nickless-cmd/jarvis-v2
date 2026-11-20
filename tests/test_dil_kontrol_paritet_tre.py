"""Paritet for DIL lag 2 (``{#each}``/``{#if}``) mellem TRE implementeringer paa flade-niveau.

Samme flade-JSON koeres gennem serverens ``_udfold_indhold`` og gennem ``kompilerFlade`` i
BAADE Desk- og mobil-klienten (``apps/*/src/lib/fladeProgram.ts``). Resultaterne skal vaere
ens: enten den samme udfoldede flade (uden ``data``), eller en fejl i alle tre.
Klienternes ``./udtryk``-import mangler filendelse, saa filerne kopieres til et tmp-dir og
importen omskrives, foer ``node --experimental-strip-types`` koerer dem.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

from core.services.jarvis_ui_guard import (
    KONTROL_MAX_DYBDE,
    KONTROL_MAX_LISTE,
    KONTROL_MAX_TEGN,
    _udfold_indhold,
)

_ROD = pathlib.Path(__file__).resolve().parent.parent
_KLIENTER = {"desk": _ROD / "apps/jarvis-desk/src/lib", "mobil": _ROD / "apps/mobile/src/lib"}

_N = KONTROL_MAX_LISTE


def _flade(tekst: str, data: object = None, *, med_data: bool = True) -> str:
    f: dict = {"type": "callout", "text": tekst}
    if med_data:
        f["data"] = data
    return json.dumps(f)


def _dyb(n: int) -> str:
    aaben = "".join(f"{{#each a som x{i}}}" for i in range(n))
    return aaben + "." + "{/each}" * n


CASES: dict[str, str] = {
    "simpel_each": _flade("{#each xs som x}[{x}]{/each}", {"xs": [1, 2, 3]}),
    "tom_liste": _flade("{#each xs som x}{x}{/each}", {"xs": []}),
    "each_dybde_2": _flade("{#each xs som x}{#each ys som y}{x}{y}{/each}{/each}", {"xs": [1, 2], "ys": ["a"]}),
    "each_dybde_3": _flade(_dyb(3), {"a": [1]}),
    "each_dybde_4_fejl": _flade(_dyb(KONTROL_MAX_DYBDE + 1), {"a": [1]}),
    "liste_praecis_loft": _flade("{#each a som x}{x},{/each}", {"a": list(range(_N))}),
    "liste_over_loft_fejl": _flade("{#each a som x}{x},{/each}", {"a": list(range(_N + 1))}),
    "tegn_over_loft_fejl": _flade("{#each a som x}" + "y" * 1000 + "{/each}", {"a": list(range(_N))}),
    "if_true": _flade("{#if a > 1}stor{:else}lille{/if}", {"a": 5}),
    "if_false": _flade("{#if a > 1}stor{:else}lille{/if}", {"a": 0}),
    "if_uden_else_false": _flade("{#if a}ja{/if}", {"a": 0}),
    "each_uden_som_fejl": _flade("{#each xs}{x}{/each}", {"xs": [1]}),
    "each_uden_navn_fejl": _flade("{#each xs som }{x}{/each}", {"xs": [1]}),
    "each_uden_luk_fejl": _flade("{#each xs som x}{x}", {"xs": [1]}),
    "ukendt_liste_fejl": _flade("{#each nope som x}{x}{/each}", {}),
    "data_er_liste_fejl": _flade("{#each xs som x}{x}{/each}", [1, 2]),
    "data_er_streng_fejl": _flade("{#each xs som x}{x}{/each}", "xs"),
    "data_er_null_fejl": _flade("{#each xs som x}{x}{/each}", None),
    "data_mangler_fejl": _flade("{#each xs som x}{x}{/each}", med_data=False),
    "data_ikke_dict_men_ingen_struktur": _flade("almindelig tekst", [1, 2]),
    "objekt_each_felter": _flade(
        "{#each rs som r}{r.navn}={r.status};{/each}",
        {"rs": [{"navn": "a", "status": "ok"}, {"navn": "b", "status": 2}]},
    ),
    "objekt_each_nested_sti": _flade("{#each rs som r}{r.d.x}/{r.l[1]};{/each}", {"rs": [{"d": {"x": 7}, "l": [1, 2]}]}),
    "objekt_each_manglende_felt_urort": _flade("{#each rs som r}{r.nope}{/each}", {"rs": [{"navn": "a"}]}),
    "objekt_each_felt_ikke_skalar_urort": _flade("{#each rs som r}{r.d}{/each}", {"rs": [{"d": {"x": 1}}]}),
    "objekt_each_med_if": _flade("{#each rs som r}{#if r.ok}J{:else}N{/if}{/each}", {"rs": [{"ok": True}, {"ok": False}]}),
    "objekt_each_liste_i_liste_fejl": _flade("{#each rs som r}{r}{/each}", {"rs": [[1]]}),
    "objekt_each_null_element_fejl": _flade("{#each rs som r}{r}{/each}", {"rs": [None]}),
    "data_fjernes": _flade("uden struktur", {"xs": [1]}),
}

_RUNNER = """
import {kompilerFlade} from %(uri)s;
const c = JSON.parse(process.argv.at(-1));
console.log(JSON.stringify(c.map((raa) => {
  const p = kompilerFlade(raa);
  return p === null ? {fejl: true, null: true} : {fejl: p.diagnostik.length > 0, rod: p.rod};
})));
"""


def _koer_klient(navn: str, tmp: pathlib.Path) -> list[dict]:
    kilde = _KLIENTER[navn]
    mappe = tmp / navn
    mappe.mkdir()
    for f in ("udtryk.ts", "delvisJson.ts"):
        (mappe / f).write_text((kilde / f).read_text().replace("'./udtryk'", "'./udtryk.ts'").replace("'./delvisJson'", "'./delvisJson.ts'"))
    flade = (kilde / "fladeProgram.ts").read_text().replace("'./udtryk'", "'./udtryk.ts'").replace("'./delvisJson'", "'./delvisJson.ts'")
    (mappe / "flade.ts").write_text(flade.replace("kompilérFlade", "kompilerFlade"))
    script = _RUNNER % {"uri": json.dumps((mappe / "flade.ts").as_uri())}
    ud = subprocess.run(
        ["node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", script, json.dumps(list(CASES.values()))],
        capture_output=True, text=True, timeout=60, cwd=tmp,
    )
    assert ud.returncode == 0, ud.stderr
    return json.loads(ud.stdout)


def _server(raa: str) -> dict:
    tekst, fejl = _udfold_indhold(raa)
    return {"fejl": bool(fejl), "rod": None if fejl else json.loads(tekst)}


@pytest.fixture(scope="module")
def klient_svar(tmp_path_factory: pytest.TempPathFactory) -> dict[str, list[dict]]:
    if shutil.which("node") is None:
        pytest.skip("node mangler")
    tmp = tmp_path_factory.mktemp("dil_paritet")
    return {navn: _koer_klient(navn, tmp) for navn in _KLIENTER}


@pytest.mark.parametrize("navn", list(CASES))
def test_tre_implementeringer_er_enige(navn: str, klient_svar: dict[str, list[dict]]) -> None:
    i = list(CASES).index(navn)
    raa = CASES[navn]
    s = _server(raa)
    for k, svar in klient_svar.items():
        k_i = svar[i]
        assert k_i["fejl"] == s["fejl"], (navn, k, "fejl-uenighed", s, k_i)
        if not s["fejl"]:
            assert k_i["rod"] == s["rod"], (navn, k, "udfoldet flade er forskellig", s, k_i)
    assert klient_svar["desk"][i] == klient_svar["mobil"][i], (navn, "desk != mobil")
    if navn.endswith("_fejl"):
        assert s["fejl"], (navn, "forventet fejl, men serveren accepterede")


def test_lofter_er_ens_i_klienterne(tmp_path: pathlib.Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node mangler")
    for navn, kilde in _KLIENTER.items():
        mappe = tmp_path / navn
        mappe.mkdir()
        (mappe / "u.ts").write_text((kilde / "udtryk.ts").read_text())
        script = (
            f"import * as m from {json.dumps((mappe / 'u.ts').as_uri())};"
            "console.log(JSON.stringify([m.KONTROL_MAX_DYBDE, m.KONTROL_MAX_LISTE, m.KONTROL_MAX_TEGN]))"
        )
        ud = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", script],
                            capture_output=True, text=True, timeout=60, cwd=tmp_path)
        assert ud.returncode == 0, ud.stderr
        assert json.loads(ud.stdout) == [KONTROL_MAX_DYBDE, KONTROL_MAX_LISTE, KONTROL_MAX_TEGN], navn
