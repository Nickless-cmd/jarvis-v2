# Experiment 015 protocol — does a sharper weight win on the median over time?

**Frozen:** 2026-11-25, before the registered measurement was written.
This file is committed **on its own**, before the module that computes anything
exists, so `git log` can prove the ordering.

## Provenance — three probes ran before this protocol

Stated plainly because Investigation 10 could not make this claim and had to
record why. The probes are `/tmp/probe_015_sharp_over_time.py`,
`/tmp/probe_015b.py` and `/tmp/probe_015c.py`. They measured:

- the pooled alpha curve per calendar year, per cell half and per source;
- the conditional median, restricted to months where the sharpened weight does
  **not** land on the oracle;
- the per-cell robustness of that conditional median.

The probe numbers are quoted below as *probe* values, not as registered
results. The module recomputes everything from the sources.

## Where the question comes from

Investigation 14 measured the alpha curve on the pooled set. The median ratio
between the ensemble's forecast error and the best single expert falls
monotonically with alpha (1.217 at alpha=1, 1.007 at alpha=10, 1.000 at the
argmax limit), while the mean has an interior minimum at alpha=3 (8.058
against 8.398 and 8.253 at the two ends). Two aggregates, two different
answers.

Pooling also hides time. A median that falls on the pooled set can be carried
by a few periods. The question asked here is narrower and answerable:

> Does a sharper weight also win on the median **over time** — inside each
> calendar year, inside each cell half, and in each source?

## The mechanism that has to be named first

`w_e = exp(-L·(retained_e - min)) / Z` is monotone decreasing in `retained`,
so `argmax(w) == argmin(retained)` exactly. Sharpening to the limit is
therefore not a tuning of the weighting; it is **following the leader** — pick
the expert with the smallest accumulated loss. This is measured as a control
(38 340 of 38 340 months agree in the probe), because a report that calls
alpha->infinity "a sharper weight" without saying it is selection would be
naming an observation after a mechanism it does not have.

## The trap this experiment exists to avoid

A median can reach 1.000 for a reason that has nothing to do with improvement:
if more than half the months sit at **exactly** 1.000, the median is 1.000 by
construction. And a month sits at exactly 1.000 whenever the heaviest expert
**is** the oracle. In the probe that share is 57.0 % at the argmax limit
against 9.2 % at alpha=1.

So a falling median is compatible with a mechanism that is *worse* in the
months where it does not hit. That is the same error class as Investigations
10-14: a number that looks like an improvement while measuring its own target.

The registered measurement therefore reports **two** medians for every alpha:

1. the **unconditional** median over all months — the number one would quote;
2. the **conditional** median over months where the sharpened weight does not
   land on the oracle — the number that can only fall if the mechanism really
   improves.

A gain that exists only in (1) is the hit rate. A gain that survives in (2) is
the mechanism.

## Registered hypotheses

Each is a falsifiable statement with a decision rule.

**H1 — the aggregate conflict is real.** The alpha that minimises the
unconditional median is not the alpha that minimises the mean. *Falsified if*
the same alpha minimises both.

**H2 — moderate sharpening improves the conditional median.** For some alpha
in {2, 3, 5, 10}, the conditional median falls against alpha=1 by more than
1e-6. *Falsified if* no alpha in that set achieves it.

**H3 — the argmax limit wins only through hits.** At alpha->infinity the
unconditional median falls, but the conditional median does **not** fall.
*Falsified if* the conditional median also falls at the limit — which would
mean pure selection genuinely improves the non-hit months.

**H4 — the gain is stable over time.** Within every calendar year, the
unconditional median at the best moderate alpha is at or below the median at
alpha=1. *Falsified if* any year reverses it.

**H5 — the gain is not carried by a minority of cells.** The conditional
median improves in more than half of the cells at the best moderate alpha.
*Falsified if* half or fewer improve.

**H6 — the per-month win rate is below one half.** Sharpening wins in fewer
than 50 % of months, so the median gain is a gain in magnitude when it wins,
not in frequency. *Falsified if* the win rate reaches 50 % or more.

## Controls

- `argmax(w) == argmin(retained)` in every month. If it fails, the sharpening
  is not the leader-following it is claimed to be.
- `alpha = 1` reproduces the unsharpened weight exactly (conditional median
  equals unconditional median restricted to the same set).
- The oracle uses hindsight, per month. No sentence may imply the gap to it is
  closable operationally.
- The error is read from the **real** predictions, never the constructed ones.
  Investigation 12 established that the constructed error cancels the outcome;
  it is not undone here.
- `alpha -> infinity` reproduces `err_selected` exactly. A finite alpha only
  approaches the argmax, so the convergence check uses the hard limit.

## What would make this experiment worthless

If the conditional median is computed on a different month set for each alpha,
the comparison measures the sets. The registered measurement therefore
restricts every alpha to months that are non-hit **for that alpha**, and
reports the set size alongside. A shrinking set is itself a result: it says
how much of the improvement is the mechanism refusing to be measured.

## Not claimed

Nothing here is operational. The oracle is hindsight per month, the losses
driving the weights are constructed from the outcome (Investigation 12), and
the experts are replayed, not deployed. The only claim is about the shape of
the alpha curve and which aggregate it belongs to.
