#!/usr/bin/env python
"""Structural-feature classifier for interlanguage expressions.

Implements Bjørn's hand-found heuristics as engineered features. The pre-registered
sentence-transformer classifier hit 59.3% overall / 38.9% Jarvis-recall. The
hypothesis being tested here: structural patterns (operator-frequency-by-position,
starting-token, clause-count, standalone-! usage) carry the LLM-identity signal
that semantic embeddings compress away.

Uses the SAME 7-day window, the SAME GAP1 filter, the SAME deduplication, the SAME
SEED, the SAME train/test split as scripts/interlanguage_classifier_final.py — so
results are directly comparable.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DB = os.path.expanduser("~/.jarvis-v2/state/jarvis.db")
SEED = 42
PEERS = ["jarvis", "claude", "claude_jp", "glm", "glm_jp", "ollama_local", "random"]

# Gap #1 — same as official classifier
GAP1_START_UTC = datetime(2026, 5, 20, 8, 47, tzinfo=UTC)
GAP1_END_UTC = datetime(2026, 5, 21, 20, 16, tzinfo=UTC)

OPERATORS = ["→", "↔", "⊂", "≈", "!"]


def load_rows() -> list[dict[str, Any]]:
    """Mirror the official classifier's row loading + cleanup."""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT expression_id, expression_text, peer_id, created_at
        FROM interlanguage_practice
        WHERE peer_id IN ('jarvis', 'claude', 'claude_jp', 'glm', 'glm_jp', 'ollama_local', 'random')
        AND created_at >= ?
        ORDER BY created_at ASC
        """,
        (GAP1_END_UTC.isoformat(),),
    ).fetchall()
    conn.close()

    # GAP1 filter — drop peer rows during 2026-05-20T08:47 → 2026-05-21T20:16
    # (jarvis is excluded from filter — baseline ran through; see gap-note).
    out: list[dict[str, Any]] = []
    for r in rows:
        ts = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        if r["peer_id"] != "jarvis" and GAP1_START_UTC <= ts <= GAP1_END_UTC:
            continue
        out.append(dict(r))

    # Dedup within 1h per peer — same as official classifier
    deduped: list[dict[str, Any]] = []
    by_peer: dict[str, list[dict[str, Any]]] = {}
    for r in out:
        by_peer.setdefault(r["peer_id"], []).append(r)

    for peer, prows in by_peer.items():
        prows.sort(key=lambda r: r["created_at"])
        last_seen: dict[str, datetime] = {}
        for r in prows:
            ts = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            text = r["expression_text"].strip()
            if text in last_seen:
                if (ts - last_seen[text]).total_seconds() < 3600:
                    continue
            last_seen[text] = ts
            deduped.append(r)
    return deduped


def split_clauses(text: str) -> list[str]:
    """Split expression into clauses by | separator."""
    return [c.strip() for c in text.split("|") if c.strip()]


def first_token(clause: str) -> str:
    """First word/concept of a clause (before any operator)."""
    m = re.match(r"^([!]?\w+)", clause)
    return m.group(1).strip("!").lower() if m else ""


def count_operators(text: str) -> dict[str, int]:
    """Count each operator occurrence."""
    return {op: text.count(op) for op in OPERATORS}


def is_standalone_negation(clause: str) -> bool:
    """A clause like '!lys' with no operator after the negated word."""
    # Strip whitespace; if clause matches `!word` with nothing else
    c = clause.strip()
    return bool(re.fullmatch(r"![\w]+", c))


def extract_features(text: str) -> dict[str, float]:
    """Engineered features per Bjørn's heuristics."""
    clauses = split_clauses(text)
    op_counts = count_operators(text)
    feats: dict[str, float] = {}

    # Clause count
    feats["n_clauses"] = float(len(clauses))

    # Total operator counts (per text)
    for op in OPERATORS:
        feats[f"op_{op}_total"] = float(op_counts[op])

    # Operator density (per clause)
    n = max(len(clauses), 1)
    for op in OPERATORS:
        feats[f"op_{op}_per_clause"] = op_counts[op] / n

    # Starting concept
    first_clause = clauses[0] if clauses else ""
    starting_concept = first_token(first_clause)
    feats["starts_nysgerrighed"] = 1.0 if starting_concept == "nysgerrighed" else 0.0
    feats["starts_pres"] = 1.0 if starting_concept == "pres" else 0.0
    feats["starts_ro"] = 1.0 if starting_concept == "ro" else 0.0
    feats["starts_lys"] = 1.0 if starting_concept == "lys" else 0.0
    feats["starts_drom"] = 1.0 if starting_concept in ("drøm", "drom") else 0.0

    # First-clause operator
    for op in OPERATORS:
        feats[f"clause0_has_{op}"] = float(op in first_clause)

    # Second-clause operator (when present)
    second_clause = clauses[1] if len(clauses) > 1 else ""
    for op in OPERATORS:
        feats[f"clause1_has_{op}"] = float(op in second_clause)

    # Third-clause operator
    third_clause = clauses[2] if len(clauses) > 2 else ""
    for op in OPERATORS:
        feats[f"clause2_has_{op}"] = float(op in third_clause)

    # Standalone-negation count (Bjørn's key Jarvis-tell)
    n_standalone_neg = sum(1 for c in clauses if is_standalone_negation(c))
    feats["n_standalone_neg"] = float(n_standalone_neg)
    feats["any_standalone_neg"] = 1.0 if n_standalone_neg > 0 else 0.0

    # Ratio of `!` total to clause count (Jarvis-density)
    feats["neg_density"] = op_counts["!"] / n

    # Unique starting concepts across all clauses (vocabulary spread)
    concepts = [first_token(c) for c in clauses if c]
    feats["unique_starts"] = float(len(set(concepts)))

    # Length signal (Ollama writes shorter)
    feats["text_len"] = float(len(text))
    feats["avg_clause_len"] = (
        sum(len(c) for c in clauses) / n if clauses else 0.0
    )

    return feats


