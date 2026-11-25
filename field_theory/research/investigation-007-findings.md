# Investigation 7: is lock-in a function of the expert loss gap?

**Status:** completed, **inconclusive** — the instrument cannot reach its own
question. Protocol frozen in `experiments/exp_007_gradient/PROTOCOL.md` and
committed before any measurement was computed. Run preserved in
`artifacts/exp_007_gradient/run_20261125_v4/`.

## What was asked

Investigation 5 found lock-in on sunspots; Investigation 6 found the relation
did not transfer to CO₂. Investigation 6's own Limitation named the untested
explanation — that `previous_month` is near-optimal by construction on CO₂ —
and its Questions section asked the discriminating version: *is there a source
where the experts are equally good, and does the mechanism then stay responsive
indefinitely?*

Investigation 7 asked whether the collapse to one expert is governed by the
**expert loss gap** rather than by the source.

## Instrument

No new observational series. The disagreement between experts was graded on the
two preserved series by blending each expert toward the mean of the other two
with weight `b ∈ {0.0, …, 1.0}`, and the mechanism was run at every blend. The
constants and the weighting rule are imported from `experiment_005_learning`,
not retyped.

The control was frozen in the protocol: at `b = 0` the run must reproduce the
preserved Investigation 5 and 6 figures for `long_continuity_continued`.

## Control: passed, after one correction

| Source | Effective experts | MAE |
|---|---:|---:|
| sunspots | 1.0000000005 (preserved 1.000) | 14.8512578623 (preserved 14.8513) |
| CO₂ | 1.8856506370 (preserved 1.8856506370006225) | 1.3023798659 (preserved 1.3023798658761925) |

The first version of the control compared against the **three-decimal** figure
`1.886` quoted in the Investigation 6 findings, with a `1e-6` tolerance, and
reported an instrument fault for a `0.0003` difference. That difference was
rounding in the report, not divergence in the mechanism. The control now
compares against the full-precision values from the preserved result file.

## Result: the instrument's independent variable is not monotone

The blend does not shrink the gap monotonically. Blending each expert toward
the mean of the other two makes the three predictions converge; once they are
close, the *difference* between their losses is dominated by noise, and the gap
turns and grows again:

| Blend | 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 1.0 |
|---|---:|---:|---:|---:|---:|---:|
| sunspots gap | 2.1019 | 1.5313 | 0.8947 | 0.2290 | 0.4544 | 1.0620 |
| CO₂ gap | 0.0554 | 0.0409 | 0.0234 | 0.0058 | 0.0117 | 0.0275 |

Both sources turn at the same blend, 0.7. That is the instrument's shape, not a
property of either source.

The consequence is visible in the outcome variable. Effective experts rise and
then fall — and the fall appears in mechanisms that have **no lock-in to
remove**:

| Mechanism | sunspots peak → end | CO₂ peak → end |
|---|---|---|
| one encounter | 2.91 → 2.57 | 3.00 → 3.00 |
| short continuity | 2.62 → 1.82 | 2.99 → 2.81 |
| long continuity | 1.07 → 1.02 | 2.62 → 1.04 |

`one_encounter` has retention 0 and cannot lock in, yet it falls on sunspots.
A fall that appears where there is nothing to remove is not evidence that
lock-in eased.

## Verdict

`inconclusive_instrument_cannot_reach_question`.

Condition 1 fired — the collapse is not monotone in the blend — but condition 4
also fired: the gap the condition depends on is itself not monotone. A
falsification that rests on a non-monotone independent variable does not
falsify the hypothesis; it shows the instrument cannot test it.

Condition 2 could not fire at all: **zero** matched-gap pairs exist. The two
sources' gap ranges do not overlap — sunspots span 0.11 to 2.10, CO₂ spans
0.003 to 0.055 — so "do the sources agree at the same gap?" is unanswerable
with this instrument. An earlier version of the code counted the absence of
pairs as a failed condition, which turned "the instrument cannot reach the
question" into a finding. That is corrected: an unreachable condition carries
no verdict.

## What this does and does not establish

**Established:** the blend instrument cannot grade expert disagreement on these
two series. The gap is not monotone in the blend, and the two sources' gap
ranges do not overlap, so neither falsification condition can be read as a
result about the mechanism.

**Not established:** whether lock-in depends on the loss gap. The question
remains open, and Investigation 6's Limitation remains untested.

**Also not established:** anything about field, identity, perspective,
experience, or access. Nothing here says whether the Sun or the atmosphere
"learns".

## What a working instrument would need

The failure is specific and fixable. The blend changes the predictions and the
gap together, so it cannot hold the gap fixed while varying something else.
Two routes avoid that:

- **Construct the gap directly.** Choose expert predictions whose pairwise
  losses differ by a prescribed amount, rather than blending real predictions
  and measuring whatever gap results. The gap then becomes the input, not an
  output.
- **Find a source with a naturally graded gap.** A series where two experts are
  genuinely comparable for a sustained period would test the question without
  a constructed blend at all — which is what Investigation 6's question asked
  for in the first place.

The first route is cheap and stays inside the preserved data. The second is the
one that would answer the question as originally posed.

## Questions raised

- Does the collapse depend on the gap at all, or on the *stability* of the gap
  over time rather than its mean?
- Is the turn at blend 0.7 a property of three experts specifically, or does it
  appear with two and four?
- If the gap is constructed directly, does the threshold sit at a fixed value
  across both sources — and is that value a property of the learning rate?
