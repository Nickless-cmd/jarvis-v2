from pathlib import Path


def test_ci_validates_commit_attribution_for_push_and_pull_request():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    assert "commit-attribution:" in workflow
    assert "fetch-depth: 0" in workflow
    assert "github.event.pull_request.base.sha" in workflow
    assert "github.event.before" in workflow
    assert "PRE_COMMIT_REF_TYPE: ${{ github.ref_type }}" in workflow
    assert 'PRE_COMMIT_FROM_REF="${PRE_COMMIT_TO_REF}^"' in workflow
    assert "scripts/validate_commit_attribution.py --pre-push" in workflow
