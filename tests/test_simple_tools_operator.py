"""Operator-eksekveringerne — argument-validering og læs-før-skriv-værnet.

`operator_multi_edit` er ny (5/9-2026) og lukker ét af fire huller i «det samme
på min maskine». Den deler værn med `operator_edit_file`: redigerer man en fil,
skal man have læst den i denne session.
"""
from __future__ import annotations

from core.tools.simple_tools_operator import _exec_operator_multi_edit


class TestMultiEditValidering:
    def test_path_kraeves(self):
        r = _exec_operator_multi_edit({"edits": [{"old_string": "a", "new_string": "b"}]})
        assert r["status"] == "error" and "path" in r["error"]

    def test_edits_kraeves(self):
        r = _exec_operator_multi_edit({"path": "/x.py"})
        assert r["status"] == "error" and "edits" in r["error"]

    def test_tom_edits_liste_afvises(self):
        """En tom liste ville ellers skrive filen uændret tilbage — en
        rundtur over broen der ikke gør noget."""
        r = _exec_operator_multi_edit({"path": "/x.py", "edits": []})
        assert r["status"] == "error"

    def test_edits_skal_vaere_en_liste(self):
        r = _exec_operator_multi_edit({"path": "/x.py", "edits": "a=1"})
        assert r["status"] == "error"


class TestLaesFoerSkrivVaernet:
    def test_blokerer_naar_filen_ikke_er_laest(self, monkeypatch):
        """Samme værn som edit_file: man må ikke redigere i blinde."""
        class _Ec:
            classification = "guard_blocked"
            reason = "ikke læst i denne session"

        import core.services.gate_execution as ge
        monkeypatch.setattr(ge, "check_operator",
                            lambda *a, **k: _Ec(), raising=False)
        r = _exec_operator_multi_edit({
            "path": "/x.py", "_session_id": "s1",
            "edits": [{"old_string": "a", "new_string": "b"}]})
        assert r["blocked_by"] == "read_before_write_guard"
        assert "operator_read_file" in r["hint"]

    def test_et_daarligt_vaern_stopper_ikke_kaldet(self, monkeypatch):
        """Værnet er self-safe: kaster det, skal redigeringen stadig kunne ske."""
        import core.services.gate_execution as ge
        monkeypatch.setattr(
            ge, "check_operator",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")),
            raising=False)
        kaldt = {}
        import core.tools.simple_tools_operator as sto

        def _fake(fn, tool_name=""):
            kaldt["tool"] = tool_name
            return {"status": "ok"}

        monkeypatch.setattr(sto, "_run_operator_async", _fake)
        r = _exec_operator_multi_edit({
            "path": "/x.py", "edits": [{"old_string": "a", "new_string": "b"}]})
        assert kaldt["tool"] == "operator_multi_edit"
        assert r["status"] == "ok"
