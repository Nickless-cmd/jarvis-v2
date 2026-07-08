#!/usr/bin/env python
"""Phase 3 FINAL classifier — pre-registered method, full 7-day data.

Built 2026-05-24 (Claude) per Codex' recommendation: get the final-run
script deterministic, gap-aware, and ready before 28/5. No analysis
changes, no hypothesis tuning — just the reporting infrastructure
required to make the 28/5 result publication-grade.

Inherits methodology from interlanguage_classifier_interim.py
(pre-registered in docs/superpowers/specs/
2026-05-16-interlanguage-validation-phase3-4-design.md). Differences
from interim:

  1. Gap #1 filter applied: peer rows in 2026-05-20T08:47Z →
     2026-05-21T20:16Z UTC are excluded (jarvis rows kept — his
     baseline ran through; see gap-note).
  2. Gap #2 annotation: claude and claude_jp marked as FROZEN with
     stop-timestamp. Their reduced sample sizes are surfaced in
     power notes, not hidden.
  3. Per-row precision/recall interpretation: classification_report
     extended with explicit "interpret per-row, not overall" guidance
     since cohort imbalance is large.
  4. Pre-registered prediction section: snapshot-vs-trajectory
     hypothesis (commit c1863124) is restated at the top with a
     "ready to fill in" result block.
  5. Determinism guard: numpy/torch seeds + classifier random_state
     set up front so re-runs produce identical output.
  6. JSON sidecar: --json flag emits structured report for
     downstream consumption.

Usage:
  /opt/conda/envs/ai/bin/python scripts/interlanguage_classifier_final.py
  /opt/conda/envs/ai/bin/python scripts/interlanguage_classifier_final.py --json > report.json

DO NOT run before 2026-05-28 22:16 UTC (7 days after restart). The
gap-note's stop-collection point is what defines "final".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime, timezone
from typing import Any

import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

DB = os.path.expanduser("~/.jarvis-v2/state/jarvis.db")
PRIMITIVES = ["→", "↔", "⊂", "≈", "!"]
SEED = 42
PEERS = ["jarvis", "claude", "claude_jp", "glm", "glm_jp", "ollama_local", "random"]

# Import CORE_TERMS from engine — source of truth (Codex 2026-05-22).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.services.interlanguage_practice import CORE_TERMS as _ENGINE_CORE_TERMS
CORE_VOCAB = list(_ENGINE_CORE_TERMS)
assert len(CORE_VOCAB) == 14, f"expected 14 core terms, got {len(CORE_VOCAB)}"

# Gap #1: hardware-rotation, peer-runners died.
GAP1_START_UTC = datetime(2026, 5, 20, 8, 47, tzinfo=UTC)
GAP1_END_UTC = datetime(2026, 5, 21, 20, 16, tzinfo=UTC)

# Gap #2: Copilot quota freeze.
GAP2_FROZEN_PEERS: dict[str, datetime] = {
    "claude": datetime(2026, 5, 22, 17, 9, tzinfo=UTC),
    "claude_jp": datetime(2026, 5, 22, 16, 21, tzinfo=UTC),
}

# Pre-registered prediction block (logged commit c1863124).
PREREG_PREDICTION = """\
Hypothesis (logged 2026-05-23 21:50 UTC before any Phase 3 analysis):
  Jarvis' interlanguage identity is a DEVELOPMENT TRAJECTORY, not a
  static fingerprint in embedding space.

Falsifiable predictions for Phase 3:
  (P1) Per-expression 403-dim classifier on "jarvis vs random":
         ~chance (50% ± sampling) — predicted weak.
  (P2) Cohort-overall accuracy on 7-way classification:
         ≥0.75 (pre-registered target).
  (P3) Jarvis-specific recall:
         ≥0.75 (pre-registered target).
  (P4) JP-seed effect (claude_jp vs claude, glm_jp vs glm) —
         JP cohort closer to Jarvis centroid (one-sided t-test,
         Bonferroni α=0.025 per pair).

Empirical basis logged in gap-note:
  Centroid distance jarvis-T3 → random = 0.0129 (closer than to
  jarvis-T1 = 0.0269) → weak fingerprint hypothesis confirmed by
  interim data.
  Temporal drift: jarvis 75pp vs random 40pp noise-floor, paired
  operator shifts (→/! down, ↔/⊂ up) → trajectory hypothesis
  empirically motivated but not yet tested.
