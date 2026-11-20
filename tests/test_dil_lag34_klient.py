"""DIL lag 3 (compile) og lag 4 (fallback/status/settle) — klientens rene logik.

``fladeProgram.ts`` og ``fladeVisning.ts`` er framework-frie, så de køres her direkte i node
(``--experimental-strip-types``); samme tests ligger som vitest/jest i
``apps/*/src/lib/fladeLag34.test.ts``. Desk- og mobil-kopierne SKAL være byte-identiske.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess

import pytest

_ROD = pathlib.Path(__file__).resolve().parent.parent
_DESK = _ROD / "apps/jarvis-desk/src/lib"
_MOBIL = _ROD / "apps/mobile/src/lib"
_FIXT = pathlib.Path(__file__).resolve().parent / "fixtures"
_DELT = ("udtryk.ts", "delvisJson.ts", "fladeProgram.ts", "fladeVisning.ts")


@pytest.mark.parametrize("navn", _DELT)
def test_delte_filer_er_byte_identiske(navn: str) -> None:
    assert (_DESK / navn).read_bytes() == (_MOBIL / navn).read_bytes()


@pytest.mark.skipif(shutil.which("node") is None, reason="node mangler")
def test_fladeLag34_koerer_groent_i_node(tmp_path: pathlib.Path) -> None:
    # Desk-filen har en vitest-import mere end mobil-filen (jest har globaler); resten er ens.
    kilde = (_DESK / "fladeLag34.test.ts").read_text()
    kilde = re.sub(r"^import \{ describe.*\n", "", kilde, flags=re.M)
    assert kilde == (_MOBIL / "fladeLag34.test.ts").read_text()
    # Minimal describe/it/expect over node:assert — vitest er ikke installeret i dette miljø.
    shim = (
        "import assert from 'node:assert/strict'\n"
        "let fejl = 0, antal = 0\n"
        "const describe = (_n: string, f: () => void) => f()\n"
        "const it = (n: string, f: () => void) => { antal++; try { f() } catch (e) { fejl++; console.error('FEJL', n, (e as Error).message) } }\n"
        "const expect = (a: unknown) => ({\n"
        "  toBe: (b: unknown) => assert.strictEqual(a, b),\n"
        "  toEqual: (b: unknown) => assert.deepStrictEqual(a, b),\n"
        "  toBeNull: () => assert.strictEqual(a, null),\n"
        "  toHaveLength: (n: number) => assert.strictEqual((a as unknown[]).length, n),\n"
        "  toContain: (x: unknown) => assert.ok((a as unknown[]).includes(x)),\n"
        "})\n"
    )
    slut = "\nconsole.log(`${antal} tests, ${fejl} fejl`)\nif (fejl) process.exit(1)\n"
    fil = _DESK / "_koer_fladeLag34.tmp.ts"
    try:
        fil.write_text(shim + kilde + slut)
        ud = subprocess.run(
            ["node", "--import", (_FIXT / "ts_register.mjs").as_uri(),
             "--experimental-strip-types", "--no-warnings", str(fil)],
            capture_output=True, text=True, timeout=60,
        )
    finally:
        fil.unlink(missing_ok=True)
    assert ud.returncode == 0, ud.stdout + ud.stderr
    assert " 0 fejl" in ud.stdout
