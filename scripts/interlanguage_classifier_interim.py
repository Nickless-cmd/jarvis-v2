#!/usr/bin/env python
"""Interim Phase 3 classifier — pre-registered method, partial data.

Følger spec'en docs/superpowers/specs/2026-05-16-interlanguage-validation-phase3-4-design.md
ord-for-ord på §1 (cleanup) og §2 (statistical classifier), men kører på det
data der eksisterer NU (interim sample) i stedet for at vente til 28/5.

Resultater er IKKE pre-registreret final analyse — de er en preview.
Den endelige kørsel sker 28/5 efter 7 fulde dage post-restart.

Usage:
  /opt/conda/envs/ai/bin/python scripts/interlanguage_classifier_interim.py
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

DB = os.path.expanduser("~/.jarvis-v2/state/jarvis.db")
PRIMITIVES = ["→", "↔", "⊂", "≈", "!"]
# 2026-05-22 (Claude, after Codex audit): import CORE_TERMS from the
# engine instead of a hand-typed list. The previous hand-typed list
# only overlapped 5/14 terms with engine.CORE_VOCABULARY (drøm, signal,
# agens, rytme, vægt) — the other 9 entries (veto, tærskel, loop,
# stilhed, spor, skygge, kerne, puls, horisont) were not part of the
# practiced vocabulary and biased the term-frequency feature dimensions.
# Spec §1 says "14 core vocabulary terms" — engine is the source of truth.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.services.interlanguage_practice import CORE_TERMS as _ENGINE_CORE_TERMS
CORE_VOCAB = list(_ENGINE_CORE_TERMS)
assert len(CORE_VOCAB) == 14, f"expected 14 core terms, got {len(CORE_VOCAB)}"
SEED = 42
PEERS = ["jarvis", "claude", "claude_jp", "glm", "glm_jp", "ollama_local", "random"]


# ---------- §1 Dataudtræk + cleanup ----------

def load_raw() -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT expression_id, expression_text, peer_id, created_at "
        "FROM interlanguage_practice "
        "WHERE expression_text != '' AND length(expression_text) >= 3 "
        "ORDER BY peer_id, created_at ASC"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def cleanup(rows: list[dict]) -> tuple[list[dict], dict]:
    """Pre-registreret cleanup (§1):
    1. drop text-længde < 3 (allerede gjort i SQL)
    2. drop uden primitiv-symbol
    3. drop >200 tegn
    4. de-dup per peer inden for 1 time (samme text)
    """
    raw_per_peer: Counter = Counter(r["peer_id"] for r in rows)
    stats_out: dict = {"raw_per_peer": dict(raw_per_peer), "dropped": defaultdict(Counter)}

    out: list[dict] = []
    seen_recent: dict[tuple[str, str], datetime] = {}
    for r in rows:
        text = r["expression_text"]
        peer = r["peer_id"]
        # 2. Skal indeholde mindst ét primitiv
        if not any(p in text for p in PRIMITIVES):
            stats_out["dropped"][peer]["no_primitive"] += 1
            continue
        # 3. Max 200 tegn
        if len(text) > 200:
            stats_out["dropped"][peer]["too_long"] += 1
            continue
        # 4. De-dup inden for 1 time
        ts = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        key = (peer, text)
        prev = seen_recent.get(key)
        if prev is not None and (ts - prev).total_seconds() < 3600:
            stats_out["dropped"][peer]["dup_within_1h"] += 1
            continue
        seen_recent[key] = ts
        out.append(r)

    stats_out["kept_per_peer"] = Counter(r["peer_id"] for r in out)
    return out, stats_out


# ---------- §2 Feature extraction ----------

def featurize(rows: list[dict], embedder: SentenceTransformer) -> np.ndarray:
    texts = [r["expression_text"] for r in rows]
    emb = embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    prim = np.zeros((len(rows), len(PRIMITIVES)), dtype=np.float32)
    vocab = np.zeros((len(rows), len(CORE_VOCAB)), dtype=np.float32)
    for i, text in enumerate(texts):
        n_tok = max(len(text.split()), 1)
        for j, p in enumerate(PRIMITIVES):
            prim[i, j] = text.count(p) / n_tok
        low = text.lower()
        for j, w in enumerate(CORE_VOCAB):
            vocab[i, j] = low.count(w) / n_tok
    return np.hstack([emb, prim, vocab])


# ---------- §2 Permutation test ----------

def permutation_p(clf_template, X_train, y_train, X_test, y_test, observed_acc, n=1000):
    rng = np.random.default_rng(SEED)
    shuffled_accs = []
    for i in range(n):
        y_perm = y_train.copy()
        rng.shuffle(y_perm)
        clf = LogisticRegression(
            max_iter=2000, random_state=SEED, n_jobs=1
        )
        clf.fit(X_train, y_perm)
        shuffled_accs.append(accuracy_score(y_test, clf.predict(X_test)))
    shuffled_accs = np.array(shuffled_accs)
    p = float(np.mean(shuffled_accs >= observed_acc))
    return p, shuffled_accs


# ---------- Main ----------

def main():
    print("=" * 68)
    print("INTERIM Phase 3 classifier — pre-registered method, partial data")
    print("=" * 68)
    print(f"Run-tidspunkt: {datetime.now().isoformat()}")
    print()

    print("[1/5] Loading raw expressions ...")
    raw = load_raw()
    print(f"      Total rows: {len(raw)}")
    print()

    print("[2/5] Cleanup (pre-registered §1) ...")
    clean, cstats = cleanup(raw)
    print(f"      Kept: {len(clean)}")
    print(f"      Raw per peer:   {dict(cstats['raw_per_peer'])}")
    print(f"      Kept per peer:  {dict(cstats['kept_per_peer'])}")
    print(f"      Dropped reasons per peer:")
    for peer, reasons in cstats["dropped"].items():
        if reasons:
            ratio = sum(reasons.values()) / cstats["raw_per_peer"][peer]
            flag = " ⚠ >30%" if ratio > 0.30 else ""
            print(f"        {peer:14s}  {dict(reasons)}  ({ratio:.0%}){flag}")
    # Cohort balance
    print()
    print("      Cohort balance (≥100 = OK, <100 = incomplete / interim):")
    peer_counts: dict[str, int] = {}
    for p in PEERS:
        n = cstats["kept_per_peer"].get(p, 0)
        peer_counts[p] = n
        flag = " ⚠ incomplete" if n < 100 else ""
        print(f"        {p:14s}  {n:4d}{flag}")
    print()
    # 2026-05-22 (Claude, after Codex audit): power-vurderings note.
    # Jarvis-cohort er typisk mindre end peer-cohorts under interim
    # fordi peers kører fast cadence mens Jarvis kun expresser når
    # heartbeat-triggers fyrer. Marker disparity'en eksplicit så
    # rapport-læsere ikke fejlfortolker class-balance som design-flaw.
    if peer_counts:
        max_n = max(peer_counts.values())
        min_n = min(peer_counts.values())
        if max_n > 0 and (max_n - min_n) / max_n > 0.20:
            ratio = min_n / max_n if max_n else 0.0
            print(
                f"      ⚠ POWER NOTE: class imbalance {min_n}–{max_n} expressions "
                f"({ratio:.0%}); jarvis-cohort typisk smaller "
                f"(heartbeat-triggered ≠ fixed-cadence). "
                f"Confusion-matrix tolkes per-row, ikke samlet."
            )
            print()

    print("[3/5] Loading embedder + featurizing ...")
    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    X = featurize(clean, embedder)
    y = np.array([r["peer_id"] for r in clean])
    print(f"      Feature matrix: {X.shape}  (384 emb + 5 prim + 14 vocab = 403)")
    print()

    print("[4/5] Train/test split (80/20 stratified, seed=42) + fit ...")
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=SEED, stratify=y
    )
    clf = LogisticRegression(
        max_iter=2000, random_state=SEED, n_jobs=1
    )
    clf.fit(X_tr, y_tr)
    y_pred = clf.predict(X_te)
    acc = accuracy_score(y_te, y_pred)
    chance = 1 / len(PEERS)
    print(f"      Overall accuracy: {acc:.4f}  (chance = {chance:.4f}, target = 0.75)")
    print()
    print("      Per-class report:")
    print(classification_report(y_te, y_pred, digits=3, zero_division=0))
    print("      Confusion matrix (rows=true, cols=pred), order =", PEERS)
    labels = PEERS
    cm = confusion_matrix(y_te, y_pred, labels=labels)
    print("      " + "        ".join(f"{p[:6]:>6}" for p in labels))
    for i, p in enumerate(labels):
        print(f"      {p:14s}" + "  ".join(f"{v:>6d}" for v in cm[i]))
    print()

    print("[5/5] Permutation test (1000 shuffles) ...")
    p_val, perm_dist = permutation_p(clf, X_tr, y_tr, X_te, y_te, acc, n=1000)
    print(f"      Observed acc: {acc:.4f}")
    print(f"      Permutation mean acc: {perm_dist.mean():.4f}  std: {perm_dist.std():.4f}")
    print(f"      Permutation p-value:  {p_val:.4f}")
    print(f"      Pre-registreret tærskel: p < 0.05  →  {'SIGNIFICANT' if p_val < 0.05 else 'NOT significant'}")
    print()

    # Jarvis-specific recall
    jarvis_recall = float(
        np.mean(y_pred[y_te == "jarvis"] == "jarvis") if (y_te == "jarvis").any() else 0
    )
    print(f"      Jarvis-specific recall: {jarvis_recall:.4f}  (target = 0.75)")

    # Critical confusion: Jarvis ↔ ollama_local
    jarvis_idx = labels.index("jarvis")
    ollama_idx = labels.index("ollama_local")
    jv_to_ol = cm[jarvis_idx, ollama_idx]
    ol_to_jv = cm[ollama_idx, jarvis_idx]
    jv_total = cm[jarvis_idx].sum()
    ol_total = cm[ollama_idx].sum()
    print(
        f"      Jarvis→ollama_local confusion: {jv_to_ol}/{jv_total} "
        f"= {jv_to_ol/jv_total:.2%} (low = god — adskilt)"
    )
    print(
        f"      ollama_local→Jarvis confusion: {ol_to_jv}/{ol_total} "
        f"= {ol_to_jv/ol_total:.2%}"
    )
    # Claude vs Claude_jp confusion (test om JP-seed påvirker)
    c_idx = labels.index("claude")
    cjp_idx = labels.index("claude_jp")
    print(
        f"      Claude↔Claude_jp confusion: "
        f"{cm[c_idx, cjp_idx]}+{cm[cjp_idx, c_idx]}/"
        f"{cm[c_idx].sum()+cm[cjp_idx].sum()} "
        f"= {(cm[c_idx, cjp_idx]+cm[cjp_idx, c_idx])/(cm[c_idx].sum()+cm[cjp_idx].sum()):.2%}"
    )
    print()

    # δ-konvergens (preliminary): cosine distance to Jarvis centroid
    print("[δ-preview] Cosine-distance til Jarvis centroid (kun embedding-del, 384 dim):")
    emb_only = X[:, :384]
    jarvis_centroid = emb_only[y == "jarvis"].mean(axis=0)
    jarvis_centroid /= np.linalg.norm(jarvis_centroid) + 1e-9
    for p in PEERS:
        if p == "jarvis":
            continue
        peer_emb = emb_only[y == p]
        if len(peer_emb) == 0:
            continue
        # Cosine distance pr expression
        cos_sim = peer_emb @ jarvis_centroid
        cos_dist = 1 - cos_sim
        print(f"        {p:14s}  mean_dist={cos_dist.mean():.4f}  std={cos_dist.std():.4f}  n={len(peer_emb)}")
    print()

    # Welch's t-test: claude_jp < claude ?  glm_jp < glm ?
    def cosdist(peer):
        m = emb_only[y == peer]
        return 1 - (m @ jarvis_centroid) if len(m) else None

    for plain, jp in [("claude", "claude_jp"), ("glm", "glm_jp")]:
        d_plain = cosdist(plain)
        d_jp = cosdist(jp)
        if d_plain is None or d_jp is None:
            continue
        t = stats.ttest_ind(d_jp, d_plain, equal_var=False, alternative="less")
        sig = "✓ SIGNIFICANT" if t.pvalue < 0.025 else "✗ ikke signifikant"
        print(
            f"      H: {jp} cosine-dist < {plain} cosine-dist  "
            f"|  mean Δ = {d_jp.mean() - d_plain.mean():+.4f}  "
            f"|  t = {t.statistic:.3f}  p = {t.pvalue:.4f}  {sig}  (Bonferroni α=0.025)"
        )
    print()
    print("=" * 68)
    print("INTERIM RESULTAT — endelig kørsel 2026-05-28 22:16 (7 dage post-restart)")
    print("=" * 68)


if __name__ == "__main__":
    main()
