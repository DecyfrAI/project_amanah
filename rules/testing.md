# Testing Standards

## Philosophy

Tests exist to give engineers confidence to ship. A passing suite MUST mean the software
works for users — not merely that the code compiles or that mocked objects return expected
values.

- You MUST prefer **meaningful tests** over raw coverage percentages. A test that asserts a
  non-trivial invariant at 60% coverage is more valuable than a trivial getter-setter test that
  reaches 95%.
- Tests MUST be **honest**: a test that passes when the real behaviour is broken is worse
  than no test at all.
- Every test MUST have exactly one reason to fail. Multi-concern tests obscure root causes
  and discourage fixing.
- The test suite SHOULD serve as living documentation. A reader MUST be able to understand
  what a system does by reading its tests without consulting separate documentation.
- Teams MUST treat test code with the same review rigour as production code. Flawed tests
  compound over time.

### The Test Pyramid

Maintain a healthy distribution across three layers:

```
        /\
       /  \   E2E (few, high-confidence user journeys)
      /----\
     /      \  Integration (service boundaries, DB, queues)
    /--------\
   /          \  Unit (fast, isolated, numerous)
  /____________\
```

| Layer       | Speed     | Isolation  | Proportion |
|-------------|-----------|------------|------------|
| Unit        | < 100 ms  | Full       | ~70 %      |
| Integration | < 5 s     | Partial    | ~20 %      |
| E2E         | Minutes   | None       | ~10 %      |

You MUST NOT invert the pyramid. A suite that is majority E2E tests is slow, brittle, and
provides poor signal.

---

## Unit Tests

Unit tests MUST be **hermetic**: each test controls all inputs and observes all outputs
without relying on external state (network, filesystem, clock, randomness) that it does not
own.

### Rules

- A unit test MUST complete in under 100 ms. Tests that routinely exceed this SHOULD be
  moved to the integration layer or have their slow dependency replaced with a fast double.
- Unit tests MUST NOT share mutable state between test cases. Each test MUST set up its
  own fixture and tear it down (explicitly or via scope-limited construction).
- You SHOULD test **behaviour**, not implementation. Testing that `calculateDiscount` returns
  `15.00` for a `VIP` customer is meaningful; testing that it calls `_applyMultiplier` is not.
- You MUST include tests for boundary values, zero, empty collections, and `null`/`None`
  inputs wherever the contract admits them.
- You SHOULD name tests after the scenario, not the method:
  `test_discount_is_zero_when_cart_is_empty` not `test_calculateDiscount`.

### Example — Python

```python
# Good: tests behaviour, controls all inputs, no shared state
def test_invoice_total_includes_tax():
    items = [LineItem(price=Decimal("100.00"), quantity=2)]
    invoice = Invoice(items=items, tax_rate=Decimal("0.10"))
    assert invoice.total() == Decimal("220.00")

def test_invoice_total_is_zero_for_empty_cart():
    invoice = Invoice(items=[], tax_rate=Decimal("0.10"))
    assert invoice.total() == Decimal("0.00")
```

---

## Integration Tests

Integration tests verify that components work correctly **at their real boundaries**: database
queries return the right rows, message queues deliver events, HTTP clients parse responses.

### Rules

- Integration tests MUST use **real dependencies** (or containerised equivalents such as
  `testcontainers`) rather than mocks for the boundary under test.
- Integration tests MUST be **isolated at the data level**: each test either runs in a
  dedicated schema/database, or wraps its operations in a transaction that is rolled back
  after the test.
- You MUST NOT rely on test-execution order. Each integration test MUST be able to run
  standalone.
- Integration tests SHOULD validate error paths as well as happy paths: what happens when
  the database is unavailable, or when the queue message is malformed?
- Secrets and connection strings MUST be injected via environment variables. They MUST
  NOT be committed to the repository.

### Example — database round-trip

```python
# Uses a real (containerised) Postgres; rolls back after each test
@pytest.fixture(autouse=True)
def db_transaction(db_session):
    yield db_session
    db_session.rollback()

def test_user_is_persisted_and_retrieved(db_session):
    repo = UserRepository(db_session)
    repo.save(User(email="alice@example.com", role="admin"))
    fetched = repo.find_by_email("alice@example.com")
    assert fetched.role == "admin"
```

---

## End-to-End Tests

