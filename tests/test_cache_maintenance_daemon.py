"""Tests for `core/services/cache_maintenance_daemon.py`.

Dæmonen samler al periodisk oprydning ét sted: web-cache, events-retention,
telemetri-tabeller, state-filer, forældreløse uploads, roterede logfiler,
tool-resultater — og vagten der rapporterer hvad der IKKE har en aftale.

Hele kroppen ligger i ét `try/except Exception`, så et hvilket som helst uheld
inde i den ender som `{"maintained": False, "error": ...}`. Det er en rimelig
konstruktion for en baggrundsdæmon, men det betyder også at en simpel
programmeringsfejl — en nøgle i resultat-ordbogen hvis variabel aldrig blev
tildelt — ville slå HELE vedligeholdelsen ud uden at noget blev rødt.

Det skete 27/9-2026 under tilføjelsen af de to sidste oprydninger. Testene her
er vagten mod netop den slags.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import core.services.cache_maintenance_daemon as cmd


def _tick_funktion() -> ast.FunctionDef:
    kilde = pathlib.Path(inspect.getsourcefile(cmd)).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(kilde)):
        if isinstance(node, ast.FunctionDef) and node.name == "tick_cache_maintenance_daemon":
            return node
    raise AssertionError("fandt ikke tick_cache_maintenance_daemon")


class TestResultatetKanFaktiskBygges:
    def test_hver_noegle_i_resultatet_har_en_tildelt_variabel(self) -> None:
        """En nøgle uden variabel giver NameError, som den ydre except sluger."""
        fn = _tick_funktion()
        tildelt: set[str] = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for m in node.targets:
                    if isinstance(m, ast.Name):
                        tildelt.add(m.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    tildelt.add(node.target.id)

        manglende: list[str] = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.Dict):
                continue
            for n, v in zip(node.keys, node.values):
                if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
                    continue
                if isinstance(v, ast.Name) and v.id not in tildelt:
                    manglende.append("%s -> %s" % (n.value, v.id))
        assert not manglende, (
            "resultat-nøgler peger på variabler der aldrig tildeles: %s" % manglende
        )

    def test_hver_variabel_tildeles_FOER_resultatet_bygges(self) -> None:
        """Tildeling inde i en `try` der kommer EFTER ordbogen tæller ikke."""
        fn = _tick_funktion()
        dicts = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Dict) and any(
                     isinstance(k, ast.Constant) and k.value == "wal_checkpoint"
                     for k in n.keys)]
        assert dicts, "fandt ikke resultat-ordbogen"
        resultat = dicts[0]

        foer: set[str] = set()
        for node in ast.walk(fn):
            if node is resultat or getattr(node, "lineno", 10**9) >= resultat.lineno:
                continue
            if isinstance(node, ast.Assign):
                for m in node.targets:
                    if isinstance(m, ast.Name):
                        foer.add(m.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    foer.add(node.target.id)

        sent = [v.id for k, v in zip(resultat.keys, resultat.values)
                if isinstance(v, ast.Name) and v.id not in foer]
        assert not sent, "tildeles først EFTER resultatet bygges: %s" % sent


class TestOprydningerneErTilsluttet:
    """«Bygget, aldrig tilsluttet» er husets hyppigste fejl.
    `cleanup_old_results(7)` lå i tool_result_store med ét kald — et script
    ingen cron og ingen timer kørte. 18.630 filer, ældste elleve dage.
    """

    @staticmethod
    def _tildelt_fra_kald(funktionsnavn: str) -> list[str]:
        """Variabler der får deres værdi fra et kald til ``funktionsnavn``.

        At lede efter NAVNET i kilden er ikke nok: en import der bliver
        stående mens kaldet erstattes af `= 0` ville stadig bestå. Det er
        tilslutningen der skal pinnes, ikke omtalen.
        """
        fn = _tick_funktion()
        ud: list[str] = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            kaldt = node.value.func
            navn = getattr(kaldt, "id", None) or getattr(kaldt, "attr", None)
            if navn != funktionsnavn:
                continue
            ud += [m.id for m in node.targets if isinstance(m, ast.Name)]
        return ud

    def test_tool_resultater_ryddes_af_daemonen(self) -> None:
        assert self._tildelt_fra_kald("cleanup_old_results") == ["tool_results_pruned"]

    def test_roterede_logfiler_ryddes_af_daemonen(self) -> None:
        assert self._tildelt_fra_kald("prune_rotated_logs") == ["rotated_logs"]

    def test_vagten_koeres_af_daemonen(self) -> None:
        assert self._tildelt_fra_kald("tabeller_uden_politik") == ["uden_politik"]

    def test_de_tre_staar_i_resultatet(self) -> None:
        fn = _tick_funktion()
        noegler = {k.value for n in ast.walk(fn) if isinstance(n, ast.Dict)
                   for k in n.keys
                   if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        for n in ("tool_results_pruned", "rotated_logs", "uden_politik"):
            assert n in noegler, "%s rapporteres ikke i resultatet" % n


class TestKadence:
    def test_daemonen_er_kadence_gated(self) -> None:
        assert cmd._CADENCE_HOURS >= 1
