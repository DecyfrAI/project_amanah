# 🤖 ML / AI Workflow

Self-contained playbook for LLM-backed features, RAG pipelines, evals, data preparation, and model rollout. ML work is **eval-first**: you define how you'll measure success before you build, because outputs are non-deterministic and "looks good" is not a test.

**Rules in scope:** `rules/ml.md` (primary), `rules/testing.md` (AI Evals section), `rules/security.md`, `rules/agentic.md`, `rules/general.md`
**Upstream sources:** `sources/openai_evals`, `sources/ThoughtWorks_Technology_Radar.md`, `sources/dbt` (semantic layer)

> Prerequisite: complete the shared phases in [../Workflow.md](../Workflow.md). ML features usually consume a backend API for serving — coordinate with [backend.md](backend.md) for the endpoint, gateway, and logging plumbing.

> **Model IDs** (knowledge cutoff aware): default to the latest capable Claude — `claude-opus-4-8` for hard reasoning/judging, `claude-sonnet-4-6` for high-volume inference, `claude-haiku-4-5` for cheap/fast paths. Pin the exact ID; never a floating alias.

---

## Build order

```
M0 Setup ─► M1 Eval-first design ─► M2 Data pipeline ─► M3 Build loop (feature + evals)
                                                              │
                                                              ▼
                                          M4 Safety gate ─► M5 Rollout ─► M6 Monitor ─► DoD
```

---

## Step M0 — Setup (once per ML capability)

**Checklist**
- [ ] Experiment tracking wired (Langfuse/MLflow/W&B) — model ID, prompt hash, dataset version, params, scores
- [ ] Eval registry directory: `evals/registry/evals/` + `evals/registry/data/<eval>/`
- [ ] Prompt templates stored in version control with semantic versions (`<name>.v<N>.md`)
- [ ] Model gateway/abstraction so app code is decoupled from the model version
- [ ] Per-request logging: prompt (anonymized), response, model, temperature, finish_reason, token counts, trace_id
- [ ] Adversarial eval dataset stored **separately/securely**, not in the main app repo

### Prompt M0 — Scaffold the ML harness

```
You are setting up an ML/LLM feature harness. Follow rules/ml.md.

Produce:
1. An eval registry layout: evals/registry/evals/<name>.yaml and data/<name>/<split>.v1.jsonl.
2. A model gateway module that pins model versions, centralizes params (temperature, top_p,
   max_tokens), and is the single place app code calls (so versions can roll out independently).
3. Structured inference logging: prompt (anonymized), response, model ID, temperature,
   finish_reason, prompt/completion token counts, latency, trace_id. Oversized prompts/responses
   stored by reference ID.
4. An experiment-record template (yaml): experiment_id, model, prompt_template hash, dataset
   version, params, eval_scores, notes.

Capability from spec: [PASTE relevant spec section]
```

---

## Step M1 — Eval-First Design (before building the feature)

Define **measurable success criteria first**. This is the single most important ML discipline.

### Prompt M1 — Define success criteria + eval plan

```
You are an ML evaluation designer. Before we build the feature, define how we measure it.
Follow rules/ml.md and rules/testing.md (AI Evals).

Produce:
1. Measurable success criteria, e.g. "The summarizer MUST score ≥ 4.0/5.0 on G-Eval Coherence
   across the eval set." Reject vague goals like "good summaries."
2. The right eval type(s) per the task:
   - Exact/Fuzzy match → structured output, extraction, MCQ
   - Model-graded (cot_classify, chain-of-thought) → open-ended quality
   - Rule-based → format/keyword/syntax checks
   - G-Eval / reference-free → coherence, fluency, relevance without ground truth
   - RAGAS (faithfulness, answer relevancy, context relevancy, context recall) → RAG
3. Quality dimensions to score (faithfulness, relevance, coherence, safety, groundedness).
4. RAG vs fine-tuning recommendation (prefer RAG when the knowledge base changes often).
5. A meta-eval plan: human "choice" labels to validate the LLM judge (target metascore ≥ 0.9).

Feature: [PASTE feature section from spec.md]
```

---

## Step M2 — Data Pipeline

### Prompt M2 — Data validation + eval dataset

```
You are building the data pipeline + eval dataset. Follow rules/ml.md (Data Quality) and
rules/testing.md (Test Data).

Produce:
1. Ingestion validation: schema, type, range, and referential checks at the boundary.
2. PII handling: redaction (e.g. Presidio) BEFORE data enters any pipeline; least-privilege
   on training data.
3. An eval dataset as JSONL with, per row: input, ideal (or rubric), category, difficulty tier,
   and for safety rows: attacker_profile, test_goal, expected_evaluation_outcome.
   - Include happy-path, edge cases, AND adversarial inputs (prompt injection / jailbreak).
   - Synthetic data only — must NOT contain real user data.
4. Dataset versioning: <name>.<split>.v<N>; splits immutable after creation; content-hash or
   tagged release as the identifier.

Data sources / knowledge base: [DESCRIBE]
Eval criteria from M1: [PASTE M1 output]
```

---

## Step M3 — Build Loop (per `[ml]` step in todo.md)

```
1. Open todo.md → next [ml] step
2. Run Prompt M3 (feature + evals together — never ship a feature without its eval)
3. Run the eval suite locally; record the experiment (model, prompt hash, dataset ver, scores)
4. Iterate on prompt/retrieval; re-run evals; compare against the previous record
5. Run Prompt M-SEC (prompt-injection / safety) — mandatory for any customer-facing feature
6. Check off todo.md → commit (e.g. "Implement M-step 3 from todo.md: RAG answer endpoint")
```

