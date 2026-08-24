# 0009. Route every model call through one gated, validated boundary

* **Status**: accepted
* **Date**: 2026-08-23
* **Deciders**: Project Amanah team

## Context and Problem Statement

`spec.md` section 11 puts Gemini behind FastAPI and constrains what it may do:
structured classification, summarisation of already-computed facts, constrained
rationale, and policy matching. Section 11.2 requires caching, input and output
caps, and per-run and daily token budgets. Section 11.3 requires collected text to
be treated as untrusted data, forbids arbitrary SQL, network, publishing,
reporting, and identity-search tools, and requires the pipeline to use a
precomputed result or mark inference unavailable when policy does not permit a
transfer.

Those are a lot of rules to hold in mind at each call site. The question is
whether they are documented expectations that every caller must remember, or
properties of a boundary that a caller cannot get wrong.

There is a second problem specific to this product. A monitoring tool that
publishes a rate about a minority community is only defensible if that rate is
checkable. A model that computes, rounds, or invents a figure — even once, even
plausibly — makes every figure on the page unfalsifiable.

## Decision Drivers

* A new AI feature must be safe by default. "Remember to check the budget" is not
  a control.
* Refused material must never enter a request object, not merely never be sent.
* A published number must be traceable to something counted in SQL.
* The product must stay useful with no API key at all, so the offline pipeline
  and the demo do not depend on a provider.

## Considered Options

1. A thin HTTP helper, with each caller applying the policy, budget, and schema
   rules itself.
2. One client that owns every rule, with prompts as registered records.
3. A provider SDK with tool-calling available but unused by convention.

## Decision

**Option 2.** `amanah.ml.gemini.GeminiClient` is the only code in the service that
contacts the provider, and every rule is enforced inside it in a fixed order:
prompt lookup, data class, transfer authorization, cache, budget, truncation,
call, schema validation.

Four consequences of that shape are the decision, not implementation detail.

**Prompts are registered records, not strings.** A prompt has an id, a version, a
required Pydantic response model, and the set of data classes it may carry. An
unregistered id fails before anything else. A prompt that summarises aggregates
cannot be handed a post's text, because its declared data classes do not include
it — so a caller passing the wrong material is refused by the boundary rather
than caught in review.

**Instructions and content never concatenate.** The system instruction carries a
standing injection guard; collected text travels as a separate, delimited user
part. `render_system` and `render_content` are separate methods and there is no
call site that formats one into the other.

**No `tools` field is ever sent.** Option 3 was rejected for exactly this: a
capability that is absent cannot be reached by a bug, whereas a capability
available-but-unused is one refactor away from being used. Section 11.3's
prohibition is satisfied by the request never having the field.

**Generated numbers are verified, not trusted.** `amanah.ml.insights` extracts
every figure from generated prose and matches it against the facts the model
cited. Output that states a figure the bundle does not hold is stored with
`validation_status = rejected` and never served. The prompt asks the model to
cite; this check is what makes the citation mean something.

Unconfigured is a first-class state. With no key every call returns `deferred`,
classification writes a prediction row recording the deferral, deterministic
aggregation still runs, and the dashboard drops its narrative paragraph and
nothing else.

## Consequences

### Positive

* Adding an AI feature means registering a prompt and a response model. The
  policy gate, budget, cache, retry, and validation come with the boundary.
* A refused transfer is provable: the material never reaches a request object, so
  it cannot leak through a retry, a log line, or a cache entry.
* Every published figure traces to SQL. AI failure costs prose, never numbers.
* The whole pipeline runs offline, which is what makes the fixture demo and CI
  honest rather than a special path.

### Negative

* The numeric validator is deliberately blunt. It matches figures, not meaning,
  so it will occasionally reject a correct sentence whose number was formatted
  unusually, and it cannot judge whether a fair claim was drawn from a cited
  fact. That second job is human review's, and the tradeoff is accepted: a
  rejected correct sentence costs a regeneration, while an accepted invented
  figure costs the product its credibility.
* One class owns several concerns. They were kept together because they are one
  contract — an order of checks, where separating them would let a caller run
  them in a different order or skip one.
* The in-process cache is per replica. Durable caching of published narrative is
  a different mechanism (`insight_snapshots`), keyed by the same versions.

## Follow-ups

* Confidence thresholds are provisional until calibrated against a reviewed
  holdout (B-S14.4). The threshold version says so, and nothing reads a tier as a
  quality claim until that happens.
* A shared, `Retry-After`-aware rate limiter across every endpoint is B-S22.4.
  The assistant carries a narrower per-user limiter now because it is the one
  route where a signed-in person spends model tokens directly.
