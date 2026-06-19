import core.services.prompt_contract as pc


def test_device_presence_line_present_when_enabled(monkeypatch):
    monkeypatch.setattr(pc, "_device_awareness_on", lambda: True)
    import core.services.device_presence as dp
    monkeypatch.setattr(dp, "summary", lambda uid: "Bjørn er ved desktop (i fokus).")
    line = pc._device_presence_line("bjorn")
    assert "desktop" in line
    assert line.startswith("[enheds-presence]")


def test_device_presence_line_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(pc, "_device_awareness_on", lambda: False)
    assert pc._device_presence_line("bjorn") == ""
