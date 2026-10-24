"""Separat søgeindeks over repoets DOKUMENTATION — ikke kildekoden.

## Hvorfor et SEPARAT indeks (målt og besluttet 23/10-2026)

`memory_search` indekserer Jarvis' egen hukommelse (MEMORY/USER/SOUL/
PLAYBOOKS + kuraterede noter). Det her er en anden slags stof: repoets
dokumentation — arkitektur, specs, runbooks, audits.

De to må ikke ligge i samme pulje. `recall._source_workspace` kalder
`search_memory` UDEN `sources`-filter, så alt i memory-indekset konkurrerer
om de samme kandidatpladser. Lagde jeg ~13.000 doc-chunks derind, ville de
fortrænge Jarvis' egne noter i de 3-5 linjer auto-recall injicerer per tur.

Bjørns arkitektur (23/10-2026): *«det var derfor jeg ville repo_recall og
auto_repo_recall, dvs. auto vil lige som nu dukke op i prompten og repo
recall er et manuelt tool.»* To spor, hver sin pulje, ingen konkurrence.

Dette modul er det ene spor: **`repo_recall`, det manuelle værktøj.**
Auto-sporet (`auto_repo_recall`) injicerer i prompten med sit EGET budget
og læser samme indeks — men det er en anden flade og bygges separat.

## Hvad der er med, og hvad der ikke er

Repos rod-Markdown + alt under `docs/`, med to bevidste undtagelser:

* ``docs/_archive/`` — per definition forældet (142 filer, målt 23/10-2026).
  DOCS_MANIFEST dokumenterer endda hvorfor hver enkelt er droppet.
* ``docs/reference/api/`` — GENERERET fra kilden (80 filer). Det beskriver
  kode, og Bjørn sagde udtrykkeligt: ikke koden. Den kan genskabes på
  sekunder med ``scripts/api_docs_gen.py``.

``docs/superpowers/plans`` er med. De beskriver arbejde der ER udført, men
netop derfor kan de svare på «hvordan blev X bygget» — det er en anden type
svar end en spec, ikke støj. (Målt: 146 filer, ~6.200 chunks.)

Identitetsfilerne på repo-roden (``USER.md``, ``STANDING_ORDERS.md``,
``MEMORY.md``) er KOPIER der ikke læses af runtimen — QUICK_FACTS er
eksplicit om at sandheden bor i workspacet. De udelades, ellers kunne
`repo_recall` returnere en forældet identitet som om den var gældende.

## Byggetiden

Målt 23/10-2026: ~130 ms pr. chunk på GTX 1070. En fuld førstegangsbygning
er derfor 20-30 minutter for hele korpuset. Derfor samme mønster som
`memory_search`: chunk straks (få sekunder, ingen embedding), svar med
TF-IDF imens, og embed i en baggrundstråd. Indekset bliver bedre af sig
selv uden at nogen tur hænger.
"""
from __future__ import annotations

import logging
import os
import pickle
import re
import threading
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from core.runtime.workspace_paths import _jarvis_home
from core.services.memory_search import (
    Chunk,
    _chunk_markdown,
    _cosine_sim,
    _embed_ollama,
    _embed_single,
    _tfidf_search,
)

logger = logging.getLogger(__name__)

_INDEX_FILENAME = "repo_index.pkl"
_EMBED_MODEL = "nomic-embed-text"

_INDEX_LOCK = threading.Lock()
_REBUILD_LOCK = threading.Lock()
_REBUILD_ACTIVE = False
_MEM_INDEX: dict[str, dict] = {}

#: Filnavne på repo-roden der er KOPIER af identitetsfiler, ikke kilden.
#: Sandheden bor i workspaces/<bruger>/ og indekseres af memory_search.
_ROOT_EXCLUDED_NAMES = frozenset({
    "USER.md",
    "STANDING_ORDERS.md",
    "STANDING_ORDERS.en.md",
    "MEMORY.md",
})

#: Kataloger under docs/ der bevidst ikke indekseres (se modul-docstring).
_EXCLUDED_PREFIXES = (
    "docs/_archive/",
    "docs/reference/api/",
)


