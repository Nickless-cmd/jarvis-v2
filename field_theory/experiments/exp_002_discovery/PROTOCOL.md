# Investigation 2: discovery under incomplete perspectives

**Mode:** exploratory discovery followed by a locally fixed confirmation.

**Protocol recorded:** 2026-10-30, before the preserved reference run.

## Question

Can a limited discovery procedure identify candidate structure without source
labels revealing what generated it, and can independent observations separate
persistent structure from patterns produced by search or unstable sampling?

This is not unrestricted discovery. It examines a declared family of binary
perspectives and therefore tests what is observable through that family.

## Procedural blinding

Generation and analysis are separate commands and modules. Generation assigns
opaque source identifiers and writes a source key that the analyzer never
reads. The analyzer receives only `observations.csv` and its generation
manifest. It selects candidates and writes results before a separate reveal
step connects opaque identifiers to generator descriptions.

This is not genuine investigator blinding: the same code author designed the
source families and the candidate catalog, and repository code makes both
inspectable. It prevents the automated selection procedure from reading the
answer, but it cannot remove designer expectations.

## Data boundary

Five sources produce the same recorded fields: `v0`, `v1`, `v2`, `v3`,
`context`, `outcome`, and source-local order. Their opaque identifiers carry no
generator meaning. The source collection includes independent pseudorandom
data, noisy relations, a relation that changes across samples, and a
deterministic process whose generating state is not exposed to analysis.

Each source has independently generated partitions:

- `discovery`: 1,024 rows, available for candidate search;
- `confirmation`: 2,048 rows, not used to select the candidate.

The split labels describe methodological roles, not universal evidence
categories. Inspecting all confirmation candidates after the run makes that
partition exploratory for future claims.

## Candidate perspectives

The discovery catalog is generated mechanically from the five recorded binary
variables:

- each variable alone;
- every unordered pair as a four-state joint representation;
- XOR transformations of every two-, three-, and four-variable subset;
- outcome sequence lags 1 through 12.

The score is plug-in mutual information with `outcome`, measured in bits. For a
lag candidate it is mutual information between earlier and later outcomes.
This catalog admits individual, contextual, higher-order, and chronological
relations without arbitrary expression search. It also omits many possible
structures. A source can contain real deterministic structure and remain
indistinguishable through these perspectives.

The highest discovery score is recorded as the candidate. Ties are resolved by
stable candidate name. The top five are retained to expose near alternatives,
not to create five confirmatory claims.

## Search and confirmation controls

For each opaque source, 250 outcome permutations preserve recorded predictors
and outcome balance while breaking their row-wise relationship.

On discovery data, every candidate is re-evaluated for every permutation and
the maximum is retained. This search-wide null describes how large the best
score can become merely because many perspectives were searched. It is not a
universal threshold.

The selected candidate is then evaluated without reselection on independent
confirmation data and compared with its candidate-specific permutation null.
The report preserves exceedance counts and a plus-one Monte Carlo rank
fraction. These are descriptive calibration measures, not permanent
pass/fail criteria.

Outcome permutation is not suitable for every possible source. It assumes
exchangeability and destroys sequence structure. For lag candidates the
shuffled sequence is used directly, but a source with nonstationarity could
still require a block or generative null in a later investigation.

## Reference-run parameters

- generation seed: 202,610,302;
- 1,024 discovery rows and 2,048 confirmation rows per source;
- 250 permutations per source and partition;
- lag range: 1–12;
- method versions: `exp002.generate.1`, `exp002.discover.1`.

These values are recorded choices for this run, not permanent standards.

## Interpretation boundaries

The investigation can show detectable statistical structure, whether a
selected representation persists on an independent sample, and whether that
representation is predictive in the narrow information-theoretic sense. It
cannot establish causality, subjective experience, a physical information
field, or a general principle that randomness is hidden order. Failure through
this catalog means “not detected here,” not “no structure exists.”
