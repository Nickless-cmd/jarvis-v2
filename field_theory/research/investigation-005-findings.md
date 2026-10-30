# Investigation 5: error, consequence, learning, and continuity

**Status:** completed independent-source exploration with one declared post-hoc
audit, 2026-10-30.

## Evidence boundary and provenance

Investigation 5 asks whether the distinctions among error, consequence,
learning, and continuity can be observed separately. It does not ask whether a
solar process learns. The observation source and the computational mechanisms
have different evidence status:

- The observed series is the WDC-SILSO version 2.0 monthly mean total sunspot
  number, an external process not generated for this project.
- The expectation experts, error normalization, adaptive weight update,
  retention values, and reset are deliberately constructed instruments.
- Their behavior on held-out chronological observations is measured.
- Any relation to Bjørn's broader progression remains an interpretation, not an
  observed mechanism in the Sun.

The protocol and implementation were committed as revision `e9a732ca9` before
the source CSV was downloaded or inspected. The preserved run is
`artifacts/exp_005_independent/silso_20261030_e9a732ca9/`.

Source provenance:

- publisher: WDC-SILSO, Royal Observatory of Belgium, Brussels;
- dataset: monthly mean total sunspot number, version 2.0;
- DOI: `10.24414/qnza-ac80`;
- license: CC BY-NC 4.0;
- preserved byte digest:
  `47:49:cc:16:c6:8e:06:73:f5:6e:c8:50:67:4d:05:c4:c8:7c:9d:3c:b8:48:5f:45:35:19:31:b3:82:2f:3f:3e`;
- definitive, non-missing observations: 3,330, from 1749-01 through 2026-06;
- excluded at collection: three publisher-marked provisional values and no
  `-1` missing values.

WDC-SILSO describes the values as arithmetic monthly means of available daily
total sunspot numbers. They remain instrumented and historically revised
records. The analysis did not use the supplied uncertainty or observation
count fields as prediction inputs. It made no CT105 query, and Investigation
4's reserved prospective outcomes remain untouched.

## What was deliberately constructed

Three fixed experts saw only prior values:

1. the previous month;
2. the trailing 12-month mean;
3. the value 132 months earlier.

The 132-month expert encodes an approximate 11-year-cycle perspective; its
period was not discovered by this run. Each adaptive mechanism converted the
experts' post-outcome normalized errors into next-month access weights. Four
retention conditions ranged from the most recent encounter only (`0.0`) to
undecayed cumulative loss (`1.0`). Continued variants carried development
state through 1999 into evaluation; reset variants discarded retained losses
immediately before 2000-01.

The fixed-uniform control deliberately retained a cumulative error ledger but
never allowed it to affect weights. This constructs a consequence without
adaptive response. The adaptive rules construct learning under the protocol's
narrow definition because error changes a later weighting. Neither construction
is an empirical discovery about natural learning.

## Primary observations

The previous-month expert had the lowest development mean absolute error and
was frozen as the selected fixed expert. It remained the best individual
expert in the 318-month evaluation. The lag-132 expert was substantially worse
than both shorter-history experts; merely supplying a cycle-shaped relation did
not make it useful month to month.

Evaluation measurements are:

| Mechanism | MAE | RMSE | Normalized absolute error | Effective experts | Mean weight change |
|---|---:|---:|---:|---:|---:|
| Fixed uniform | 17.8609 | 24.4061 | 0.9420 | 3.000 | 0.000 |
| Fixed selected previous month | 14.8513 | 21.0017 | **0.4297** | 1.000 | 0.000 |
| One encounter, continued | 14.4462 | 20.6927 | 0.4441 | 2.480 | 0.398 |
| Short continuity, continued | **14.0282** | 20.0394 | 0.4489 | 1.599 | 0.145 |
| Long continuity, continued | 14.8513 | 21.0017 | 0.4297 | 1.000 | approximately 0 |
| Cumulative continuity, continued | 14.8513 | 21.0017 | 0.4297 | 1.000 | 0.000 |
| Long continuity, reset | 14.4150 | 20.4453 | **0.4283** | 1.123 | 0.021 |
| Cumulative continuity, reset | 14.4548 | 20.4862 | 0.4286 | 1.120 | 0.021 |

There is no single winner. Short continuity has the lowest ordinary absolute
error; the reset long-continuity variant has the lowest predeclared normalized
absolute error; and the fixed previous-month expert is simpler and close to
both. The uniform control is much worse because it permanently includes the
poor lag-132 expert. Adaptation is not being compared with an artificially weak
control alone: it is also compared with the development-selected fixed expert.

These are descriptive differences on one chronological evaluation period.
There is no sampling-based uncertainty interval, source replication, or fixed
success threshold.

## Observation: prior history changed later access, but not monotonically

Continued and reset mechanisms received identical evaluation observations.
Their predictions nevertheless differed because their accessible retained
losses differed:

| Retention | Different evaluation predictions | Mean absolute difference | Last difference |
|---|---:|---:|---|
| One encounter | 1 / 318 | 0.0440 | 2000-01 |
| Short continuity | 263 / 318 | 0.2559 | 2023-12 |
| Long continuity | 189 / 318 | 2.2293 | 2026-06 |
| Cumulative continuity | 95 / 318 | 2.2874 | 2007-11 |

