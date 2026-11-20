"""Konkret bevis for DIL lag 2: modellen leverer selv ``data`` i en jarvis-ui-flade.

Fladen bruger ``{#each}`` over en liste af skalarer (seneste runs fra ``visible_runs``) og
``{#if}`` som betingelse. Den koeres gennem ``normalisér()`` (Python) og gennem
``kompilérFlade`` (TS, Desk). Begge skal give samme udfoldede tekst, og ``data`` skal vaere
fjernet fra den tegnede flade. Fejler hvis guarden/klienten stripper ``data`` foer udfoldning.
"""
import json
import pathlib
import shutil
import sqlite3
import subprocess

import pytest

from core.services.jarvis_ui_guard import normalisér

_ROD = pathlib.Path(__file__).resolve().parent.parent
_DESK = _ROD / "apps/jarvis-desk/src/lib"
_DB = pathlib.Path("/home/bs/.jarvis-v2/state/jarvis.db")

# Snapshot af en rigtig koersel (visible_runs, nyeste foerst) — det en model ville sende.
SNAPSHOT = [
    "running visible-95faad1e4c primary",
    "completed visible-48197a0245 primary",
    "completed visible-e2caf49fad primary",
    "completed autonomous-901d3d4 primary",
]


def spec(runs: list[str], antal_fejlede: int) -> dict:
    return {
        "type": "callout",
        "title": "Seneste runs",
        "body": (
            "{#each runs som r}- {r}\n{/each}"
            "{#if antal_fejlede > 0}OBS: der er fejlede runs{:else}ingen fejlede{/if}"
        ),
        "data": {"runs": runs, "antal_fejlede": antal_fejlede},
    }


FORVENTET = (
    "- running visible-95faad1e4c primary\n"
    "- completed visible-48197a0245 primary\n"
    "- completed visible-e2caf49fad primary\n"
    "- completed autonomous-901d3d4 primary\n"
    "ingen fejlede"
)


def _python(flade: dict) -> dict:
    ud = normalisér("```jarvis-ui\n" + json.dumps(flade) + "\n```", run_id="x")
    assert ud.startswith("```jarvis-ui\n"), ud
    return json.loads(ud.removeprefix("```jarvis-ui\n").rsplit("\n```", 1)[0])


_RUNNER = """
import {kompilerFlade} from %(uri)s;
const p = kompilerFlade(process.argv.at(-1));
console.log(JSON.stringify(p === null ? null : {rod: p.rod, diag: p.diagnostik}));
"""


def _ts(flade: dict, tmp: pathlib.Path) -> dict:
    if shutil.which("node") is None:
        pytest.skip("node mangler")
    for f in ("udtryk.ts", "delvisJson.ts"):
        (tmp / f).write_text((_DESK / f).read_text().replace("'./udtryk'", "'./udtryk.ts'").replace("'./delvisJson'", "'./delvisJson.ts'"))
    src = (_DESK / "fladeProgram.ts").read_text().replace("'./udtryk'", "'./udtryk.ts'").replace("'./delvisJson'", "'./delvisJson.ts'")
    (tmp / "flade.ts").write_text(src.replace("kompilérFlade", "kompilerFlade"))
    ud = subprocess.run(
        ["node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e",
         _RUNNER % {"uri": json.dumps((tmp / "flade.ts").as_uri())}, json.dumps(flade)],
        capture_output=True, text=True, timeout=60, cwd=tmp,
    )
    assert ud.returncode == 0, ud.stderr
    svar = json.loads(ud.stdout)
    assert svar is not None and svar["diag"] == [], svar
    return svar["rod"]


def test_python_udfolder_each_og_if_og_fjerner_data() -> None:
    rod = _python(spec(SNAPSHOT, 0))
    assert rod["body"] == FORVENTET
    assert "data" not in rod


def test_desk_udfolder_each_og_if_og_fjerner_data(tmp_path: pathlib.Path) -> None:
    rod = _ts(spec(SNAPSHOT, 0), tmp_path)
    assert rod["body"] == FORVENTET
    assert "data" not in rod


def test_begge_ender_er_enige_ogsaa_naar_if_er_sand(tmp_path: pathlib.Path) -> None:
    flade = spec(["failed visible-aaaa primary"], 1)
    py, ts = _python(flade), _ts(flade, tmp_path)
    assert py["body"] == ts["body"] == "- failed visible-aaaa primary\nOBS: der er fejlede runs"
    assert py == ts


def test_live_db_runs_giver_samme_tekst_i_begge_ender(tmp_path: pathlib.Path) -> None:
    if not _DB.exists():
        pytest.skip("jarvis.db mangler")
    con = sqlite3.connect(f"file:{_DB}?mode=ro", uri=True)
    try:
        raekker = con.execute(
            "select status || ' ' || substr(run_id, 1, 18) from visible_runs order by id desc limit 5"
        ).fetchall()
        fejlede = sum(1 for (r,) in raekker if r.split()[0] in ("failed", "interrupted"))
    finally:
        con.close()
    runs = [r for (r,) in raekker]
    flade = spec(runs, fejlede)
    py, ts = _python(flade), _ts(flade, tmp_path)
    assert py["body"] == ts["body"]
    assert all(f"- {r}\n" in py["body"] for r in runs)
    assert "data" not in py and "data" not in ts


def test_hard_degradering_uden_som_navn(tmp_path: pathlib.Path) -> None:
    flade = spec(SNAPSHOT, 0)
    flade["body"] = "{#each runs}{r}{/each}"
    ud = normalisér("```jarvis-ui\n" + json.dumps(flade) + "\n```", run_id="x")
    assert "{#each" not in ud and "Seneste runs" not in ud  # blokken degraderes, ikke tegnet


def test_variabel_udenfor_each_interpoleres_ikke(tmp_path: pathlib.Path) -> None:
    """Begraensning (begge ender): ``{navn}`` erstattes kun inde i en each-krop."""
    flade = {"type": "callout", "title": "t", "body": "{#if a > 0}n={a}{/if}", "data": {"a": 1}}
    assert _python(flade)["body"] == _ts(flade, tmp_path)["body"] == "n={a}"
