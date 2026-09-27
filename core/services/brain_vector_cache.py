"""Embedding-matricen for `jarvis_brain`, holdt i hukommelsen mellem søgninger.

## Hvorfor den findes

Målt 27/9-2026 på CT105 med 13.541 aktive poster. `search_brain_scored` tog
170 ms median, og den store post var ikke SQL'en — det var python-løkken der
regnede cosinus én række ad gangen:

    SELECT med blob-kolonnen         40,9 ms
    SELECT uden blob-kolonnen        33,8 ms
    cosinus: per-række python-løkke  56,9 ms
    cosinus: vektoriseret matmul      2,6 ms
    salience-løkke (python)          19,1 ms

To ting følger af det. Løkken skal være ÉN matmul — 54 ms. Og for at kunne
lave den matmul skal vektorerne allerede ligge som en matrix; bygger man den
pr. søgning koster `frombuffer`+`stack` 22-28 ms, altså næsten hele gevinsten.
Derfor cachen.

## Hvorfor den er sikker at cache

En embedding skrives ÉN gang pr. post og ændres aldrig bagefter:

* `write_entry` indsætter altid `embedding = NULL`.
* `embed_pending_entries` er den eneste der sætter en værdi, og den vælger kun
  rækker `WHERE embedding IS NULL` — altså rækker der pr. definition ikke kan
  ligge i cachen, for cachen indeholder kun rækker med en embedding.
* Intet andet sted i repoet skriver til `brain_index.embedding`.

Nøglen er alligevel `(id, indexed_at)` og ikke bare `id`. Skulle en række en
dag blive skrevet forfra (`write_entry`/`rebuild_index_from_files` sætter
`indexed_at = now`), skifter nøglen og vektoren hentes igen. Det gør cachen
korrekt uden at hvile på invarianten ovenfor.

`bump_salience` rører hverken `embedding` eller `indexed_at`, så en genkaldelse
invaliderer ikke noget. Al den metadata der FAKTISK ændrer sig — bumps,
`last_used_at`, `status`, `tags` — læses stadig fra SQL ved hver søgning.
Cachen holder kun det der står stille.
"""

from __future__ import annotations

import logging
import threading
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

#: Nøgle -> række i `_M`. Nøglen er `(id, indexed_at)`; se modulets docstring.
_RAEKKE: dict[tuple[str, str], int] = {}

#: Vektorerne, én pr. række. Erstattes ALTID af en ny matrix når den vokser —
#: aldrig muteret på stedet — så en læser der allerede har taget en reference
#: kan regne videre uden at holde låsen.
_M: np.ndarray | None = None
_NORMER: np.ndarray | None = None

#: Cachen hører til ÉN database. Skifter stien (tests med et midlertidigt
#: JARVIS_HOME, eller en nulstillet fil), smides alt væk. Uden det ville
#: modul-niveau-tilstanden lække mellem tests med genbrugte id'er.
_DB: str | None = None

_LAAS = threading.Lock()

#: Over dette antal rækker bygges cachen forfra i stedet for at vokse videre.
#: 100.000 poster à 768 float32 er ~300 MB. Indekset har 13.541 i dag, så
#: loftet rammes ikke — men cachen lever i en dæmon der kører i ugevis, og en
#: dict uden loft i sådan en er en lækage der venter.
_MAKS_RAEKKER = 100_000

#: Mangler flere end dette, hentes ALT i én forespørgsel. Grænsen findes for at
#: undgå en `IN (...)` med 13.000 pladsholdere ved koldstart — præcis den fælde
#: temporal-boosten sad i (`IN (...)` med 27.068 parametre, 426 ms pr. søgning).
_FULD_HENTNING_GRAENSE = 500


def ryd() -> None:
    """Smid alt væk. Bruges af tests og af en eksplicit genopbygning."""
    global _M, _NORMER, _DB
    with _LAAS:
        _RAEKKE.clear()
        _M = None
        _NORMER = None
        _DB = None


def status() -> dict[str, object]:
    """Hvad ligger der lige nu. Til diagnostik — ikke en del af søgevejen."""
    with _LAAS:
        return {
            "raekker": len(_RAEKKE),
            "dim": int(_M.shape[1]) if _M is not None and _M.size else 0,
            "bytes": int(_M.nbytes) if _M is not None else 0,
            "db": _DB,
        }


