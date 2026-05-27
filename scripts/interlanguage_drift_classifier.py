#!/usr/bin/env python
"""Phase 3 supplementary — drift-feature classifier for jarvis vs random.

Tests the pre-registered prediction (logged 2026-05-23 21:50 in
docs/superpowers/specs/2026-05-16-interlanguage-validation-gap-note.md):

    Per-expression features → jarvis-vs-random accuracy ≈ 50% (chance)
    Drift-derived features  → jarvis-vs-random accuracy ≥ 70%

The per-expression result is already shown by interlanguage_classifier_final.py
(jarvis row confuses 25/59 with random in the interim dry-run). This script
tests the second half: does adding drift features change the picture?

Method:
  1. For each peer: split expressions into chronological chunks of N=15.
  2. For each chunk: compute 19-dim snapshot feature (5 op-freqs + 14 vocab-freqs).
  3. ALSO compute 19-dim drift feature = (last_5_ops_freq - first_5_ops_freq)
     and analogous for vocab. Total 38-dim per chunk.
  4. Train two classifiers (snapshot-only vs snapshot+drift) on jarvis-vs-random
     chunks (binary classification).
  5. Compare accuracy. Pre-prediction: drift-features classifier > snapshot
     classifier by at least 20 percentage points.

Pre-registered, NOT post-hoc. Locked before final 28/5 data, output added
to Phase 3 report as the targeted test of identity-as-trajectory hypothesis.

Usage:
    /opt/conda/envs/ai/bin/python scripts/interlanguage_drift_classifier.py [--allow-early]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# Pre-registered constants — locked, do NOT tune
CHUNK_SIZE = 15  # expressions per chunk; chosen to balance n_chunks and drift signal
DRIFT_HALF = 5   # use first 5 and last 5 of chunk to estimate drift
OPS = ["→", "↔", "⊂", "≈", "!"]
VOCAB = [
    "nysgerrighed", "fokus", "ro", "agens", "signal",
    "drøm", "lys", "rytme", "kontinuitet", "tomhed",
    "grænse", "pres", "relation", "vægt",
]
RANDOM_SEED = 42
PHASE_END_UTC = datetime(2026, 5, 28, 22, 16, tzinfo=UTC)

DB_PATH = Path(os.environ.get("JARVIS_DB", "~/.jarvis-v2/state/jarvis.db")).expanduser()


def load_peer_expressions(peer: str) -> list[str]:
    """Pull all post-cleanup expressions for one peer, chronologically ordered."""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        """SELECT expression_text FROM interlanguage_practice
           WHERE peer_id = ?
             AND length(expression_text) >= 3
             AND length(expression_text) <= 200
           ORDER BY created_at ASC""",
        (peer,),
    ).fetchall()
    # Apply gap #1 filter — drop peer-rows in 2026-05-20T08:47Z → 2026-05-21T20:16Z
    # (jarvis rows are NOT filtered per gap-note rules)
    if peer != "jarvis":
        rows = conn.execute(
            """SELECT expression_text FROM interlanguage_practice
               WHERE peer_id = ?
                 AND length(expression_text) >= 3
                 AND length(expression_text) <= 200
                 AND NOT (created_at >= '2026-05-20T08:47:00+00:00'
                          AND created_at <  '2026-05-21T20:16:00+00:00')
               ORDER BY created_at ASC""",
            (peer,),
        ).fetchall()
    conn.close()
    # Must contain at least one operator (Phase 3 cleanup rule §1.2)
    return [r[0] for r in rows if any(op in r[0] for op in OPS)]


def featurize_snapshot(expressions: list[str]) -> np.ndarray:
    """19-dim: 5 op-freqs + 14 vocab-freqs (relative to total ops + total vocab)."""
    op_counts = Counter()
    vocab_counts = Counter()
    for txt in expressions:
        for op in OPS:
            op_counts[op] += txt.count(op)
        for v in VOCAB:
            vocab_counts[v] += txt.count(v)
    op_total = sum(op_counts.values()) or 1
    vocab_total = sum(vocab_counts.values()) or 1
    return np.array(
        [op_counts[op] / op_total for op in OPS]
        + [vocab_counts[v] / vocab_total for v in VOCAB]
    )


def featurize_chunk(chunk: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Return (snapshot_19, drift_19) where drift = late_half - early_half."""
    snapshot = featurize_snapshot(chunk)
    if len(chunk) < 2 * DRIFT_HALF:
        # Fallback: zero drift if chunk too small
        drift = np.zeros(len(snapshot))
    else:
        early = featurize_snapshot(chunk[:DRIFT_HALF])
        late = featurize_snapshot(chunk[-DRIFT_HALF:])
        drift = late - early
    return snapshot, drift


def build_chunks_for_peer(peer: str) -> list[tuple[np.ndarray, np.ndarray]]:
    """Chunk expressions chronologically; return [(snapshot, drift), ...]."""
    exprs = load_peer_expressions(peer)
    chunks = [exprs[i:i + CHUNK_SIZE] for i in range(0, len(exprs), CHUNK_SIZE)]
    # Drop trailing chunk if it's < CHUNK_SIZE (avoids partial-chunk noise)
    chunks = [c for c in chunks if len(c) == CHUNK_SIZE]
    return [featurize_chunk(c) for c in chunks]


