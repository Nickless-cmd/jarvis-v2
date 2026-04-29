import pytest

from core.runtime.db import connect, init_db


@pytest.fixture(autouse=True, scope="session")
def _ensure_dispatch_schema():
    init_db()


@pytest.fixture
def tmp_dispatch_db():
    with connect() as conn:
        conn.execute("DELETE FROM claude_dispatch_budget")
        conn.execute("DELETE FROM claude_dispatch_audit")
        conn.commit()
    yield
    with connect() as conn:
        conn.execute("DELETE FROM claude_dispatch_budget")
        conn.execute("DELETE FROM claude_dispatch_audit")
        conn.commit()