def _repo_root() -> Path:
    """Repoets rod. Kan overstyres med JARVIS_REPO_ROOT (tests, worktrees)."""
    override = os.environ.get("JARVIS_REPO_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2]


def _index_path() -> Path:
    """Global sti — dokumentationen er den samme for alle brugere."""
    return _jarvis_home() / "state" / _INDEX_FILENAME


def _is_excluded(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    if rel in _ROOT_EXCLUDED_NAMES:
        return True
    return any(rel.startswith(p) for p in _EXCLUDED_PREFIXES)


def repo_files(root: Path | None = None) -> list[Path]:
    """Alle dokumentationsfiler der skal indekseres, sorteret.

    Glob-baseret med vilje: en hårdkodet filliste rådner tavst. Det var
    præcis fejlen med PLAYBOOKS.md (målt 23/10-2026) — filen fandtes på
    disken, men stod ikke på listen, så `recall` kunne ikke finde den.
    """
    root = root or _repo_root()
    files: list[Path] = []
    docs = root / "docs"
    if docs.is_dir():
        for f in docs.rglob("*.md"):
            if not f.is_file():
                continue
            try:
                rel = f.relative_to(root).as_posix()
            except ValueError:  # fil uden for docs-roden — spring den over, ikke hele indekset
                continue
            if not _is_excluded(rel):
                files.append(f)
    for f in sorted(root.glob("*.md")):
        if f.is_file() and not _is_excluded(f.name):
            files.append(f)
    return sorted(set(files))


def _file_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:  # filen forsvandt mellem glob og stat — behandl som uændret
        return 0.0


def _chunk_files(files: list[Path], root: Path) -> list[Chunk]:
    """Læs + chunk. Kun fil-I/O — ingen embedding."""
    all_chunks: list[Chunk] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("repo_index: kunne ikke læse %s: %s", f, exc)
            continue
        try:
            rel = f.relative_to(root).as_posix()
        except ValueError:  # fil uden for roden (fx symlink) — filnavnet er nok
            rel = f.name
        all_chunks.extend(_chunk_markdown(text, rel))
    return all_chunks


def _load_cached_vectors(path: Path) -> dict[str, np.ndarray]:
    """chunk-tekst → vektor fra eksisterende cache, til inkrementel reindeksering."""
    try:
        if not path.exists():
            return {}
        with open(path, "rb") as fh:
            data = pickle.load(fh)
        if data.get("model") != _EMBED_MODEL:
            return {}
        chunks = data.get("chunks") or []
        embs = data.get("embeddings")
        if embs is None or len(chunks) != len(embs):
            return {}
        return {c.text: embs[i] for i, c in enumerate(chunks)}
    except Exception:  # brudt eller fremmed cache → fuld re-embed, aldrig en kastet fejl
        return {}


def build_index(*, root: Path | None = None, force: bool = False) -> dict:
    """Byg indekset og skriv cachen. Blokerer indtil embeddings er færdige.

    Kaldes fra CLI'en og fra baggrundstråden — ALDRIG fra en bruger-tur.
    """
    root = root or _repo_root()
    files = repo_files(root)
    mtimes = {str(f): _file_mtime(f) for f in files}
    path = _index_path()

    if not force and path.exists():
        try:
            with open(path, "rb") as fh:
                cached = pickle.load(fh)
            if cached.get("mtimes") == mtimes and cached.get("model") == _EMBED_MODEL:
                return {
                    "status": "unchanged",
                    "chunks": len(cached.get("chunks") or []),
                    "files": len(files),
                }
        except Exception:  # korrupt pkl → byg forfra nedenfor i stedet for at kaste
            pass

    all_chunks = _chunk_files(files, root)
    if not all_chunks:
        return {"status": "empty", "chunks": 0, "files": len(files)}

    reuse = {} if force else _load_cached_vectors(path)
    todo = [i for i, c in enumerate(all_chunks) if c.text not in reuse]
    embeddings: np.ndarray | None
    if not reuse:
        embeddings = _embed_ollama([c.text for c in all_chunks])
    elif todo:
        new_vecs = _embed_ollama([all_chunks[i].text for i in todo])
        if new_vecs is None:
            embeddings = _embed_ollama([c.text for c in all_chunks])
        else:
            dim = len(next(iter(reuse.values())))
            embeddings = np.zeros((len(all_chunks), dim), dtype=np.float32)
            k = 0
            for i, c in enumerate(all_chunks):
                if c.text in reuse:
                    embeddings[i] = reuse[c.text]
                else:
                    embeddings[i] = new_vecs[k]
                    k += 1
            logger.info(
                "repo_index: inkrementel — %d genbrugt, %d embeddet",
                len(all_chunks) - len(todo), len(todo),
            )
    else:
        embeddings = _embed_ollama([c.text for c in all_chunks])

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump({
            "chunks": all_chunks,
            "embeddings": embeddings,
            "mtimes": mtimes,
            "model": _EMBED_MODEL,
            "root": str(root),
            "built_at": datetime.now(UTC).isoformat(),
        }, fh)
    tmp.replace(path)  # atomisk: en halvskrevet pkl må aldrig kunne læses
    logger.info("repo_index: bygget — %d chunks, embeddings=%s",
                len(all_chunks), embeddings is not None)
    return {
        "status": "built",
        "chunks": len(all_chunks),
        "files": len(files),
        "has_embeddings": embeddings is not None,
        "embedded": len(todo) if reuse else len(all_chunks),
    }


def _schedule_background_build() -> None:
    """Byg i baggrunden (fire-and-forget, kun én ad gangen)."""
    global _REBUILD_ACTIVE
    with _REBUILD_LOCK:
        if _REBUILD_ACTIVE:
            return
        _REBUILD_ACTIVE = True

    def _run() -> None:
        global _REBUILD_ACTIVE
        try:
            build_index()
        except Exception as exc:
            logger.warning("repo_index: baggrundsbygning fejlede: %s", exc)
        finally:
            with _REBUILD_LOCK:
                _REBUILD_ACTIVE = False

    threading.Thread(target=_run, name="repo-index-build", daemon=True).start()


def _load_or_build() -> tuple[list[Chunk], np.ndarray | None, dict[str, float]]:
    """(chunks, embeddings, mtimes). Blokerer aldrig på en fuld embedding."""
    path = _index_path()
    files = repo_files()
    mtimes = {str(f): _file_mtime(f) for f in files}

    if path.exists():
        try:
            key = str(path)
            pkl_mtime = _file_mtime(path)
            mem = _MEM_INDEX.get(key)
            if mem is not None and mem.get("pkl_mtime") == pkl_mtime:
                cached = mem["data"]
            else:
                with open(path, "rb") as fh:
                    cached = pickle.load(fh)
                _MEM_INDEX[key] = {"pkl_mtime": pkl_mtime, "data": cached}
            if cached.get("mtimes") == mtimes and cached.get("model") == _EMBED_MODEL:
                return cached["chunks"], cached.get("embeddings"), mtimes
            # Forældet → svar straks med det gamle, byg nyt i baggrunden.
            _schedule_background_build()
            return cached.get("chunks", []), cached.get("embeddings"), cached.get("mtimes", mtimes)
        except Exception as exc:
            logger.warning("repo_index: cache-indlæsning fejlede: %s", exc)

    # Ingen cache: chunk hurtigt (sekunder), svar med TF-IDF, embed i baggrunden.
    all_chunks = _chunk_files(files, _repo_root())
    _schedule_background_build()
    return all_chunks, None, mtimes


def _path_matches(source: str, path_prefix: str | None) -> bool:
    if not path_prefix:
        return True
    return source.replace("\\", "/").startswith(path_prefix.strip("/"))


#: Område-vægte — ganget på cosinus-scoren, ikke et filter.
#:
#: HVORFOR (målt 24/10-2026): indekset havde 18.204 chunks, hvoraf
#: `docs/superpowers` var 13.415 = 73,7 %, mens `docs/notes` var 1,6 %.
#: Cosine er upartisk, så mængde vandt over relevans: på «desk release CI
#: tag» kom `docs/mobile/signering.md` og en marketplace-plan øverst, mens
#: `docs/notes/2026-10-04-desk-udgivelser.md` — det rigtige svar, som ER i
#: indekset — slet ikke blev ramt. Fire af seks kontrolspørgsmål ramte
#: forkert. Det er samme fejlklasse som QUICK_FACTS-loftet: indholdet var
#: der, balancen var forkert.
#:
#: Vægten er en MENING om hvad et svar er værd, ikke en måling — derfor
#: står tallene her og ikke spredt i koden, så de kan diskuteres og ændres.
#: `docs/superpowers/specs` er urørt (1,0): specs beskriver hvordan tingene
#: ER, og de var allerede de bedste svar på «recall arkitektur».
_AREA_WEIGHTS: tuple[tuple[str, float], ...] = (
    # Udførte planer: mest historik, mindst svar. Stadig søgbare — de kan
    # svare på «hvordan blev X bygget» — men de skal ikke vinde i kraft af
    # at være 146 filer.
    ("docs/superpowers/plans/", 0.72),
    # Levende specs: urørt. Det er den bedste kilde til «hvordan hænger det sammen».
    ("docs/superpowers/specs/", 1.0),
    # Håndskrevet reference og driftsdokumentation: høj værdi, lav mængde.
    ("docs/reference/", 1.12),
    ("docs/runbooks/", 1.12),
    ("docs/notes/", 1.10),
    ("docs/specs/", 1.08),
    ("docs/", 1.05),
    # Rod-Markdown (AGENTS.md, CONTRIBUTING.md …): gældende regler.
    ("", 1.10),
)


def _area_weight(source: str) -> float:
    """Vægt for en chunk-kilde. Første match vinder, mest specifikke først."""
    src = source.replace("\\", "/")
    for prefix, weight in _AREA_WEIGHTS:
        if prefix and src.startswith(prefix):
            return weight
    return 1.0


#: Vægt mellem semantik og leksik i hybrids-scoren.
#:
#: HVORFOR (målt 24/10-2026): område-vægten alene flyttede rangeringen, men
#: kunne ikke redde «desk release CI tag». Det rigtige hit —
#: `docs/notes/2026-10-04-desk-udgivelser.md` — lå på **rank 224** med rå
#: cosine 0,548, mens det forkerte topsvar lå på 0,620. Embeddingen kunne
#: ikke skelne dem; nomic giver flade cosinus på dansk. Vægtning kan ikke
#: løfte et hit der ligger 224 pladser nede.
#:
#: Målt over otte kontrolspørgsmål: 0,25 leksik flyttede det rigtige hit til
#: top-1 på «desk release» (0,715) og forbedrede eller bevarede de øvrige.
#: 0,35 gav marginalt højere score på det rigtige hit, men begyndte at
#: rangere på ord-overlap alene. 0,25 er valgt som den mindste vægt der
#: løser problemet.
_LEXICAL_WEIGHT = 0.25


def _lexical_score(query_terms: list[str], chunk: "Chunk") -> float:
    """Andel af query-termer der optræder i chunk, sektion eller sti."""
    if not query_terms:
        return 0.0
    hay = f"{chunk.text} {chunk.source} {chunk.section or ''}".lower()
    return sum(1 for t in query_terms if t in hay) / len(query_terms)


def search_repo(
    query: str,
    *,
    limit: int = 8,
    path_prefix: str | None = None,
) -> list[dict]:
    """Semantisk søgning i repoets dokumentation.

    ``path_prefix`` afgrænser til fx ``docs/superpowers/specs``. Det er et
    billigt filter oven på resultatet — indekset er ét korpus, ikke syv.
    """
    query = (query or "").strip()
    if not query:
        return []

    with _INDEX_LOCK:
        chunks, embeddings, _ = _load_or_build()

    if not chunks:
        return []

    if path_prefix:
        keep = [i for i, c in enumerate(chunks) if _path_matches(c.source, path_prefix)]
        if not keep:
            return []
        chunks = [chunks[i] for i in keep]
        if embeddings is not None:
            embeddings = embeddings[keep]

    if embeddings is not None:
        q_emb = _embed_single(query)
        if q_emb is not None:
            scores = _cosine_sim(q_emb, embeddings)
            # Hybrid: semantik + leksik, derefter område-vægt. Rækkefølgen er
            # ikke ligegyldig — vægten ganges på FØR udvælgelsen, ellers ville
            # top-N være valgt på den rå cosine og kun blive omrokeret bagefter.
            # Målt 24/10-2026: det rigtige hit lå på rank 224 og kom derfor
            # aldrig i betragtning uanset hvordan man vejede de øverste.
            terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
            lexical = np.array([_lexical_score(terms, c) for c in chunks], dtype=np.float32)
            combined = scores * (1.0 - _LEXICAL_WEIGHT) + lexical * _LEXICAL_WEIGHT
            weights = np.array([_area_weight(c.source) for c in chunks], dtype=np.float32)
            weighted = combined * weights
            top_idx = np.argsort(weighted)[::-1][: limit * 3]
            results = []
            for i in top_idx:
                # Gulvet maaler den SAMLEDE relevans, ikke raa cosine.
                # Foer (maalt 24/10-2026) stod der `scores[i] <= 0.1`, og det
                # kasserede praecis de hits hybrid-scoren findes for: en chunk
                # der deler alle query-ord men ligger semantisk fjernt (dansk
                # tekst giver flad cosine) blev filtreret vaek FOER den blev
                # bedoemt. Testen `test_hybrid_loefter_leksikalsk_hit_som_
                # embedding_missede` fangede det.
                if combined[i] <= 0.1:
                    continue
                results.append({
                    "text": chunks[i].text,
                    "source": chunks[i].source,
                    "section": chunks[i].section,
                    "score": float(weighted[i]),
                    "raw_score": float(scores[i]),
                    "method": "embedding",
                })
                if len(results) >= limit:
                    break
            return results

    return _tfidf_search(query, chunks, limit)


def get_stats() -> dict:
    """Indeksets tilstand uden at bygge noget."""
    path = _index_path()
    files = repo_files()
    if not path.exists():
        return {
            "status": "not_built",
            "chunk_count": 0,
            "file_count": len(files),
            "path": str(path),
        }
    try:
        with open(path, "rb") as fh:
            cached = pickle.load(fh)
        chunks = cached.get("chunks") or []
        by_area: dict[str, int] = {}
        for c in chunks:
            area = c.source.split("/")[0] if "/" in c.source else "(rod)"
            if c.source.startswith("docs/"):
                parts = c.source.split("/")
                area = "/".join(parts[:2]) if len(parts) > 2 else "docs"
            by_area[area] = by_area.get(area, 0) + 1
        return {
            "status": "ready",
            "chunk_count": len(chunks),
            "file_count": len(cached.get("mtimes") or {}),
            "current_file_count": len(files),
            "has_embeddings": cached.get("embeddings") is not None,
            "model": cached.get("model", ""),
            "built_at": cached.get("built_at", ""),
            "root": cached.get("root", ""),
            "path": str(path),
            "by_area": dict(sorted(by_area.items(), key=lambda kv: -kv[1])),
        }
    except Exception:  # ulæselig pkl → rapportér "corrupt" frem for at kaste i en status-visning
        return {"status": "corrupt", "chunk_count": 0, "path": str(path)}


def invalidate() -> None:
    """Slet cachen, så næste søgning genopbygger."""
    try:
        _index_path().unlink(missing_ok=True)
        _MEM_INDEX.clear()
        logger.info("repo_index: cache invalideret")
    except Exception as exc:
        logger.warning("repo_index: invalidering fejlede: %s", exc)


def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Repo-dokumentationsindeks")
    parser.add_argument("--build", action="store_true", help="byg indekset")
    parser.add_argument("--force", action="store_true", help="ignorér cachen")
    parser.add_argument("--stats", action="store_true", help="vis tilstand")
    parser.add_argument("--search", default="", help="søg og vis hits")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args(argv)

    if args.build:
        print(json.dumps(build_index(force=args.force), ensure_ascii=False, indent=2))
    if args.search:
        print(json.dumps(search_repo(args.search, limit=args.limit),
                         ensure_ascii=False, indent=2))
    if args.stats or not (args.build or args.search):
        print(json.dumps(get_stats(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