### Prompt M3 — Implement an ML step + its evals

```
You are implementing an ML/LLM feature AND its evals together. Follow rules/ml.md.

Rules:
- Context engineering: cache static instructions via prompt caching; load dynamic context via
  retrieval (progressive disclosure) — do NOT front-load everything into a static prompt.
- Prefer RAG over fine-tuning when the knowledge base changes frequently; ground answers in
  retrieved docs to narrow hallucination surface.
- Pin the model version explicitly. Centralize params in the gateway.
- Log per request: anonymized prompt, response, model ID, temperature, finish_reason, token
  counts, trace_id.
- Evals run in CI on every model/prompt/retrieval change; failing evals block deploy.

Output:
1. The feature implementation (via the model gateway).
2. The eval YAML (use cot_classify for model-graded) + any new JSONL rows.
3. Metrics to instrument: eval_score, faithfulness, answer_relevancy, p95 latency,
   tokens_per_request, cost_per_request.
4. This feature's rollback criteria (see M5).

Current state: [BRIEF: existing gateway/prompts/evals]
Eval criteria (M1) + dataset (M2): [PASTE]
Task: [PASTE the [ml] step from todo.md]
Reference files: rules/ml.md, rules/testing.md, rules/security.md
```

---

## Step M4 — Safety Gate

### Prompt M-SEC — Prompt-injection & safety review

*Mandatory for any customer-facing LLM feature or any agent with tool access.*

```
You are an AI safety + security reviewer. Be adversarial. Per finding: Severity | Location | Issue | Fix.

Prompt injection & data trust (rules/agentic.md, rules/ml.md):
[ ] User/retrieved content treated as UNTRUSTED — instructions embedded in it are not executed
[ ] Toxic-flow mapping done: every path from untrusted input → model action is documented
[ ] Lethal-trifecta check: the system does NOT simultaneously have (1) access to private data,
    (2) exposure to untrusted content, and (3) ability to act externally/irreversibly. If it does,
    one leg MUST be broken (e.g. isolate retrieval from action).

Eval coverage (rules/testing.md):
[ ] Eval suite includes prompt-injection AND jailbreak cases
[ ] Per-category defect thresholds defined (e.g. <2% violent) and wired to fail CI
[ ] Safety evals trigger on any PR touching a system prompt, retrieval pipeline, or model version

Data & privacy (rules/ml.md, rules/security.md):
[ ] Training/eval data PII-redacted; no real user data in datasets
[ ] Prompts/responses anonymized in logs; oversized payloads stored by reference, access-controlled
[ ] HITL gate for high-impact agentic actions (writes to prod data, external comms, payments)

Changes to review: [PASTE DIFF + prompt templates]
Reference files: rules/ml.md, rules/agentic.md, rules/security.md
```

---

## Step M5 — Rollout

### Prompt M5 — Progressive rollout plan

```
You are planning the model/feature rollout. Follow rules/ml.md (Rollouts) + the model registry rules.

Produce:
1. A model-card entry: model_id, base_model, training/eval dataset versions, eval_scores at
   registration, risk_classification, approved_by.
2. Progressive rollout phases with observation windows:
   Phase 1 canary 1% (24h) → Phase 2 10% (48h) → Phase 3 50% (72h) → Phase 4 100%.
3. Explicit automatic rollback triggers, e.g.:
   p95 latency +20% OR error rate +2pp OR rolling eval score -5pp.
4. A/B or shadow-scoring plan to compare candidate vs baseline on PRODUCTION traffic.
5. Gateway routing: how version pinning + controlled rollout to consumer subsets works.
- Promotion gates on BOTH eval scores AND stability (a model that improves accuracy but raises
  change-failure-rate MUST NOT advance).

Feature + eval scores: [PASTE M3 results]
```

---

## Step M6 — Monitor & Detect Drift

### Prompt M6 — Production monitoring + drift detection

```
You are instrumenting production ML monitoring. Follow rules/ml.md (Monitoring, Drift, Human Review).

Produce:
1. Dashboards/metrics: RPS, error_rate, p50/p95/p99, tokens_per_request, cost_per_request,
   rolling eval_score, faithfulness, answer_relevancy, user_abandonment_rate.
2. Drift detection: daily eval suite against the PROD endpoint (not just at deploy); embedding-
   distance histograms for input drift; semantic entropy on a canary prompt set; alert when
   rolling faithfulness < 0.85 over 24h.
3. Human-review sampling policy: e.g. 2% random; 100% where faithfulness < 0.7; 100% of safety-
   rule triggers; quarterly judge-calibration set.
4. A trigger to re-run reference evals on every upstream model-provider version bump.

Feature in production: [DESCRIBE endpoints + eval suite]
Reference files: rules/ml.md
```

---

## Definition of Done (ML / AI)

- [ ] Measurable success criteria defined (M1) and met on the versioned eval set
- [ ] Feature ships WITH its eval; evals run in CI and gate deploy
- [ ] Model version pinned; params centralized in the gateway; inference fully logged
- [ ] Eval dataset versioned; includes adversarial rows; no real user data
- [ ] M-SEC passes: prompt-injection/jailbreak covered; lethal-trifecta check clear; HITL on risky actions
- [ ] Experiment recorded (model, prompt hash, dataset ver, scores) for reproducibility
- [ ] Progressive rollout + automatic rollback triggers defined; model-card registered
- [ ] Production monitoring + drift alerts live

→ Hand off to [devops.md](devops.md) for serving infra/CI, and [backend.md](backend.md) for the serving endpoint.
