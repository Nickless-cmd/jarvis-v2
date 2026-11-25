# Investigation 8: the gap as input — and the variable that turned out to matter

**Status:** completed, **falsified as stated** — but the falsification is
informative, and it identifies the variable Investigation 6 was missing.
Protocol frozen in `experiments/exp_008_direct_gap/PROTOCOL.md` (including the
addendum that introduces the assignment axis) and committed before any
measurement was computed. Run preserved in
`artifacts/exp_008_direct_gap/run_20261125_v2/`.

## What was asked

Investigation 7 could not reach its question because its blend changed the
predictions and the gap together. Its own closing section named the fix:
construct the gap directly, so it becomes the input. This experiment did that,
and then asked Investigation 6's open question: **at a prescribed expert loss
gap held identical across both sources, does the collapse depend on the source
at all — and if not, where is the threshold?**

## Instrument

`_normalized_loss(p, y) = |p − y| / (1 + |y|)` is invertible, so a prescribed
normalized loss `l` is produced exactly by `p = y + s · l · (1 + |y|)`. For each
month, `l_best` was measured on the real experts, so the difficulty of the month
is anchored in the observation. Three constructed experts then received
`l_best`, `l_best + gap/2`, `l_best + gap`.

The gap is the input by construction. **Measured calibration error: 6.7 · 10⁻¹⁶**
over every cell — the prescribed gap is the gap the mechanism actually sees.

Two assignments were run, because *which* expert is systematically best is a
separate variable from *how large* the gap is:

- **`fixed`** — one expert is best every month; the advantage is systematic.
- **`roving`** — the gap is the same size, but which expert is best follows the
  real series, so no one accumulates an advantage.

## Control: passed

At `gap = 0` all three constructed experts have identical losses, so the softmax
is uniform and the effective count is exactly 3. This is an analytic prediction,
not a figure lifted from an earlier run. **Measured 3.000000000 for all 16
(gap = 0) cells, tolerance 1e-9.**

## Result 1: with a systematic advantage, the source disappears

This is the finding the experiment exists for. At `fixed` assignment the two
physically unrelated series — monthly sunspot number and Mauna Loa CO₂ —
behave **almost identically**:

| gap | 0.0 | 0.005 | 0.01 | 0.02 | 0.05 | 0.1 | 0.2 | 0.4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sunspots, r=0.99 | 3.00 | 2.59 | 1.96 | 1.31 | 1.01 | 1.00 | 1.00 | 1.00 |
| CO₂, r=0.99 | 3.00 | 2.60 | 1.97 | 1.31 | 1.01 | 1.00 | 1.00 | 1.00 |

Across all 40 matched (retention, gap) pairs the **median** difference in
effective experts between the two sources is **0.0000**, and 39 of 40 sit below
the 0.25 threshold. The single exception is at `cumulative_continuity`
(`r = 1.0`), `gap = 0.002`, where the two sources read 1.005 and 1.913 — and
that exception is itself predicted: at `r = 1` the accumulated difference grows
linearly without bound, so the crossing is knife-edge and a hair's difference in
the starting condition separates the two.

**Established:** once the expert loss gap is held fixed and the advantage is
systematic, the source contributes essentially nothing. The collapse is a
property of the mechanism and the gap, not of sunspots or CO₂.

## Result 2: the threshold sits at (1 − r), within a factor of 2

The protocol predicted, before measurement, that the threshold would be
`gap ≈ (1 − r)`. In the `fixed` mode it is:

| retention | predicted `1 − r` | measured threshold (both sources) |
|---|---:|---:|
| short_continuity (0.9) | 0.100 | **0.2** |
| long_continuity (0.99) | 0.010 | **0.02** |
| cumulative_continuity (1.0) | 0.000 | **≤ 0.002** |

The measured threshold is consistently about twice the analytic value, and
identical on both sources. The accumulation argument is right in form; the
factor of two is the softmax's tolerance for a competitor that is not yet
vanished.

Condition 2 of the protocol fired (`partially_falsified_accumulation_argument_wrong`)
only because it also counts the `roving` mode, where the threshold is 0.05–0.1.
That is not the accumulation argument failing — it is the accumulation argument
not applying, because in `roving` there is no accumulated advantage to
threshold.

## Result 3: the variable that mattered is stability, not size

At `roving` assignment the two sources **do** diverge: 11 of 40 matched pairs
differ by more than 0.25, against 1 of 40 in `fixed`.

| gap | 0.01 | 0.02 | 0.05 | 0.1 | 0.2 |
|---|---:|---:|---:|---:|---:|
| sunspots, r=0.99 | 2.79 | 2.43 | 1.76 | 1.35 | 1.10 |
| CO₂, r=0.99 | 2.33 | 1.85 | 1.30 | 1.05 | 1.00 |

The reason is visible in what `roving` actually does on each series. On CO₂ the
strong monotone trend makes `previous_month` best nearly every month, so
`roving` is almost `fixed` there and collapses nearly as fast. On sunspots the
cycle rotates which expert wins, the advantage is spread, and the mechanism
stays responsive longer.

**This is Investigation 6's missing explanation, measured.** Its Limitation said
CO₂'s trend makes `previous_month` near-optimal by construction, and that this
was an interpretation it had not tested. It is now tested: the trend does not
matter because the gap is small. It matters because the trend makes the gap
**stable** — the same expert is ahead every month, which is exactly the `fixed`
condition, and under `fixed` both sources collapse identically.

Investigation 7's open question — *"does the collapse depend on the gap at all,
or on the stability of the gap over time rather than its mean?"* — is answered:
**on the stability.** The assignment axis changed the outcome in 20 of 80 cells.

## Verdict

`falsified` for the hypothesis as stated: *"the collapse is governed by the
expert loss gap, not by the source."* The source does matter — in the `roving`
mode. But the falsification locates the mechanism rather than defeating it:

- With a systematic advantage, the gap alone governs the collapse, and the
  source is irrelevant (median difference 0.0000, 39/40 cells).
- With a rotating advantage, the source matters — through how often the leading
  expert changes, not through how far apart the experts are.

So the honest statement is narrower than either investigation's framing: **the
collapse is governed by the accumulated advantage, which is the gap multiplied
by how persistently it points the same way.** Gap size sets the scale; stability
decides whether the scale is ever reached.

## What this does and does not establish

**Established:** with the gap constructed directly and a systematic advantage,
two physically unrelated series collapse identically, at a threshold near
`1 − r`. The failure of Investigation 6's transfer is a stability effect, not a
source effect.

**Not established:** that any real process behaves this way. The predictions are
constructed; only `l_best(t)` and the sign of the error come from the data. This
says nothing about field, identity, perspective, experience, or access, and
nothing about whether the Sun or the atmosphere "learns".

**Also not established:** that the threshold `2·(1 − r)` is universal. It is
bounded by this expert set, this learning rate, this loss, and these two sources.
The factor of two was not derived — it was measured.

## What a working instrument would need next

The stability axis is currently binary (`fixed` / `roving`). A graded version —
an expert that is best with probability `p` — would locate the transition
instead of bracketing it, and would give the second axis a measurable threshold
the way the first axis now has one.

## Questions raised

- Is the factor of two between `(1 − r)` and the measured threshold a property
  of `LEARNING_RATE = 2.0`, or of the softmax form?
- With three experts the middle one is placed at `gap/2` by construction. Does
  the threshold move if the middle expert sits elsewhere, or if there are two or
  four experts?
- Does a graded stability axis produce a threshold, and does it interact with
  the gap threshold or replace it?
