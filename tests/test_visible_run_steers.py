from core.services.run_trailing import RundeHale
from core.services.visible_run_steers import append_real_user_steers


def test_real_steer_keeps_user_role_while_runtime_notice_is_system():
    tail = RundeHale()
    tail.tilfoej_runde("Skriv nu dit endelige svar")
    accepted, stopped = append_real_user_steers(
        tail, [{"content": "  tjek filen  ", "at": "nu"}]
    )
    assert accepted == [{"content": "tjek filen", "at": "nu"}]
    assert not stopped
    assert [m["role"] for m in tail.som_liste()] == ["user", "system"]


def test_stop_steer_stops_following_messages():
    tail = RundeHale()
    accepted, stopped = append_real_user_steers(
        tail, [{"content": "stop nu"}, {"content": "skal ikke nås"}]
    )
    assert stopped
    assert [m["content"] for m in accepted] == ["stop nu"]
    assert [m["content"] for m in tail.som_liste()] == ["stop nu"]
