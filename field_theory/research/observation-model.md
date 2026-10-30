# Minimal observation and provenance model

This is a set of distinctions, not a permanent object model or database design.
The first experiment expresses it with ordinary files because no current need
justifies a database.

## Layers

### 1. Source and method

A source describes where records came from. A method describes how they were
collected or generated. For simulated data, the generator, parameters,
pseudorandom mechanism, and runtime are part of provenance. A source label is
not a claim that the source's internal categories are ground truth.

### 2. Raw observation

A raw observation is the earliest preserved record available to this project,
not necessarily unmediated reality. It has a stable identifier and source-local
fields. “Raw” therefore means *not subsequently altered by this analysis*, not
free from instruments, choices, or prior transformations.

Raw files are content-digested. A run refuses to overwrite an existing output
directory. Corrections or new collection methods create new records with an
explicit relationship to the earlier version; they do not edit history.

### 3. Perspective or access specification

A perspective states which recorded distinctions and prior relations an
analysis can use. It may later include assumptions, transformations, model
class, or observer history. In experiment 001 it means only accessible fields
and must not be interpreted as subjective perspective.

### 4. Derived measurement

A measurement names its method version, parameters, input digest, and result.
Changing the statistic or its implementation creates a new derivation. A
measurement may be accurate under its definition while supporting a mistaken
interpretation.

### 5. Interpretation, hypothesis, and evidence relation

Interpretations and hypotheses belong in the research record rather than the
raw dataset. Evidence is a documented relation: an observation or measurement
may support, conflict with, remain ambiguous about, or be irrelevant to a
specific claim under stated assumptions. No result automatically inherits the
truth of a broader theory.

### 6. Revision

A revision records what changed, why, and which earlier conclusions depended
on the old method. Exploratory revisions are allowed after inspection. A later
confirmatory test must freeze its local claim, data boundary, method, and
evaluation rule before examining confirming data.

## Minimum run bundle

The current bundle contains immutable-by-convention raw records, a manifest,
versioned derived results, complete null measurements, a generated summary,
and a visualization. Git history adds change provenance. This is sufficient for
the first question. SQLite, a generic schema, notebooks with hidden execution
state, and a web interface are deferred until a concrete investigation needs
them.

## Known gaps

File-system immutability is enforced only by refusal to overwrite a run, not by
an append-only store. Git can still rewrite files. The current format does not
yet represent cross-run evidence links, human observers, uncertainty beyond
permutation summaries, or transformations as first-class records. Adding those
now would predict needs that have not emerged.
