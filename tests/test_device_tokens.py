import core.services.device_tokens as dt


def _clear():
    dt._ensure_table()
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM device_tokens")


def test_register_and_list():
    _clear()
    dt.register("bjorn", "tok-A", "android")
    dt.register("bjorn", "tok-B", "android")
    dt.register("mikkel", "tok-C", "android")
    assert set(dt.list_for_user("bjorn")) == {"tok-A", "tok-B"}
    assert dt.list_for_user("mikkel") == ["tok-C"]


def test_register_is_upsert():
    _clear()
    dt.register("bjorn", "tok-A", "android")
    dt.register("mikkel", "tok-A", "android")  # samme token, ny ejer (telefon-skift)
    assert dt.list_for_user("bjorn") == []
    assert dt.list_for_user("mikkel") == ["tok-A"]


def test_delete():
    _clear()
    dt.register("bjorn", "tok-A", "android")
    dt.delete("tok-A")
    assert dt.list_for_user("bjorn") == []
    dt.delete("tok-A")  # idempotent — må ikke fejle
