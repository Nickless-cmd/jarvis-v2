"""Tests for degenerations-guarden (model-repetitions-løkke-detektor)."""
from core.services.stream_degeneration import check_degeneration


def test_runaway_incrementing_filenames_flagged():
    # Den ægte 147KB-sag: probe_ollama864.py ... probe_ollama991.py ×mange.
    text = " ".join(f"probe_ollama{i}.py" for i in range(864, 864 + 2000))
    deg, why = check_degeneration(text)
    assert deg is True
    assert "repetition" in why


def test_repeated_token_flagged():
    text = ("FEJL " * 500)
    deg, _ = check_degeneration(text)
    assert deg is True


def test_real_varied_listing_not_flagged():
    # Ægte directory-listing med varierede navne → høj diversitet → IKKE flagget.
    names = ["1635980525.bin", "multi-user.md", "JarvisX.zip", "QUICK_FACTS.md",
             "bridge.js", "app.asar", "atomic_claim.py", "benchmark.txt",
             "add_gpt55.py", "auth_e2e.py", "c3_verify.py", "advokat.html"]
    text = " ".join(names * 40)
    deg, _ = check_degeneration(text)
    assert deg is False


def test_real_prose_not_flagged():
    text = ("Containeren har kørt 28 dage uden genstart og load average er lavt nok. ") * 30
    deg, _ = check_degeneration(text)
    assert deg is False


def test_short_text_not_flagged():
    assert check_degeneration("bs")[0] is False
    assert check_degeneration("")[0] is False


def test_self_safe_on_bad_input():
    assert check_degeneration(None)[0] is False  # type: ignore[arg-type]
