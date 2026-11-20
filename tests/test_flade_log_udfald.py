"""flade_log skal acceptere de udfald klienten faktisk sender (DIL lag 4)."""
import pytest
from pydantic import ValidationError

from apps.api.jarvis_api.routes.flade_log import FladeSnapshot


@pytest.mark.parametrize("udfald", ["native", "native-delvis", "settle-afvigelse", "parse-null"])
def test_kendte_udfald_accepteres(udfald: str) -> None:
    assert FladeSnapshot(udfald=udfald).udfald == udfald


def test_ukendt_udfald_afvises() -> None:
    with pytest.raises(ValidationError):
        FladeSnapshot(udfald="noget-andet")