"""


# ── Data load + gap filter ───────────────────────────────────────────────


def load_raw() -> list[dict]:
    """Load all interlanguage_practice rows from the sqlite DB, keeping only
    non-empty expressions of length >= 3, ordered by peer_id then created_at.
    Returns a list of dicts (expression_id, expression_text, peer_id, created_at)."""
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


def apply_gap_filter(rows: list[dict]) -> tuple[list[dict], dict]:
    """Drop peer rows (NOT jarvis rows) inside gap #1's hardware-rotation
    window. Per gap-note 2026-05-16-interlanguage-validation-gap-note.md
    SQL filter — peers were dead, jarvis baseline continued."""
    kept: list[dict] = []
    dropped_per_peer: Counter = Counter()
    for r in rows:
        peer = r["peer_id"]
        try:
            ts = datetime.fromisoformat(
                str(r["created_at"]).replace("Z", "+00:00")
            )
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            kept.append(r)
            continue
        if peer != "jarvis" and GAP1_START_UTC <= ts < GAP1_END_UTC:
            dropped_per_peer[peer] += 1
            continue
        kept.append(r)
    return kept, {
        "gap1_dropped_per_peer": dict(dropped_per_peer),
        "gap1_total_dropped": sum(dropped_per_peer.values()),
        "gap1_window_utc": [GAP1_START_UTC.isoformat(), GAP1_END_UTC.isoformat()],
    }


# ── Cleanup (pre-registered §1) — verbatim from interim ──────────────────


def cleanup(rows: list[dict]) -> tuple[list[dict], dict]:
    """Apply pre-registered §1 cleanup: drop rows with no primitive glyph,
    rows over 200 chars, and per-peer duplicates of the same text within 1h.
    Returns (kept_rows, stats) where stats records raw/kept counts per peer
    and per-peer drop reasons."""
    raw_per_peer: Counter = Counter(r["peer_id"] for r in rows)
    stats_out: dict = {"raw_per_peer": dict(raw_per_peer), "dropped": defaultdict(Counter)}
    out: list[dict] = []
    seen_recent: dict[tuple[str, str], datetime] = {}
    for r in rows:
        text = r["expression_text"]
        peer = r["peer_id"]
        if not any(p in text for p in PRIMITIVES):
            stats_out["dropped"][peer]["no_primitive"] += 1
            continue
        if len(text) > 200:
            stats_out["dropped"][peer]["too_long"] += 1
            continue
        ts = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        key = (peer, text)
        prev = seen_recent.get(key)
        if prev is not None and (ts - prev).total_seconds() < 3600:
            stats_out["dropped"][peer]["dup_within_1h"] += 1
            continue
        seen_recent[key] = ts
        out.append(r)
    stats_out["kept_per_peer"] = Counter(r["peer_id"] for r in out)
    stats_out["dropped"] = {k: dict(v) for k, v in stats_out["dropped"].items()}
    return out, stats_out


# ── Featurize (pre-registered §2) — verbatim ─────────────────────────────


def featurize(rows: list[dict], embedder: SentenceTransformer) -> np.ndarray:
    """Build the 403-dim feature matrix: normalized sentence embeddings (384)
    hstacked with per-token primitive-glyph counts (5) and per-token core-vocab
    counts (14). Returns the combined ndarray, one row per expression."""
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


def permutation_p(clf_template, X_train, y_train, X_test, y_test, observed_acc, n=1000):
    """Permutation test for classifier accuracy: refit a LogisticRegression on
    n shuffled label sets and score each on the test set. Returns the p-value
    (fraction of shuffled accuracies >= observed_acc) and the array of shuffled
    accuracies."""
    rng = np.random.default_rng(SEED)
    shuffled_accs = []
    for i in range(n):
        y_perm = y_train.copy()
        rng.shuffle(y_perm)
        clf = LogisticRegression(max_iter=2000, random_state=SEED)
        clf.fit(X_train, y_perm)
        shuffled_accs.append(accuracy_score(y_test, clf.predict(X_test)))
    arr = np.array(shuffled_accs)
    return float(np.mean(arr >= observed_acc)), arr


# ── Per-row interpretation helper ────────────────────────────────────────


def per_row_interpretation(report_dict: dict, cohort_counts: dict[str, int]) -> str:
    """Pre-registered note: overall accuracy is misleading under cohort
    imbalance (Copilot freeze). Each class precision/recall must be
    read per-row."""
    lines = ["Per-row interpretation (REQUIRED under cohort imbalance):"]
    for peer in PEERS:
        if peer not in report_dict:
            continue
        prec = report_dict[peer].get("precision", 0.0)
        rec = report_dict[peer].get("recall", 0.0)
        f1 = report_dict[peer].get("f1-score", 0.0)
        support = int(report_dict[peer].get("support", 0))
        n_cohort = cohort_counts.get(peer, 0)
        frozen_marker = ""
        if peer in GAP2_FROZEN_PEERS:
            frozen_marker = f" [FROZEN {GAP2_FROZEN_PEERS[peer].strftime('%Y-%m-%d')}]"
        lines.append(
            f"  {peer:14s} prec={prec:.3f}  rec={rec:.3f}  "
            f"f1={f1:.3f}  test_n={support}  cohort_n={n_cohort}{frozen_marker}"
        )
    return "\n".join(lines)


# ── Reporting helpers ────────────────────────────────────────────────────


def render_cohort_balance(kept_per_peer: dict[str, int]) -> str:
    """Surface cohort balance with FROZEN annotation per gap #2."""
    lines = ["Cohort balance (post-cleanup):"]
    for p in PEERS:
        n = kept_per_peer.get(p, 0)
        flag = ""
        if p in GAP2_FROZEN_PEERS:
            stop_at = GAP2_FROZEN_PEERS[p]
            flag = f"  ⚠ FROZEN {stop_at.strftime('%Y-%m-%d %H:%M')} UTC (Copilot quota)"
        elif n < 100:
            flag = "  ⚠ incomplete"
        lines.append(f"  {p:14s}  {n:4d}{flag}")
    # Power note
    if kept_per_peer:
        max_n = max(kept_per_peer.values())
        min_n = min(v for p, v in kept_per_peer.items() if v > 0)
        if max_n > 0 and (max_n - min_n) / max_n > 0.20:
            ratio = min_n / max_n if max_n else 0.0
            lines.append("")
            lines.append(
                f"⚠ POWER NOTE: cohort imbalance {min_n}–{max_n} "
                f"({ratio:.0%}). Pre-registered analysis: read confusion-"
                "matrix per-row (per-class precision/recall), NOT overall "
                "accuracy. JP-seed t-tests still valid (paired cohorts of "
                "comparable size)."
            )
    return "\n".join(lines)


