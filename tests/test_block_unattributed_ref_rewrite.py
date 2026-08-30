from unittest.mock import patch

from scripts.block_unattributed_ref_rewrite import main


ZERO = "0" * 40


def test_reference_transaction_rejects_non_fast_forward(capsys):
    update = "old new refs/heads/main\n"
    with patch(
        "scripts.block_unattributed_ref_rewrite._is_ancestor",
        return_value=False,
    ):
        assert main(["prepared"], input_text=update) == 1

    assert "non-fast-forward branch rewrite" in capsys.readouterr().err


def test_reference_transaction_allows_fast_forward():
    update = "old new refs/heads/main\n"
    with patch(
        "scripts.block_unattributed_ref_rewrite._is_ancestor",
        return_value=True,
    ):
        assert main(["prepared"], input_text=update) == 0


def test_reference_transaction_allows_create_delete_and_non_branch_refs():
    updates = (
        f"{ZERO} new refs/heads/new\n"
        f"old {ZERO} refs/heads/old\n"
        "old new refs/remotes/origin/main\n"
    )
    with patch(
        "scripts.block_unattributed_ref_rewrite._is_ancestor"
    ) as ancestor:
        assert main(["prepared"], input_text=updates) == 0
    ancestor.assert_not_called()


def test_attributed_amend_escape_is_explicit(monkeypatch):
    monkeypatch.setenv("JARVIS_ATTRIBUTED_REWRITE", "1")
    with patch(
        "scripts.block_unattributed_ref_rewrite._is_ancestor"
    ) as ancestor:
        assert main(
            ["prepared"], input_text="old new refs/heads/main\n"
        ) == 0
    ancestor.assert_not_called()
