#!/usr/bin/env python
"""Binary: jarvis vs ollama_local — pre-check for Phase 4.

ollama_local in Phase 3 was already deepseek-v4-flash:cloud (same arch as
jarvis full runtime). Difference between the two cohorts was:
  - ollama_local: bare peer_runner protocol prompt (mood injected, no
    awareness, no memory, no identity files)
  - jarvis: full runtime context (awareness, memory, prompt-contract,
    identity files, recall-before-act)

If the structural classifier separates them at ≥65% binary accuracy,
runtime carries identity ALREADY proven by Phase 3 data — no new
cohort needed for Phase 4 (the comparison is essentially the same).

This script uses the SAME features and SAME train/test methodology as
scripts/interlanguage_structural_classifier.py.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import shuffle as sk_shuffle

# Local re-import: feature extractor from the Phase 3 structural script
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from interlanguage_structural_classifier import extract_features, load_rows  # type: ignore

SEED = 42


def main() -> None:
    rows = load_rows()
    rows = [r for r in rows if r["peer_id"] in ("jarvis", "ollama_local")]
    print(f"Rows (jarvis + ollama_local): {len(rows)}")

    by_peer: dict[str, int] = {}
    for r in rows:
        by_peer[r["peer_id"]] = by_peer.get(r["peer_id"], 0) + 1
    print(f"Per-peer: {by_peer}")

    feature_dicts = [extract_features(r["expression_text"]) for r in rows]
    feature_names = sorted(feature_dicts[0].keys())
    X = np.array([[fd[k] for k in feature_names] for fd in feature_dicts], dtype=float)
    y = np.array([r["peer_id"] for r in rows])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = LogisticRegression(max_iter=2000, random_state=SEED, C=1.0)
    clf.fit(X_train_s, y_train)
    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)

    print(f"\nBinary accuracy (jarvis vs ollama_local): {acc:.4f}")
    print(f"Chance baseline: 0.5000")
    print(f"Phase 4 weak threshold: 0.60")
    print(f"Phase 4 strong threshold: 0.65")

    print("\nClassification report:")
    print(classification_report(y_test, y_pred, labels=["jarvis", "ollama_local"], zero_division=0))

    print("\nConfusion matrix (rows=true, cols=pred):")
    cm = confusion_matrix(y_test, y_pred, labels=["jarvis", "ollama_local"])
    print(f"            jarvis  ollama")
    print(f"  jarvis    {cm[0][0]:>6}  {cm[0][1]:>6}")
    print(f"  ollama    {cm[1][0]:>6}  {cm[1][1]:>6}")

    # Permutation test (200 shuffles)
    print("\nRunning permutation test (200 shuffles)...")
    perm_count = 0
    rng = np.random.default_rng(SEED)
    for i in range(200):
        y_shuf = sk_shuffle(y_train, random_state=int(rng.integers(0, 2**31)))
        clf_p = LogisticRegression(max_iter=2000, random_state=SEED, C=1.0)
        clf_p.fit(X_train_s, y_shuf)
        acc_p = accuracy_score(y_test, clf_p.predict(X_test_s))
        if acc_p >= acc:
            perm_count += 1
    perm_p = perm_count / 200
    print(f"perm_p = {perm_p:.3f}")

    # Top features
    coef = np.abs(clf.coef_).flatten()
    top_idx = np.argsort(coef)[::-1][:10]
    print("\nTop 10 features by |coef|:")
    for i in top_idx:
        sign = "+" if clf.coef_.flatten()[i] > 0 else "-"
        print(f"  {sign} {feature_names[i]:<30} {coef[i]:.3f}")

    print("\n--- DECISION ---")
    if acc >= 0.65:
        print(f"Accuracy {acc:.3f} ≥ 0.65 → STRONG: runtime materially shapes voice.")
        print("Phase 4 question is essentially already answered by Phase 3 data.")
        print("New jarvis_bare runner is NOT NEEDED — can proceed to write Phase 4 report directly.")
    elif acc >= 0.60:
        print(f"Accuracy {acc:.3f} ∈ [0.60, 0.65) → WEAK: runtime has measurable effect.")
        print("Recommend running the stricter jarvis_bare cohort to disambiguate.")
    elif acc >= 0.50:
        print(f"Accuracy {acc:.3f} ∈ [0.50, 0.60) → INCONCLUSIVE.")
        print("Must run jarvis_bare cohort for a clean answer.")
    else:
        print(f"Accuracy {acc:.3f} < 0.50 → sampling noise around chance.")
        print("Runtime has no detectable effect on voice — H1 likely false.")

    out = {
        "method": "binary_jarvis_vs_ollama_local",
        "n_jarvis": int(by_peer.get("jarvis", 0)),
        "n_ollama_local": int(by_peer.get("ollama_local", 0)),
        "accuracy": float(acc),
        "perm_p": float(perm_p),
        "confusion_matrix": cm.tolist(),
        "top_features": [
            {"name": feature_names[i], "abs_coef": float(coef[i])}
            for i in top_idx
        ],
        "seed": SEED,
    }
    with open("/tmp/binary_jarvis_vs_ollama_result.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