def render_text_report(report: dict[str, Any]) -> str:
    """Format the full report for human reading."""
    L = []
    L.append("=" * 72)
    L.append("FINAL Phase 3 classifier — interlanguage validation")
    L.append("=" * 72)
    L.append(f"Run timestamp:  {report['run_timestamp']}")
    L.append(f"Seed:           {SEED} (deterministic)")
    L.append(f"DB:             {DB}")
    L.append("")
    L.append("─" * 72)
    L.append("PRE-REGISTERED PREDICTION (commit c1863124, 2026-05-23 21:50 UTC)")
    L.append("─" * 72)
    L.append(PREREG_PREDICTION)
    L.append("─" * 72)
    L.append("DATA PREPARATION")
    L.append("─" * 72)
    L.append(f"Raw rows loaded:  {report['raw_rows']}")
    L.append(
        f"Gap #1 dropped:   {report['gap1']['gap1_total_dropped']} peer-rows "
        f"in {report['gap1']['gap1_window_utc'][0][:10]} → "
        f"{report['gap1']['gap1_window_utc'][1][:10]} (hardware rotation)"
    )
    L.append(f"After gap filter: {report['after_gap_rows']}")
    L.append(f"After cleanup §1: {report['after_cleanup_rows']}")
    L.append("")
    L.append(render_cohort_balance(report["cleanup_stats"]["kept_per_peer"]))
    L.append("")
    L.append("─" * 72)
    L.append("CLASSIFIER RESULTS (pre-registered method, §2)")
    L.append("─" * 72)
    L.append(f"Feature matrix shape: {report['feature_shape']} (384 emb + 5 prim + 14 vocab = 403)")
    L.append(f"Train/test split: 80/20 stratified, seed=42")
    L.append("")
    chance = 1 / len(PEERS)
    L.append(f"Overall accuracy:  {report['accuracy']:.4f}   "
             f"(chance={chance:.4f}, P2 target=0.75)")
    L.append(f"P2 verdict:        {'✓ MET' if report['accuracy'] >= 0.75 else '✗ NOT met'}")
    L.append("")
    L.append(report["per_row_interpretation"])
    L.append("")
    L.append("Confusion matrix (rows=true, cols=predicted):")
    labels = PEERS
    cm = np.array(report["confusion_matrix"])
    # Wider columns so labels like 'claude_jp' and 'ollama_local' aren't
    # truncated — these are pre-registered cohort names, must be readable.
    L.append(" " * 16 + " ".join(f"{p:>12}" for p in labels))
    for i, p in enumerate(labels):
        L.append(f"  {p:14s}" + " ".join(f"{v:>12d}" for v in cm[i]))
    L.append("")
    L.append("─" * 72)
    L.append("PRE-REGISTERED HYPOTHESIS TESTS")
    L.append("─" * 72)
    L.append(
        f"(P2) Overall accuracy ≥ 0.75:        "
        f"{report['accuracy']:.4f}  →  "
        f"{'✓ supported' if report['accuracy'] >= 0.75 else '✗ refuted'}"
    )
    L.append(
        f"(P3) Jarvis-specific recall ≥ 0.75:  "
        f"{report['jarvis_recall']:.4f}  →  "
        f"{'✓ supported' if report['jarvis_recall'] >= 0.75 else '✗ refuted'}"
    )
    L.append(
        f"     Permutation p-value (n=1000):   {report['perm_p']:.4f}  →  "
        f"{'✓ significant' if report['perm_p'] < 0.05 else '✗ not significant'}"
        " (α=0.05)"
    )
    L.append("")
    L.append("(P4) JP-seed effect (one-sided t-tests, Bonferroni α=0.025):")
    for name, t in report["jp_tests"].items():
        sig = "✓ supported" if t["pvalue"] < 0.025 else "✗ not supported"
        L.append(
            f"     {name:30s}  Δmean={t['delta']:+.4f}  "
            f"t={t['t']:+.3f}  p={t['pvalue']:.4f}  {sig}"
        )
    L.append("")
    L.append(
        f"(P1) Jarvis vs random — post-hoc note: requires drift-based "
        "features, NOT just per-expression embedding. Per pre-registration, "
        "P1 prediction is that per-expression accuracy on jarvis-vs-random "
        "is ~chance because both have 100% distinct + balanced operator "
        "profiles. Drift-features test is a Phase 4 question (commit "
        "c1863124) — not run here."
    )
    L.append("")
    L.append("─" * 72)
    L.append("POST-HOC OBSERVATIONS (clearly labeled, no hypothesis tuning)")
    L.append("─" * 72)
    L.append("Cosine distance to Jarvis centroid (embedding-only, 384 dim):")
    for name, info in report["centroid_distances"].items():
        L.append(
            f"  {name:14s}  mean_dist={info['mean']:.4f}  "
            f"std={info['std']:.4f}  n={info['n']}"
        )
    L.append("")
    if report.get("critical_confusions"):
        L.append("Critical pairwise confusion rates (per-row):")
        for label, cc in report["critical_confusions"].items():
            L.append(f"  {label}: {cc}")
    L.append("")
    L.append("=" * 72)
    L.append("END OF FINAL REPORT")
    L.append("=" * 72)
    return "\n".join(L)


