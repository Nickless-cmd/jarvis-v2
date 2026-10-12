import pytest


def test_empty_routine_identity_fails_closed(isolated_runtime):
    from core.services.routine_identity import UnresolvedRoutinePrincipal, resolve_principal

    with pytest.raises(UnresolvedRoutinePrincipal):
        resolve_principal("")