E2E tests confirm that the **full system behaves correctly from a user's perspective**: from
the outermost API or UI surface down through all services.

### Rules

- You MUST restrict E2E tests to a small set of **critical user journeys** (sign-up, checkout,
  core workflow). Every E2E test added increases pipeline duration and flake risk.
- E2E tests MUST run against a **dedicated, hermetically provisioned environment** — never
  against production, and never against a shared staging environment that other developers
  modify concurrently.
- E2E tests MUST be idempotent: running them multiple times against a clean environment
  MUST produce the same result.
- You SHOULD encode E2E assertions at the user-visible level (HTTP status codes, page
  content, returned JSON fields) rather than internal state.
- E2E tests that consistently take longer than 10 minutes SHOULD be reviewed for
  decomposition or parallelisation.

---

## Fixtures

Fixtures supply the pre-conditions a test requires. Well-designed fixtures prevent duplication
and make tests readable.

### Rules

- Fixtures MUST be **minimal**: include only the fields relevant to the test. Irrelevant fields
  SHOULD use clearly fake or default values so readers know they do not affect the outcome.
- Shared fixtures MUST be read-only. If a test needs to mutate a fixture, it MUST create its
  own copy.
- You SHOULD build fixtures with factory helpers rather than raw constructors so that schema
  changes require one update, not dozens.
- Fixture data MUST NOT be sourced from production or staging systems. It MUST be
  purpose-built synthetic data (see **Test Data**).

### Example — factory pattern

```python
# Factory with safe defaults; tests only override what they care about
def make_order(*, status="pending", total=Decimal("50.00"), items=None):
    return Order(
        id=uuid4(),
        status=status,
        total=total,
        items=items or [make_line_item()],
        created_at=datetime(2024, 1, 1),
    )

def test_fulfilled_order_cannot_be_cancelled():
    order = make_order(status="fulfilled")
    with pytest.raises(InvalidTransitionError):
        order.cancel()
```

---

## Test Data

### Rules

- Tests MUST NOT depend on data that pre-exists in any shared environment. All required
  data MUST be created as part of the test and cleaned up after.
- Production data MUST NOT be used in any automated test. Use **synthetic data** that
  structurally resembles production (realistic cardinality, representative edge cases) but
  contains no real user information.
- Large datasets required for performance or scale tests MUST be generated programmatically
  and checked into the repository as seed scripts, not as binary dumps.
- Test data files MUST be versioned alongside the tests that use them. Stale data MUST be
  removed.
- For AI/ML tests, evaluation datasets MUST include:
  - Representative happy-path examples
  - Known adversarial or edge-case inputs
  - Labelled expected outputs or rubric criteria for each row

---

## Mocking

Mocks are powerful and easily misused. Overuse produces tests that pass even when the real
integration is broken.

### Rules

- You MUST mock **only what you own or what crosses a process boundary** (external HTTP
  APIs, email services, payment gateways). You MUST NOT mock the system under test itself.
- You MUST NOT mock a dependency that you could use for real in a hermetic integration
  test. Using `testcontainers` for a real database is preferred to mocking a repository.
- Mocks MUST reflect the real contract of the dependency. When the dependency's API
  changes, the mock MUST be updated in the same commit.
- You SHOULD verify that mocked calls were actually made when call-count or argument
  correctness is part of the contract (e.g., confirming an audit log was written).
- You MUST NOT mock away error conditions to make a test pass. Unhappy-path mocks (HTTP
  500, network timeout) MUST be tested explicitly.

### Example — mock at the HTTP boundary only

```python
# Mock the external payment gateway; keep everything else real
@responses.activate
def test_checkout_records_payment_on_success(db_session):
    responses.add(
        responses.POST,
        "https://payments.example.com/charge",
        json={"status": "ok", "transaction_id": "txn_abc"},
        status=200,
    )
    order = make_order(status="pending", total=Decimal("99.00"))
    checkout_service = CheckoutService(db=db_session)
    checkout_service.process(order)
    assert db_session.query(Payment).filter_by(order_id=order.id).count() == 1
```

---

## Flaky Tests

A flaky test — one that passes and fails on the same code non-deterministically — MUST be
treated as a defect, not a nuisance.

### Rules

- Flaky tests MUST be quarantined (skipped or moved to a separate suite) within one
  business day of being identified. They MUST NOT block the main branch.