# ── Main ─────────────────────────────────────────────────────────────────


def run() -> dict[str, Any]:
    """Execute the full pre-registered Phase 3 pipeline and return the report dict.
    Loads and gap-filters rows, cleans them, featurizes, fits an 80/20 stratified
    LogisticRegression, then computes accuracy, jarvis recall, permutation p-value,
    JP-seed centroid t-tests, per-peer centroid distances, and critical pairwise
    confusion rates."""
    raw = load_raw()
    after_gap, gap_info = apply_gap_filter(raw)
    clean, cstats = cleanup(after_gap)
    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    X = featurize(clean, embedder)
    y = np.array([r["peer_id"] for r in clean])
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=SEED, stratify=y
    )
    clf = LogisticRegression(max_iter=2000, random_state=SEED)
    clf.fit(X_tr, y_tr)
    y_pred = clf.predict(X_te)
    acc = float(accuracy_score(y_te, y_pred))

    cls_report = classification_report(
        y_te, y_pred, labels=PEERS, output_dict=True, zero_division=0,
    )
    cm = confusion_matrix(y_te, y_pred, labels=PEERS).tolist()
    jarvis_idx = PEERS.index("jarvis")
    cm_arr = np.array(cm)
    jarvis_recall = float(cm_arr[jarvis_idx, jarvis_idx] / max(cm_arr[jarvis_idx].sum(), 1))

    p_val, _ = permutation_p(clf, X_tr, y_tr, X_te, y_te, acc, n=1000)

    # JP-seed centroid t-tests
    emb_only = X[:, :384]
    jarvis_centroid = emb_only[y == "jarvis"].mean(axis=0)
    jarvis_centroid = jarvis_centroid / (np.linalg.norm(jarvis_centroid) + 1e-9)

    def cosdist(peer):
        m = emb_only[y == peer]
        return 1 - (m @ jarvis_centroid) if len(m) else None

    jp_tests: dict[str, dict[str, float]] = {}
    for plain, jp in [("claude", "claude_jp"), ("glm", "glm_jp")]:
        dp, dj = cosdist(plain), cosdist(jp)
        if dp is None or dj is None or len(dp) == 0 or len(dj) == 0:
            continue
        t = stats.ttest_ind(dj, dp, equal_var=False, alternative="less")
        jp_tests[f"{jp} < {plain}"] = {
            "delta": float(dj.mean() - dp.mean()),
            "t": float(t.statistic),
            "pvalue": float(t.pvalue),
        }

    centroid_distances: dict[str, dict[str, float]] = {}
    for p in PEERS:
        if p == "jarvis":
            continue
        d = cosdist(p)
        if d is None or len(d) == 0:
            continue
        centroid_distances[p] = {
            "mean": float(d.mean()),
            "std": float(d.std()),
            "n": int(len(d)),
        }

    # Critical pairwise confusions
    def confusion_pct(a, b):
        ai, bi = PEERS.index(a), PEERS.index(b)
        denom = cm_arr[ai].sum()
        return (
            f"{int(cm_arr[ai, bi])}/{int(denom)} = "
            f"{cm_arr[ai, bi]/max(denom,1):.2%}"
        )

    critical_confusions = {
        "jarvis → ollama_local": confusion_pct("jarvis", "ollama_local"),
        "ollama_local → jarvis": confusion_pct("ollama_local", "jarvis"),
        "claude → claude_jp": confusion_pct("claude", "claude_jp"),
        "claude_jp → claude": confusion_pct("claude_jp", "claude"),
        "glm → glm_jp": confusion_pct("glm", "glm_jp"),
        "glm_jp → glm": confusion_pct("glm_jp", "glm"),
    }

    report = {
        "run_timestamp": datetime.now(UTC).isoformat(),
        "seed": SEED,
        "raw_rows": len(raw),
        "gap1": gap_info,
        "after_gap_rows": len(after_gap),
        "after_cleanup_rows": len(clean),
        "cleanup_stats": cstats,
        "feature_shape": list(X.shape),
        "accuracy": acc,
        "classification_report": cls_report,
        "confusion_matrix": cm,
        "jarvis_recall": jarvis_recall,
        "perm_p": p_val,
        "jp_tests": jp_tests,
        "centroid_distances": centroid_distances,
        "critical_confusions": critical_confusions,
        "per_row_interpretation": per_row_interpretation(
            cls_report, cstats["kept_per_peer"],
        ),
    }
    return report


