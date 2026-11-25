# Investigation 17 — what retention costs when the world changes

> **Correction (Investigation 18, 2026-11-25).** The delays reported here are measured from the
> first **evaluated** month, not from the shift. The shift sits at `swap_at = len(rows)//2`,
> which is **1893-04** inside the development period; evaluation starts **2000-01**, 1281 months
> later, where `0.99^1281 = 2.6e-6` and the heaviest weight already sits on the structurally best
> expert at retention 0.9 and 0.99. Placed at the evaluation midpoint (2013-04) the same shift
> gives delays **2 / 24 / 150** months and excess loss **13.9 / 55.0 / 395.2**. The numbers below
> are real; the name "adaptation delay" is not.


Investigations 8–16 all measured the mechanism inside a **stationary** world: the
gap was fixed, the retention was fixed, and whichever expert happened to be best
stayed best. Every conclusion — that the error is data, that retention reaches
the forecast only through the weight vector, that a fixed alpha transfers out of
sample — was measured in a world that does not change.

This one changes exactly one thing. The world shifts.

## The design, and why it is not another constructed outcome

The shift is an **exchange of prediction series between expert names**. Before
the shift, expert `e_i` delivers the real predictions of series `s_i`; after it,
series `s_(i+1)`. Every number entering the accumulation comes from
`experiment_009._predict` run on preserved observations. The outcome is never
touched and no prediction is ever derived from it — which is the trap
Investigation 10 fell into and the reason Investigation 12's MAE measured the
imposed gap rather than skill.

The control is the identical accumulation with no swap. Same rows, same gap,
same retention, same rank assignment. The difference between the two runs is the
shift and nothing else.

This is also the first experiment in the series whose protocol was committed
**before any measurement existed**. No probe for a regime shift is in `/tmp`.
That is not a virtue I earned by being careful; the question was raised at the
end of the evening and there was no time to explore it first.

## The control that killed the protocol's first premise

The protocol said, and I quote it because the sentence is the finding:

> Retention 0 must cost **exactly nothing**, because a mechanism that forgets
> everything cannot carry a stale world forward.

**That is false, and the mechanism says so.** With

```
retained[e] ← retention · retained[e] + loss[e]
```

and `retention = 0`, `retained` is rebuilt from the previous month's loss every
step. The weight for month *t* is therefore built from month *t−1*'s loss. The
mechanism does not forget everything at retention 0. It remembers **exactly one
month**.

Measured: retention 0 carries a median excess loss of **0.242**, not zero, and
the worst cell reaches **7 349**. The control that pins this down — recomputing
month *t−1*'s constructed loss and comparing it against the stored `retained` —
lands at residual **0.0** on every cell. So the leak is not a bug. It is what
the mechanism does, and my premise was wrong about it.

This is the same error class the whole evening has been about: a sentence that
sounds right, written from what the mechanism *ought* to do rather than from what
it does. The control caught it because I wrote the control to be able to.

### A second property the same control exposed

The accumulation updates `retained` from **`predictions`**, not from `real`:

```python
losses = {expert: _normalized_loss(predictions[expert], outcome) ...}
retained = {expert: retention*retained[expert] + losses[expert] ...}
```

So what moves the weight is the **imposed gap**, while the error is measured on
the experts' real forecasts. The mechanism learns from one thing and is scored on
another. That is a property of the shared mechanism and not of this experiment,
but it belongs in the record: Investigations 12–16 measured the consequence of it
without ever stating it in one place.

## What held

| hypothesis | result |
|---|---|
| **H2** delay grows with retention | **held** — 6.0 → 8.5 → 126.0 months |
| **H3** delay predictable from retention alone | **held** — median ratio **1.52** |
| **H1b** cost strictly increasing (post hoc) | **held** — 0.242 → 3.400 → 164.83 |

The half-life implied by `retained ← r·retained + loss` is `ln(0.5)/ln(r)`:
**6.58** months at 0.9 and **68.97** at 0.99. The measured delay medians are 8.5
and 126.0. The ratio of measured to predicted has median **1.52** — inside a
factor of two, which is what H3 asked for and what I expected to fail.

The failure of the naive model is in the right direction and has a reason: the
delay is longer than the half-life because the weight has to move *past* the
half-way point and the rank order is rebuilt every month from the constructed
gap, so the memory and the new evidence compete for longer than a pure decay
would suggest.

## What failed, and the two failures that matter

### H4 — diversity reduces the damage but lengthens the recovery

| expert set | accumulated excess | recovery (months) |
|---|---:|---:|
| two experts | 33.19 | **11.0** |
| four experts | **8.09** | 23.5 |

Four experts accumulate **less** than a quarter of the excess loss of two — but
take **twice as long** to get their rolling error back to the control's level.

That is not a contradiction. Excess loss is *how much* the mechanism pays while
it is wrong; recovery is *how long* it stays measurably wrong. More experts
soften the peak and smear the tail. The "diversity buys resilience" reading is
half supported and half refuted by the same measurement, and reporting only the
first half would have been the flattering error.

### H5 — a large regime shift costs *less* than a small one

This one failed in the opposite direction from my prediction. Splitting the 180
cells at the median contrast between the old best expert's error and the new
best expert's error:

| contrast half | cells | median excess |
|---|---:|---:|
| low (the new world is close to the old) | 126 | **60.69** |
| high (the new world is far from the old) | 54 | **8.09** |

I predicted the high-contrast half would carry the larger cost, on the reasoning
that a bigger change is a bigger loss. The measurement says the reverse, and the
mechanism explains why: a large shift produces a **large, unambiguous signal**
that moves the weight quickly. A small shift is the dangerous case — the old
world keeps looking almost right, so the memory keeps winning by default and the
cost is paid quietly over many months.

That is the operationally useful finding of the whole experiment, and it is the
opposite of what I registered.

## Controls

All green, and each one able to fail the run:

- **Identity** `error == |Σ w·a|` on every month — worst residual **0.0**.
- **The swap is a permutation** — the multiset of series is unchanged, worst
  residual **0.0**. Without this the cell would be a data change, not a shift.
- **The unshifted path equals `_prepare`** byte for byte — verified in the code
  guard, not just at run time.
- **Retention 0 remembers exactly one month** — residual **0.0** after
  recomputing the constructed loss. This replaced the protocol's false premise.
- **The verdict names a broken control before a hypothesis** — a failed control
  must not be readable as a failed hypothesis.

## What this does and does not say

It says that in this mechanism, memory has a price measured in forecast error,
that the price rises monotonically with the retention knob, that its time scale
is within a factor of 1.5 of `ln(0.5)/ln(r)`, and that **small** shifts are more
expensive than large ones.

It does not say that retention is bad. Retention is what makes the weight stable
enough to be useful at all in a stationary world — Investigations 14 and 15
measured that side. What this experiment adds is the bill for the other side.

It also does not say anything yet about whether the mechanism can *detect* a
shift, as opposed to merely paying for it. Every number here is measured with the
outcome in hand, exactly as in Investigations 12–16. Whether a shift is
noticeable before the outcome arrives is the next question and it is a different
one.