- Once quarantined, a flaky test MUST be fixed or deleted within **two weeks**. Quarantine
  is not a permanent state.
- The root cause of a flaky test MUST be documented in the issue tracker. Common causes:
  - Shared mutable state between tests
  - Real-time (`sleep`) assertions instead of event-driven waits
  - Hardcoded ports or paths that collide under parallelism
  - Non-deterministic ordering (maps, sets, query results without `ORDER BY`)
- Tests MUST NOT use `sleep` to wait for asynchronous events. Use polling with a timeout
  or an explicit synchronisation mechanism.
- You SHOULD track flake rates per test in CI. A test that exceeds a **1% flake rate** over a
  rolling 7-day window MUST be quarantined immediately.

---

## Regression Testing

A regression is a behaviour that worked and then broke. Regression tests exist to prevent the
same bug from recurring.

### Rules

- Every bug fix MUST be accompanied by a test that would have caught the bug. This test
  MUST fail on the unfixed code and pass on the fix.
- The regression test MUST be placed at the lowest layer of the pyramid that can demonstrate
  the bug. A parsing bug SHOULD be a unit test, not an E2E test.
- Regression tests MUST include a reference to the bug report or incident (e.g., a comment
  with the ticket ID) so future readers understand its purpose.
- Before closing a post-incident review, the team MUST confirm that a regression test for the
  root cause exists and has been merged.

### Example

```python
# Regression: order total was negative when a discount exceeded the item price.
# See: ISSUE-4821
def test_discount_cannot_make_order_total_negative():
    item = make_line_item(price=Decimal("10.00"), discount=Decimal("15.00"))
    order = make_order(items=[item])
    assert order.total() >= Decimal("0.00")
```

---

## Performance Tests

Performance tests MUST be written against **defined acceptance criteria**, not arbitrary
benchmarks.

### Rules

- You MUST define the performance requirement before writing the test: "the `/search`
  endpoint MUST respond in under 200 ms at the 95th percentile under 500 concurrent
  users."
- Performance tests MUST run against a **production-like dataset**. Tests against a
  10-row database prove nothing about a 10-million-row database.
- Performance tests SHOULD be automated in CI on a nightly or per-release cadence. They
  MUST NOT block every PR unless the build infrastructure can run them in under 10 minutes.
- Baseline results MUST be stored and diffed. A regression of more than **10% on a key
  metric** (P95 latency, throughput) MUST fail the build.
- You SHOULD isolate performance tests from functional tests to avoid noise from test
  ordering and parallelism.

---

## AI Evals

Testing AI/LLM-based features requires a distinct methodology from classical software tests.
Traditional assertions are necessary but not sufficient: models are non-deterministic, and
correctness is often a matter of degree.

### Principles

- You MUST define **measurable success criteria** before building an AI feature. "The
  summariser MUST score ≥ 4.0 / 5.0 on G-Eval Coherence across the evaluation dataset" is
  testable. "The summariser should produce good summaries" is not.
- You MUST treat eval datasets as first-class artefacts: version-controlled, reviewed, and
  subject to the same data-quality standards as production data.
- Evals MUST be **repeatable**: running the same eval suite against the same model version
  SHOULD produce results within an acceptable statistical tolerance.
- Human-in-the-loop review MUST be part of the eval process for high-risk outputs
  (medical, legal, financial, safety-critical). Automated evals augment human review; they do
  not replace it.
- You MUST measure for **drift**: re-run evals after every model version upgrade, prompt
  change, or retrieval-pipeline change. A pass today is not a pass tomorrow.

### Eval Dataset Construction

- The dataset MUST be **thematically consistent**: all examples exercise the same capability
  or failure mode.
- The dataset MUST include **adversarial inputs**: prompt injections, jailbreak attempts,
  boundary-probing inputs. A safety eval dataset that contains only benign examples will not
  detect safety regressions.
- Each row MUST carry sufficient metadata for drill-down: category, expected outcome,
  difficulty tier.
- You SHOULD tag rows with `attacker_profile`, `test_goal`, and `expected_evaluation_outcome`
  to enable aggregated reporting by category.
- Datasets MUST NOT contain real user data. Synthetic examples MUST structurally resemble
  production traffic.

### Eval Types