def run(allow_early: bool) -> None:
    now = datetime.now(UTC)
    if now < PHASE_END_UTC and not allow_early:
        print(f"⛔ Gate: current UTC {now.isoformat()} is before Phase 2 end "
              f"{PHASE_END_UTC.isoformat()}. Pass --allow-early for dry-run.")
        sys.exit(2)

    print("=" * 72)
    print("Phase 3 — DRIFT-FEATURE CLASSIFIER (jarvis vs random)")
    print(f"Pre-registered: gap-note c1863124 (2026-05-23 21:50 UTC)")
    print(f"Run timestamp: {now.isoformat()}")
    print(f"Chunk size: {CHUNK_SIZE}, drift half: {DRIFT_HALF}")
    print("=" * 72)
    print()

    j_chunks = build_chunks_for_peer("jarvis")
    r_chunks = build_chunks_for_peer("random")
    print(f"jarvis chunks: {len(j_chunks)}")
    print(f"random chunks: {len(r_chunks)}")
    if len(j_chunks) < 10 or len(r_chunks) < 10:
        print(f"⚠ Insufficient chunks (<10 per class). Results unreliable.")

    # Build feature matrices
    X_snap = np.array([c[0] for c in j_chunks + r_chunks])
    X_drift_only = np.array([c[1] for c in j_chunks + r_chunks])
    X_combined = np.concatenate([X_snap, X_drift_only], axis=1)
    y = np.array([0] * len(j_chunks) + [1] * len(r_chunks))  # 0=jarvis, 1=random

    # Same train/test split for fair comparison
    idx = np.arange(len(y))
    train_idx, test_idx = train_test_split(
        idx, test_size=0.30, stratify=y, random_state=RANDOM_SEED
    )

    def fit_score(X: np.ndarray, label: str) -> float:
        Xtr, Xte = X[train_idx], X[test_idx]
        ytr, yte = y[train_idx], y[test_idx]
        clf = LogisticRegression(max_iter=2000, random_state=RANDOM_SEED)
        clf.fit(Xtr, ytr)
        acc = accuracy_score(yte, clf.predict(Xte))
        print(f"  {label:<30}  X.shape={X.shape}  test_acc={acc:.4f}")
        return acc

    print()
    print("CLASSIFIER ACCURACY (jarvis vs random, 70/30 stratified split):")
    print()
    acc_snapshot = fit_score(X_snap, "snapshot only (19-dim)")
    acc_drift = fit_score(X_drift_only, "drift only (19-dim)")
    acc_combined = fit_score(X_combined, "snapshot+drift (38-dim)")

    delta = (acc_drift - acc_snapshot) * 100
    print()
    print("=" * 72)
    print("PRE-REGISTERED HYPOTHESIS TEST (P1 from gap-note)")
    print("=" * 72)
    print()
    print(f"Snapshot-only accuracy:   {acc_snapshot:.4f}")
    print(f"Drift-only accuracy:      {acc_drift:.4f}")
    print(f"Combined accuracy:        {acc_combined:.4f}")
    print()
    print(f"Δ (drift - snapshot):     {delta:+.1f} percentage points")
    print()
    pred_threshold_snapshot = 0.55  # "near chance" ceiling
    pred_threshold_drift = 0.70     # drift-features target
    pred_delta = 20.0
    print("Pre-registered predictions:")
    print(f"  snapshot ≈ chance (~50%, ≤{pred_threshold_snapshot*100:.0f}%)")
    print(f"  drift ≥ {pred_threshold_drift*100:.0f}%")
    print(f"  Δ ≥ {pred_delta:.0f}pp")
    print()
    p_snap = "✓" if acc_snapshot <= pred_threshold_snapshot else "✗"
    p_drift = "✓" if acc_drift >= pred_threshold_drift else "✗"
    p_delta = "✓" if delta >= pred_delta else "✗"
    print(f"  {p_snap} snapshot near chance: {acc_snapshot:.3f} {'≤' if acc_snapshot <= pred_threshold_snapshot else '>'} {pred_threshold_snapshot:.2f}")
    print(f"  {p_drift} drift ≥ target:      {acc_drift:.3f} {'≥' if acc_drift >= pred_threshold_drift else '<'} {pred_threshold_drift:.2f}")
    print(f"  {p_delta} Δ ≥ {pred_delta:.0f}pp:           {delta:+.1f}pp")
    print()
    all_three = (acc_snapshot <= pred_threshold_snapshot
                 and acc_drift >= pred_threshold_drift
                 and delta >= pred_delta)
    print(f"Hypothesis P1 (identity-as-trajectory): {'SUPPORTED ✓' if all_three else 'NOT FULLY SUPPORTED ✗'}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 3 drift-feature classifier (run on/after 2026-05-28 22:16 UTC)",
    )
    parser.add_argument("--allow-early", action="store_true",
                        help="Override the 2026-05-28 gate (dry-run only)")
    args = parser.parse_args()
    run(allow_early=args.allow_early)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