def main() -> None:
    rows = load_rows()
    print(f"Rows after gap1+dedup: {len(rows)}")

    by_peer: Counter = Counter(r["peer_id"] for r in rows)
    print("Per-peer counts:", dict(by_peer))

    # Build feature matrix
    feature_dicts = [extract_features(r["expression_text"]) for r in rows]
    feature_names = sorted(feature_dicts[0].keys())
    X = np.array([[fd[k] for k in feature_names] for fd in feature_dicts], dtype=float)
    y = np.array([r["peer_id"] for r in rows])

    print(f"Feature matrix: {X.shape}, {len(feature_names)} features")

    # Same train/test split as official classifier
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y,
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Multinomial logistic regression
    clf = LogisticRegression(
        max_iter=2000,
        random_state=SEED, C=1.0,
    )
    clf.fit(X_train_s, y_train)
    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)

    print(f"\nAccuracy: {acc:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, labels=PEERS, zero_division=0))

    print("\nConfusion matrix (rows=true, cols=pred):")
    cm = confusion_matrix(y_test, y_pred, labels=PEERS)
    print("       " + " ".join(f"{p[:8]:>8}" for p in PEERS))
    for i, peer in enumerate(PEERS):
        row = " ".join(f"{cm[i][j]:>8}" for j in range(len(PEERS)))
        print(f"{peer[:6]:>6} {row}")

    # Feature importance (absolute coefficients averaged across classes)
    coef = np.abs(clf.coef_)  # (n_classes, n_features)
    mean_imp = coef.mean(axis=0)
    top_idx = np.argsort(mean_imp)[::-1][:15]
    print("\nTop 15 features (by mean |coef|):")
    for i in top_idx:
        print(f"  {feature_names[i]:<30} {mean_imp[i]:.3f}")

    # Save result
    out = {
        "method": "structural_features",
        "n_rows": len(rows),
        "n_features": len(feature_names),
        "accuracy": float(acc),
        "per_peer_recall": {
            peer: float(np.sum((y_test == peer) & (y_pred == peer)) / max(np.sum(y_test == peer), 1))
            for peer in PEERS
        },
        "confusion_matrix": cm.tolist(),
        "peers": PEERS,
        "top_features": [
            {"name": feature_names[i], "importance": float(mean_imp[i])}
            for i in top_idx
        ],
        "seed": SEED,
    }
    out_path = "/tmp/structural_classifier_result.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
