# Investigation 15 — a sharper weight wins on the median, but not for the reason it looks

**Question:** does a sharper weight also win on the median **over time**?

**Answer:** yes for moderate sharpening, and no for the limit — and the
difference between the two is the whole result. The median at the argmax limit
falls to exactly 1.000 because 57 % of months land on the oracle, not because
the mechanism improves. Restricted to the months it misses, the limit is
*worse* than plain weighting.

## What Investigation 14 left open

The alpha curve on the pooled set: median 1.217 at alpha=1, 1.007 at alpha=10,
1.000 at the argmax limit, while the **mean** has an interior minimum at
alpha=3 (8.058 against 8.398 and 8.253 at the two ends). Two aggregates, two
answers — and pooling hides whether either survives inside a single year.

## The trap

A median reaches 1.000 whenever more than half the months sit at **exactly**
1.000, and a month sits exactly there when the heaviest expert **is** the
oracle. Sharpening raises that share:

| alpha | 1.0 | 2.0 | 3.0 | 5.0 | 10.0 | limit |
|---|---:|---:|---:|---:|---:|---:|
| months landing on the oracle | 9.2 % | 15.9 % | 22.3 % | 28.7 % | 34.6 % | **57.0 %** |

So a falling median is compatible with a mechanism that is worse everywhere it
does not hit. That is the same error class as Investigations 10–14: a number
that looks like an improvement while measuring its own target.

The measurement therefore reports **two** medians for every alpha — the
unconditional one, and the one restricted to months where the sharpened weight
does not land on the oracle.

## The two medians

38 196 months, 120 cells, two sources, five expert sets.

| alpha | unconditional median | conditional: base → sharp | conditional months |
|---|---:|---:|---:|
| 1.0 | 1.2166 | 1.3312 → 1.3312 | 34 699 |
| 2.0 | 1.1013 | 1.4342 → **1.2969** | 32 131 |
| 3.0 | 1.0639 | 1.5416 → **1.3509** | 29 673 |
| 5.0 | 1.0317 | 1.6891 → **1.3709** | 27 234 |
| 10.0 | 1.0069 | 1.8546 → **1.4050** | 24 988 |
| **limit** | **1.0000** | 2.0104 → **2.0922** | 16 407 |

Moderate sharpening improves the conditional median at every alpha tested
(0.137 to 0.450). The limit **reverses** it: 2.0104 becomes 2.0922, a loss of
0.082.

That reversal is the sharpest single number in this investigation. Per cell,
conditionally:

| | improved | worsened |
|---|---:|---:|
| alpha = 2 | 85 | 15 |
| alpha = 3 | 80 | 21 |
| alpha = 5 | 74 | 24 |
| alpha = 10 | 64 | 33 |
| **limit** | **14** | **79** |

And unconditionally the limit looks **exactly as good as alpha=2**: both
improve in 92 cells and worsen in 10. The entire apparent gain of the limit is
the hit rate. That is the trap closing.

## Two aggregates, two different alpha

The alpha that minimises the unconditional median is the **limit**; the alpha
that minimises the mean is **3.0**. They are not the same, and no single alpha
wins both.

## It is not carried by a period, but it is thin

The unconditional median at the best moderate alpha (10.0) is at or below the
alpha=1 median in **all 27 calendar years** — no single period carries it.

But the per-cell robustness is thinner than the year result suggests: at
alpha=10 the conditional median improves in **64 of 112 cells (57 %)**. An
exploratory probe run before this protocol measured the same per-cell test for
the other alphas and got 85 of 116 (73 %) at alpha=2 and 80 of 116 (69 %) at
alpha=3. **The alpha with the largest median gain is the least robust across
cells.** Choosing alpha on the pooled median gain picks the wrong alpha if the
goal is that the improvement holds everywhere.

That probe number is quoted as a probe observation, not as a registered result:
the protocol registered H5 only at the best moderate alpha.

## And it wins less often than it loses

| alpha | months it wins | win rate |
|---|---:|---:|
| 2.0 | 18 425 | 48.2 % |
| 3.0 | 18 232 | 47.7 % |
| limit | 17 795 | 46.6 % |

Sharpening improves the median while winning **fewer than half** of the months.
Both are true because the median is a magnitude when it moves, not a frequency.
The wins are larger than the losses — median win −0.079 against median loss
+0.061 at alpha=3 — but the worst single month loses by a factor of **2 019**.
A report that says "sharpening helps" without the win rate and the tail would be
selling the aggregate again.

## Controls

- `argmax(w) == argmin(retained)` in **38 340 of 38 340** months. Sharpening to
  the limit is *following the leader* — pick the expert with the smallest
  accumulated loss. Naming it "a sharper weight" without that sentence would
  name an observation after a mechanism it does not have.
- `err == |Σ w a|` recomposed from the stored weight and the real predictions:
  worst residual **0.0**.
- The limit reproduces `err_selected` exactly: worst gap **0.0**. A finite alpha
  only approaches the argmax, so the convergence check uses the hard limit — a
  check at alpha=50 would fail for arithmetic reasons and hide a real error.
- The error is read from the **real** predictions, never the constructed ones.

Three mutations were each caught and then reverted: reading `a` from the
constructed predictions (the error became gap-dependent, 2.75 instead of
invariant), reverting the `inf` label to a numeric format (the summary lookup
breaks), and computing the conditional median from the unconditional set (1.0
instead of 2.5 on a hand-built five-month case). The last one required pulling
the two medians into their own function — the frozen artifact cannot see a code
mutation, which Investigation 13 learned the hard way.

## What is not claimed

Nothing here is operational. The oracle is hindsight per month, the losses that
drive the weights are constructed from the outcome (Investigation 12), and the
experts are replayed, not deployed. The claim is about the shape of the alpha
curve and which aggregate it belongs to.

And the finding does not say "use alpha=3". It says that the median gain of
moderate sharpening is real, that the median gain of pure selection is not, and
that the alpha with the best median gain is not the alpha with the best per-cell
robustness. Anyone choosing alpha from this has to say which of those they want.
