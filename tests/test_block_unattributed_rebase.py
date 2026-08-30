from scripts.block_unattributed_rebase import main


def test_rebase_hook_fails_with_attribution_reason(capsys):
    assert main(["main"]) == 1
    error = capsys.readouterr().err
    assert "rebase is blocked" in error
    assert "stale Actor" in error
