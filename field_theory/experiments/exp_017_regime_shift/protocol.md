# Experiment 017 protocol — what does retention cost when the world changes?

**Frozen:** 2026-11-25, before any measurement in this experiment was computed.

This file is committed **on its own**, before the module that computes anything
exists, so `git log` can prove the ordering.

## Provenance — this one is clean, and that is worth saying

Investigations 10 through 16 each had to record that a probe ran before the
protocol was written. This one does not. No probe for this experiment exists:
`/tmp` holds probes 013a–e, 014, 014b, 015, 015b and 015c, and none of them
measures a regime shift. The first measurement of a regime shift happens after
this commit.

That is not a virtue I earned by being careful. It is a consequence of the
question being new: it was raised at the end of the evening, and there was no
time to explore it first.

## The question, and why it is different from the previous sixteen

Investigations 8–16 all measured the mechanism inside a **stationary** world.
The gap was fixed, the retention was fixed, and whichever expert happened to be
best stayed best. Every conclusion — that the error is data, that retention
reaches the forecast only through the weight vector, that a fixed alpha
transfers out of sample — was measured in a world that does not change.

A real world changes. The question is what the mechanism costs when it does,
and whether the cost is predictable from the retention knob alone.

## The design — an identity swap, not a constructed outcome

The trap from Investigation 10 was that `predictions` were built as
`outcome + sign*(l_best+delta)*scale`, so the outcome cancelled out of the error
and the measurement described the imposed gap. Nothing like that is allowed
here.

**The regime shift is an exchange of prediction series between expert names.**

Before the shift, expert `e_i` delivers the real predictions of series `s_i`.
After the shift, expert `e_i` delivers the real predictions of series `s_j`,
with `j = (i+1) mod n`. Every number that enters the accumulation is a real
prediction computed by `experiment_009._predict` from preserved observations.
The outcome is never touched, and no prediction is ever derived from it.

What changes is only **who is good**. The mechanism sees a permanent, complete
reversal of the ranking, and its memory is the only thing standing between it
and the new world.

The control is the identical accumulation with no swap. Same data, same gap,
same retention, same rank assignment. The difference between the two is the
shift and nothing else, and the control's residual must be exactly zero.

## What is measured

For each cell — source, expert set, assignment, retention, gap — the
accumulation runs twice, once with the swap and once without, and reports:

1. **Adaptation delay.** Months from the shift until the heaviest weight sits on
   the expert that owns the best series in the new world. If it never happens
   inside the window, the delay is the window length and that is reported as a
   censored value, not as a missing one.
2. **Accumulated excess loss.** The sum of `error_shift − error_control` over
   the months after the shift. This is the price of the memory, in the units the
   mechanism is actually scored in.
3. **Recovery.** Months until the shifted run's rolling 12-month error is back
   at or below the control's, or censored.
4. **Cost per unit of retention**, so a reader can see whether the cost is
   linear in the knob or has a knee.

## Registered hypotheses

Each is written so that it can fail.

**H1 — the cost is monotone in retention.** Retention 0 must cost **exactly
nothing**, because a mechanism that forgets everything cannot carry a stale
world forward. Retention 0.9 must cost more than 0, and 0.99 more than 0.9. If
retention 0 shows any excess loss above numerical noise, the design is wrong and
the experiment says nothing about retention.

**H2 — the adaptation delay grows with retention.** The delay at 0.99 must
exceed the delay at 0.9, which must exceed the delay at 0. The expected shape is
the logarithmic one implied by `retained ← r·retained + loss`: the half-life of
a memory with retention `r` is `ln(0.5)/ln(r)` months, which is 6.6 at 0.9 and
69.3 at 0.99.

**H3 — the delay is predictable from retention alone.** The measured delay must
land within a factor of two of the half-life formula. This is the hypothesis I
expect to fail, because the formula ignores how much better the new expert is;
if it fails, the failure is the finding.

**H4 — diversity shortens the recovery.** The four-expert set must recover
faster and accumulate less excess loss than the two-expert set at the same
retention. This is the operational claim: keeping more experts around buys
resilience, not accuracy. If it fails, the "diversity as self-correction"
reading is unsupported by this mechanism.

**H5 — the cost is larger when the new world is far from the old.** Splitting
cells by the gap between the old best expert's error and the new best expert's
error, the high-contrast half must carry the larger excess loss. If contrast
does not matter, then the cost is purely a function of the knob and the world's
shape is irrelevant.

## Controls, each able to fail the whole run

- **Identity holds.** `error == |Σ w·a|` on every month, worst residual 0.
- **The swap is a permutation.** After the swap, the multiset of prediction
  series in the cell is unchanged. If it is not, the cell was not a regime shift
  but a data change.
- **The no-swap control is a fixed point.** Running the control against itself
  gives excess loss exactly 0.
- **Retention 0 is inert.** H1's first clause doubles as a control: any excess
  loss at retention 0 above 1e-12 falsifies the design, not the hypothesis.
- **Errors are read from real predictions.** A guard reads `a` from `real` and
  a mutation that reads it from the constructed path must fail the tests.

## What would make the whole experiment worthless

If the excess loss at retention 0 is non-zero, the design leaks. If the control
residual is non-zero, the two runs are not the same mechanism. If the swap
changes the multiset of series, it is not a regime shift. Each of these is
checked before any hypothesis is reported, and a failure in any of them means
the verdict names the broken control rather than a hypothesis.