def cosinus(
    noegler: Sequence[tuple[str, str]],
    qv: np.ndarray,
) -> np.ndarray:
    """Cosinus mellem `qv` og hver nøgle, i samme rækkefølge som `noegler`.

    `noegler` er `(id, indexed_at)` for de poster kalderen har tilbage efter
    sine billige filtre. Vektorer der ikke allerede er cachet, hentes i ÉN
    forespørgsel.

    En nøgle der ikke kan hentes — rækken blev slettet mellem kalderens SELECT
    og nu — får cosinus 0,0. Det er samme udfald som en tom vektor gav før, og
    det er at foretrække frem for at vælte en søgning på et kapløb.
    """
    n = len(noegler)
    if n == 0:
        return np.zeros(0, dtype=np.float32)

    dim = int(qv.shape[0])
    with _LAAS:
        _nulstil_hvis_anden_db()
        mangler = [nk for nk in noegler if nk not in _RAEKKE]
        if mangler:
            _hent_ind(mangler, dim)
        M, normer = _M, _NORMER
        # -1 markerer "kunne ikke hentes"; se docstring.
        idx = np.fromiter(
            (_RAEKKE.get(nk, -1) for nk in noegler), dtype=np.int64, count=n
        )

    if M is None or M.size == 0:
        return np.zeros(n, dtype=np.float32)

    qn = float(np.linalg.norm(qv)) or 1e-9
    # Regn mod HELE matricen og hent resultatet bagefter. Alternativet — at
    # samle en delmatrix med `M[idx]` først — kopierer 42 MB pr. søgning for at
    # spare en matmul der tager 2,6 ms.
    naevner = normer * qn
    naevner = np.where(naevner == 0.0, 1e-9, naevner)
    alle = (M @ qv) / naevner

    ud = np.where(idx >= 0, alle[np.clip(idx, 0, len(alle) - 1)], 0.0)
    return ud.astype(np.float32, copy=False)


def _nulstil_hvis_anden_db() -> None:
    """Kaldes under `_LAAS`."""
    global _M, _NORMER, _DB
    from core.services.jarvis_brain import index_db_path

    sti = str(index_db_path())
    if _DB is not None and _DB != sti:
        _RAEKKE.clear()
        _M = None
        _NORMER = None
    _DB = sti


def _hent_ind(mangler: list[tuple[str, str]], dim: int) -> None:
    """Hent de manglende vektorer og udvid matricen. Kaldes under `_LAAS`."""
    global _M, _NORMER

    if len(_RAEKKE) + len(mangler) > _MAKS_RAEKKER:
        logger.info(
            "brain_vector_cache: %s + %s rækker over loftet %s — bygger forfra",
            len(_RAEKKE), len(mangler), _MAKS_RAEKKER,
        )
        _RAEKKE.clear()
        _M = None
        _NORMER = None

    from core.services.jarvis_brain import connect_index

    conn = connect_index()
    try:
        if len(mangler) > _FULD_HENTNING_GRAENSE:
            raekker = conn.execute(
                "SELECT id, indexed_at, embedding, embedding_dim FROM brain_index "
                "WHERE embedding IS NOT NULL"
            ).fetchall()
        else:
            ider = sorted({eid for eid, _ in mangler})
            ph = ",".join("?" * len(ider))
            raekker = conn.execute(
                "SELECT id, indexed_at, embedding, embedding_dim FROM brain_index "
                f"WHERE id IN ({ph}) AND embedding IS NOT NULL",
                ider,
            ).fetchall()
    finally:
        conn.close()

    # ALT det der kom med i forespørgslen beholdes — også rækker kalderen ikke
    # spurgte om. Ved en fuld hentning er blob'en allerede læst; at smide den
    # væk ville betyde en ny fuld hentning næste gang nogen søger med et andet
    # `kind`-filter.
    nye_noegler: list[tuple[str, str]] = []
    nye_vektorer: list[np.ndarray] = []
    for eid, indexed_at, blob, emb_dim in raekker:
        nk = (eid, indexed_at)
        if nk in _RAEKKE:
            continue
        if blob is None or emb_dim is None or int(emb_dim) != dim:
            # Afvigende dimension er ikke noget cachen kan regne med i samme
            # matrix. Den udelades, og kalderen får cosinus 0,0 for posten —
            # frem for en ValueError midt i en søgning.
            continue
        nye_noegler.append(nk)
        nye_vektorer.append(
            np.frombuffer(blob, dtype=np.float32).reshape(int(emb_dim))
        )

    if not nye_noegler:
        return

    ny = np.stack(nye_vektorer).astype(np.float32, copy=False)
    ny_normer = np.linalg.norm(ny, axis=1).astype(np.float32, copy=False)
    if _M is None or _M.size == 0:
        _M, _NORMER = ny, ny_normer
        start = 0
    else:
        start = _M.shape[0]
        _M = np.concatenate([_M, ny])
        _NORMER = np.concatenate([_NORMER, ny_normer])
    for i, nk in enumerate(nye_noegler):
        _RAEKKE[nk] = start + i