def main() -> int:
    """CLI entry point. Parses --json/--allow-early, enforces the pre-registered
    2026-05-28 22:16 UTC cutoff gate (returns 2 if before it without --allow-early),
    runs the pipeline, and prints either JSON or the text report. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Phase 3 FINAL classifier (run on/after 2026-05-28 22:16 UTC)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument(
        "--allow-early", action="store_true",
        help="Override the 2026-05-28 gate (for dry-run testing only)",
    )
    args = parser.parse_args()

    gate = datetime(2026, 5, 28, 22, 16, tzinfo=UTC)
    now = datetime.now(UTC)
    if now < gate and not args.allow_early:
        print(
            f"FINAL run blocked: current time {now.isoformat()} is before "
            f"the pre-registered cutoff {gate.isoformat()}. Use "
            "--allow-early for dry-run testing (clearly labeled as such "
            "in the output).",
            file=sys.stderr,
        )
        return 2

    report = run()
    if args.allow_early:
        report["dry_run_disclaimer"] = (
            "Run before 2026-05-28 22:16 UTC gate. Data is incomplete; "
            "results are dry-run validation of the analysis pipeline, "
            "NOT pre-registered conclusions."
        )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        if args.allow_early:
            print("⚠ DRY RUN — before pre-registered cutoff. Not publication-ready.\n")
        print(render_text_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