This is a causal fact about the paired software mechanisms because history
reset is their only declared difference. It is not evidence that natural
perspective or identity works this way. Persistence is also non-monotonic:
undecayed cumulative histories did not remain observably different longest.
Both cumulative variants eventually concentrated on the same expert, erasing
their output difference despite retaining different numerical histories.

## Surprising result: continuity became lock-in

The continued long-retention and cumulative mechanisms assigned effectively
all weight to the previous-month expert in all 318 evaluation rows. Their
predictions became indistinguishable from the fixed selected expert. The
continued cumulative mechanism used exactly one-hot weights throughout.

Resetting the retained losses at 2000 initially restored access to the other
experts. The reset long and cumulative mechanisms gave the trailing-12 expert
dominant weight for 30 and 31 evaluation months respectively before also
converging toward the previous-month expert. Both reset variants slightly
improved every aggregate error measure relative to their continued versions.

Thus retention preserved historical selection but removed most subsequent
adaptive capacity. Under this update rule, more continuity did not mean more
continuing learning. It meant that new consequences were too small relative to
accumulated history to change access. This is an observed property of the
constructed mechanism, not a general law favoring forgetting or reset.

## Post-hoc audit: why metrics disagree

After primary inspection, one declared post-hoc audit divided evaluation
outcomes at their observed quartiles: 17.95, 62.3, and 113.8. These boundaries
and all interval findings are exploratory.

Compared with the fixed previous-month expert, continued short continuity:

- worsened mean absolute error in the lowest outcome quartile from 5.3300 to
  5.9156 and normalized error from 1.0140 to 1.1186;
- changed little in the second quartile;
- improved mean absolute error in the third quartile from 16.9557 to 15.0335;
- improved it in the highest quartile from 24.8025 to 22.7645.

Normalized error deliberately gives a fixed-sized miss more weight when the
outcome is small. One low-value month, 2007-11, added 17.50 more absolute error
than the fixed expert and 4.60 more normalized error. Meanwhile, several
high-value months produced large absolute improvements with modest normalized
effects. The metrics therefore answer different questions; one is not a
corrected version of the other.

## Inferences supported only under stated conditions

1. **Consequence and learning can be instrumentally separated.** The uniform
   control retained changing error state with no change in later weights. The
   adaptive variants changed later weights. This separation is true by design,
   while their measured trajectories were not preordained.
2. **Learning and improvement are different.** Every adaptive variant changed
   response, yet the resulting advantage depended on the metric and retention
   condition. Some retained learning collapsed into the fixed baseline.
3. **Learning and continuity are different.** Short continuity remained
   responsive; long continuity preserved prior organization so strongly that
   it became inert. A continuing mechanism can preserve its identity and rule
   while losing practical adaptability.
4. **Same current information can support different expectations after
   different histories.** Continued/reset pairs establish this narrowly for
   the declared update rule. The differences can later disappear when distinct
   histories lead to the same concentrated access.
5. **A relation's availability does not ensure its use or value.** The lag-132
   expert was always available but was heavily downweighted and individually
   inaccurate for one-month expectation.

## What contradicted or constrained earlier expectations

- More retained history did not monotonically preserve a richer adaptive
  perspective. It often reduced the effective perspective to one expert.
- The cyclic source did not make the explicit 132-month relation a strong
  one-month predictor.
- The mechanism with lowest ordinary absolute error did not have the lowest
  normalized error. “Learning helped” is underspecified without naming the
  consequence that matters.
- Resetting historical state did not necessarily harm continuity of useful
  expectation; it slightly improved the long-retention variants here.

## What cannot be determined

- Whether learning is ontologically distinct from an ordinary state transition.
- Whether the Sun or the observation network contains any analogous learning,
  filter, perspective, identity, or experience mechanism.
- Whether the chosen experts are a defensible model of information access
  outside this experiment.
- Whether another learning rate, loss, split, retention family, or expert set
  would reverse the findings. Changing them now would be a new exploration.
- Whether differences generalize to another solar cycle or another independent
  process.
- Whether standard deviations, observation counts, source revisions, or
  provisional values would change the interpretation.
- Whether the evaluation differences exceed what would arise under an
  appropriate stochastic or generative model of the series.

## Questions raised

- Can retained history be represented without cumulative evidence becoming
  practically irreversible?
- Is adaptability a component of continuity, a competing requirement, or a
  relation that depends on scale?
- Which observable criterion distinguishes useful learning from persistent
  error-driven change without defining learning as prediction success?
- Would two mechanisms with different internal histories but identical outputs
  count as different perspectives, latent perspectives, or the same observable
  perspective?
- Does the metric conflict persist in a second independently chosen process?
- Can a controlled intervention distinguish change caused by consequence from
  change that would have occurred through an autonomous state transition?

No result validates the full conceptual progression. The strongest result is
narrower: the distinctions prevent a misleading conclusion. Error-driven
change occurred, but continuity sometimes preserved the change so strongly
that later consequences ceased to reorganize access.
