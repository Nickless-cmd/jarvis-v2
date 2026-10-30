# Experiment 006 protocol — is the learning/continuity relation transferable?

**Frozen:** 2026-10-30, before the NOAA series was parsed or any measurement was
computed. This file is committed before the run.

## Question

Investigation 5 found, on one external process (monthly sunspot number), that
increasing retention of accumulated loss did not increase continuing
adaptation: long and cumulative retention concentrated all weight on one
expert and became indistinguishable from a fixed baseline. That was recorded as
a property of the constructed mechanism, not a general law.

Investigation 6 asks the narrower, discriminating question:

> Does the retention→adaptation relation observed on the solar series also
> appear on a physically unrelated series, using the *same* mechanism, the
> *same* expert set, the *same* learning rate and the *same* evaluation rule?

This is a transfer test. It is not a test of Bjørn's full progression, and it
cannot be: the progression's terms (field, identity, perspective, experience)
are not operationalised here.

## Why this is not circular

The mechanism is fixed in advance and is *not* fitted to the new source. The
experts are the same three blind rules (previous value, trailing-12 mean,
lag-132). The learning rate, loss normalisation, retention family and
evaluation start rule are copied unchanged from `exp005.learning.1`.

If the result reproduces, the mechanism's behaviour is not an artefact of the
solar series. If it does not reproduce, the earlier finding was
source-dependent, and the "continuity became lock-in" observation must be
narrowed to the solar case.

## Source

- NOAA Global Monitoring Laboratory, Mauna Loa CO₂ monthly mean, `co2_mm_mlo.csv`
- Retrieved 2026-10-30; preserved byte digest recorded in the manifest.
- Column used: `average` (monthly mean, ppm). `-1` marks missing; none present.
- 823 monthly observations, 1958-03 through 2026-09.
- This is an instrumented, historically revised record from a physical
  measurement network. It is not generated for this project.

## Falsification, stated before measurement

The claim under test is: *"under this update rule, greater retention of
accumulated loss reduces continuing adaptive capacity, independent of source."*

It is contradicted if, on the CO₂ series:

1. the long/cumulative continued variants retain **effective experts > 1.5**
   through the evaluation period (i.e. they do not collapse to one expert), **or**
2. mean weight change for the long/cumulative continued variants is **not**
   near zero (threshold: > 0.05), **or**
3. the continued long/cumulative variants are **not** within 0.5 % MAE of the
   fixed selected expert.

Any one of these would show that lock-in is a property of the solar series or
of the specific expert set, not of the retention rule.

## What this experiment cannot show

- Nothing about field, identity, perspective, experience, or access as
  Bjørn's progression uses those terms.
- Nothing about whether the Sun or the atmosphere "learns".
- Nothing about whether a different expert set would reverse the result.
- No claim of universality. Two sources are two sources.

## Evaluation rule

Development period: all observations before 2000-01. Evaluation period:
2000-01 onward. The fixed expert is selected by development MAE, exactly as in
`exp005.learning.1`. All retention conditions and both continued/reset variants
are computed. No parameter is tuned after inspection.
