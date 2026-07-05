"""Tests for de 5 resterende datasource-fetchers (path + shape + self-safe):
attention / skills / integrity / experiments / execution.
"""


class _FC:
    def __init__(self, payload=None, raise_=False):
        self._payload = payload
        self._raise = raise_
        self.path = None

    def get_json(self, p, params=None):
        self.path = p
        if self._raise:
            raise RuntimeError("nej")
        return self._payload


# ── attention ────────────────────────────────────────────────────────────────
def test_attention_path_and_shape():
    from central_cli import datasource
    fc = _FC({"attention": {"budget": 7}})
    out = datasource.attention(fc)
    assert fc.path == "/central/attention"
    assert out == {"budget": 7}


def test_attention_self_safe():
    from central_cli import datasource
    assert datasource.attention(_FC(raise_=True)) == {}
    assert datasource.attention(_FC(payload="not-a-dict")) == {}


# ── skills ───────────────────────────────────────────────────────────────────
def test_skills_path_and_shape():
    from central_cli import datasource
    fc = _FC({"engine": {"skills": ["a"]}, "contracts": {"c": 1}})
    out = datasource.skills(fc)
    assert fc.path == "/central/skills"
    assert out == {"engine": {"skills": ["a"]}, "contracts": {"c": 1}}


def test_skills_self_safe():
    from central_cli import datasource
    assert datasource.skills(_FC(raise_=True)) == {"engine": {}, "contracts": {}}
    assert datasource.skills(_FC(payload=None)) == {"engine": {}, "contracts": {}}


# ── integrity ────────────────────────────────────────────────────────────────
def test_integrity_path_and_shape():
    from central_cli import datasource
    fc = _FC({"integrity": {"guard": True}})
    out = datasource.integrity(fc)
    assert fc.path == "/central/integrity"
    assert out == {"guard": True}


def test_integrity_self_safe():
    from central_cli import datasource
    assert datasource.integrity(_FC(raise_=True)) == {}
    assert datasource.integrity(_FC(payload=[])) == {}


# ── experiments ──────────────────────────────────────────────────────────────
def test_experiments_path_and_shape():
    from central_cli import datasource
    fc = _FC({"experiments": {"n": 3}})
    out = datasource.experiments(fc)
    assert fc.path == "/central/experiments"
    assert out == {"n": 3}


def test_experiments_self_safe():
    from central_cli import datasource
    assert datasource.experiments(_FC(raise_=True)) == {}
    assert datasource.experiments(_FC(payload="x")) == {}


# ── execution ────────────────────────────────────────────────────────────────
def test_execution_path_and_shape():
    from central_cli import datasource
    fc = _FC({"execution": {"visible_model_provider": "github-copilot"}})
    out = datasource.execution(fc)
    assert fc.path == "/central/execution"
    assert out == {"visible_model_provider": "github-copilot"}


def test_execution_self_safe():
    from central_cli import datasource
    assert datasource.execution(_FC(raise_=True)) == {}
    assert datasource.execution(_FC(payload=None)) == {}