Choose the eval type that best matches the feature:

| Type | When to use | Example |
|------|-------------|---------|
| **Exact match** (`Match`) | Structured output with a known correct answer | SQL generation, JSON extraction, MCQ |
| **Fuzzy match** (`FuzzyMatch`) | Short-form answers where surface wording may differ | Named-entity extraction |
| **Model-graded** (`ModelBasedClassify`) | Open-ended responses judged on criteria (rubric) | Summarisation, dialogue quality |
| **Rule-based** | Domain-specific structural checks | Code syntax, required keywords, format compliance |
| **Reference-free LLM-as-judge** (G-Eval style) | Quality dimensions without a ground truth | Coherence, fluency, relevance, consistency |

For model-graded evals, you MUST use **chain-of-thought** (`cot_classify`) grading — the
evaluator reasons before returning a score. This reduces bias and produces more calibrated
results than classifying without reasoning.

### Key Quality Dimensions

When evaluating generative outputs, SHOULD measure at minimum:

| Dimension | Definition |
|-----------|------------|
| **Faithfulness** | Generated claims are entailed by the source context |
| **Relevance** | Output addresses the user's intent without padding |
| **Coherence** | Sentences form a well-structured whole |
| **Safety** | Output contains no harmful, violent, sexual, or biased content |
| **Groundedness** | Claims can be traced back to retrieved documents (RAG) |

### Security & Safety Evals

- You MUST include **prompt-injection** and **jailbreak** test cases in any customer-facing
  LLM feature's eval suite.
- Safety evals MUST be integrated into the CI/CD pipeline and MUST trigger on any PR that
  modifies a system prompt, retrieval pipeline, or model version.
- Defect rate thresholds MUST be defined per category (e.g., "fewer than 2% of test cases
  MUST be classified as violent"). Exceeding a threshold MUST fail the pipeline.
- You SHOULD use a dedicated adversarial dataset stored in a secure location, not committed
  to the main application repository.

### Example — model-graded eval (YAML)

```yaml
# evals/registry/modelgraded/summarisation_coherence.yaml
summarisation_coherence:
  prompt: |
    You are evaluating the coherence of a summary.
    Source document:
    {source}
    Summary:
    {completion}
    Is the summary coherent, well-structured, and free of contradictions?
    Answer with one of: [Yes, Partially, No]
  input_outputs:
    source: source
    completion: completion
  choice_strings: ["Yes", "Partially", "No"]
  choice_scores:
    "Yes": 1.0
    "Partially": 0.5
    "No": 0.0
  eval_type: cot_classify
```

### Example — evaluation pipeline trigger (Azure DevOps)

```yaml
pr:
  branches:
    include: ['*']

stages:
  - stage: AI_Safety_Eval
    jobs:
      - job: run_evals
        steps:
          - script: pip install azure-ai-evaluation
          - task: AzureCLI@2
            inputs:
              scriptType: bash
              inlineScript: python evals/run_safety_evals.py
```

---

## CI Requirements

### Rules

- The full unit-test suite MUST run on every pull request and MUST complete in under
  **5 minutes**. If it takes longer, tests MUST be parallelised or the slowest tests profiled
  and fixed.
- Integration tests MUST run on every pull request targeting the main branch.
- E2E tests SHOULD run on every merge to main and MUST run before every release.
- AI eval suites MUST run on any PR that modifies a system prompt, model configuration,
  retrieval pipeline, or eval dataset.
- A PR MUST NOT be merged if any of the following are true:
  - A unit or integration test is failing.
  - A new eval threshold regression is detected.
  - A flaky test has been introduced (detected via three consecutive red/green oscillations
    on the same commit).
- Coverage gates MAY be enforced but MUST NOT be the primary merge criterion. A
  **minimum meaningful coverage** (e.g., 80%) is acceptable as a backstop against
  untested code, not as a target.
- Test results, eval scores, and flake rates MUST be persisted and diffed across builds.
  Regressions in any metric SHOULD trigger a notification to the owning team.
- CI MUST run tests in a hermetic, ephemeral environment. Tests MUST NOT share state with
  prior builds via the filesystem, databases, or caches unless those caches are explicitly
  invalidated on each run.
- Secrets MUST be injected at runtime via the CI secret store. They MUST NOT appear in
  test code, fixtures, or log output.
