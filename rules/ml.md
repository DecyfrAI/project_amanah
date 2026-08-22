# ML Engineering Standards

Production standards for machine learning systems, drawing from OpenAI Evals, the Microsoft Engineering Playbook, and the ThoughtWorks Technology Radar (Vol. 34, April 2026).

---

## Data Quality

**Data is the foundation of every ML system. Garbage in, garbage out — no eval framework rescues a poisoned dataset.**

- Teams MUST validate data at ingestion boundaries: schema, type, range, and referential integrity checks before any downstream use.
- Teams MUST sanitize training data to prevent PII leakage. Use tools such as Microsoft Presidio or equivalent for automated redaction before data enters any pipeline.
- Teams MUST scan data sources for malware and adversarial content. Data poisoning can occur at pre-training, fine-tuning, and embedding stages.
- Teams SHOULD apply the rule of least privilege to training data: do not train on information accessible only to high-privilege users if the model will serve lower-privilege consumers.
- Teams SHOULD perform exploratory data analysis (EDA) before any training run. Understanding distributions, class imbalances, and outliers before training prevents wasted compute.
- Teams SHOULD maintain a data lineage record (ML-BOM) using tools such as OWASP CycloneDX to track data origin and transformations.
- Teams MAY use `openai tools fine_tunes.prepare_data` or equivalent converters to normalize raw data into JSONL format for LLM-based pipelines.

**Example — JSONL record for an eval dataset:**
```jsonl
{"input": [{"role": "user", "content": "What is the return policy?"}], "ideal": "Items may be returned within 30 days with receipt."}
{"input": [{"role": "user", "content": "Can I exchange without a receipt?"}], "ideal": "Exchanges without receipt are subject to manager approval."}
```

---

## Feature Engineering

- Teams MUST treat the context window as a design surface, not a text box. Context engineering is the practice of intentionally constructing the AI's information environment — it is now a foundational architectural concern.
- Teams MUST avoid front-loading every instruction into a static context. Progressive context disclosure — starting with a lightweight index and loading detailed instructions only when relevant — prevents context rot and degraded reasoning.
- Teams SHOULD centralize metric definitions, joins, access rules, and business terminology in a semantic layer (e.g., dbt MetricFlow, Cube, Snowflake Semantic Views) before features reach any model. Without a semantic layer, business logic scatters across ad-hoc tables, and metric definitions quietly diverge.
- Teams SHOULD use embeddings with cosine similarity for semantic feature retrieval, and monitor embedding distance distributions in production as a proxy for retrieval health.
- Teams SHOULD prefer RAG over fine-tuning for domain adaptation when the knowledge base changes frequently. RAG reduces retraining cost and narrows hallucination surface by grounding responses at inference time.
- Teams MAY use TOON (Token-Oriented Object Notation) as a last-mile optimization for structured input to LLMs, particularly for large, regular datasets where repeated JSON keys waste tokens. Benchmark against raw JSON/CSV before adopting.

**Context engineering checklist:**
```
[ ] Static instructions cached via prompt caching (front-loaded, not repeated per request)
[ ] Dynamic context loaded via retrieval — not pre-injected wholesale
[ ] Context window utilization monitored per request (token counts logged)
[ ] Signal-to-noise ratio validated by spot-checking reasoning traces
```

---

## Experiment Tracking

- Teams MUST log every experiment with: model version, prompt template, dataset version, hyperparameters, and eval scores. Without this, comparisons across runs are meaningless.
- Teams MUST use structured, queryable experiment stores — not ad-hoc spreadsheets. Tools such as Langfuse (self-hostable, OpenTelemetry-native) or equivalent platforms SHOULD be used for tracing, prompt management, and evaluation datasets.
- Teams SHOULD track both inner-loop metrics (accuracy, latency, cost) and outer-loop metrics (DORA: deployment frequency, change failure rate, MTTR, rework rate). Faster model generation that does not improve deployment frequency or stability is not an improvement.
- Teams SHOULD implement a feedback flywheel: after each experiment cycle, explicitly capture what worked and what failed, and update curated shared instructions accordingly. This is analogous to code refactoring — incremental improvement compounds.
- Teams SHOULD tag every experiment run with: model ID, prompt template hash, dataset version, sampling parameters (temperature, top-p, max tokens), and finish reason.
- Teams MAY use W&B, MLflow, or equivalent to link experiment artifacts to downstream eval results for full traceability.

**Minimum experiment record:**
```yaml
experiment_id: exp-2026-06-12-001
model: claude-sonnet-4-6
prompt_template: v3.2
dataset: customer-support-qa.v4
temperature: 0.2
eval_scores:
  accuracy: 0.87
  faithfulness: 0.91
  latency_p95_ms: 820
notes: "Reduced hallucination rate vs v3.1 by 4pp on consistency dimension"
```

---

## Evaluation

Evaluation is a first-class engineering concern. Without evals, it is difficult to understand how model or prompt changes affect production behavior.

- Teams MUST define evals before deploying any model to production. Evals MUST cover the primary use case, failure modes, and safety constraints.
- Teams MUST version evals alongside code. The naming convention MUST follow `<eval_name>.<split>.<version>` (e.g., `customer-support.test.v2`). Bumping the version is required when eval logic or data changes, so that historical results remain comparable.
- Teams MUST run evals in CI on every model or prompt change. Failing evals block deployment.
- Teams SHOULD layer eval types by signal strength:
  1. **Exact match / fuzzy match** — for constrained outputs (multiple choice, structured fields)
  2. **Model-graded (LLM-as-judge)** — for open-ended outputs; use chain-of-thought grading (`cot_classify` eval type) for highest accuracy
  3. **Human review** — for high-stakes decisions, ambiguous failures, and meta-eval calibration
- Teams SHOULD use G-Eval or equivalent for abstractive summarization, scoring on coherence, consistency, fluency, and relevance using probability-weighted token scoring across N=20 samples.
- Teams SHOULD implement meta-evals: human-labeled "choice" ground truth that validates the accuracy of the LLM judge itself. A well-calibrated judge achieves `metascore/ ≥ 0.9`.
- Teams SHOULD evaluate RAG pipelines on all four RAGAS dimensions: faithfulness, answer relevancy, context relevancy, and context recall.
- Teams MAY use DeepEval (Trial, ThoughtWorks Radar) for hallucination detection, answer relevance scoring, tool correctness, and multi-turn agentic evaluation.

**Example model-graded eval YAML (OpenAI Evals format):**
```yaml
customer-support-quality:
  id: customer-support-quality.test.v1
  description: Evaluates response relevance, factual grounding, and conciseness
  metrics: [accuracy]

customer-support-quality.test.v1:
  class: evals.elsuite.modelgraded.classify:ModelBasedClassify
  args:
    samples_jsonl: customer-support/samples.jsonl
    eval_type: cot_classify
```

---

## Metrics

- Teams MUST track operational metrics per deployment: request rate (RPS), error rate, latency percentiles (P50, P95, P99), and cost per transaction (tokens consumed).
- Teams MUST correlate client-observed latency spikes against dependency-level metrics (model inference, retrieval, embedding) to accelerate incident triage.
- Teams SHOULD select eval metrics matched to the task:

| Task | Primary Metric | Secondary |
|---|---|---|
| Classification | Accuracy, F1 | Calibration |
| Summarization | G-Eval (coherence, consistency, relevance, fluency) | ROUGE-L |
| RAG QA | Faithfulness, Answer Relevancy | Context Recall |
| Code generation | Functional correctness (pass@k) | Syntax correctness |
| Translation | BLEU | BERTScore |
| Open-ended generation | LLM-as-judge score | Semantic entropy |

- Teams SHOULD prefer LLM-based evaluators over n-gram metrics (BLEU, ROUGE) for tasks involving semantic quality. G-Eval with updated prompts achieves Spearman ρ ≈ 0.52 vs. human judgments compared to ROUGE-L at ρ ≈ 0.17.
- Teams SHOULD track semantic entropy as a confabulation signal: high entropy across repeated samples for a given prompt indicates unreliable outputs that warrant human review.
- Teams MUST NOT use coding throughput (lines generated, PRs merged) as a proxy for ML system quality. First-pass acceptance rate — how often model output is used with minimal rework — is a more meaningful leading indicator.

---

## Dataset Versioning

- Teams MUST version every dataset used in training, fine-tuning, and evaluation. Version identifiers MUST be immutable and addressable (e.g., content hash or tagged release).
- Teams MUST track the data split in the version label: `val`, `test`, `dev`, `prod`. Running the same eval name and version against the same model MUST produce reproducible results.
- Teams SHOULD use Apache Iceberg or equivalent open table formats for large-scale analytical datasets. Iceberg provides snapshot-based design with serializable isolation, safe concurrent writes, and time-travel for rollback — enabling audit of what data a model was trained on at any point.
- Teams SHOULD store eval datasets as JSONL files in a versioned registry (e.g., `evals/registry/data/<eval_name>/<split>.v<N>.jsonl`). Cloud paths are acceptable for private use but MUST NOT be referenced in shared eval definitions.
- Teams SHOULD treat training, validation, and test splits as immutable after creation. Any augmentation or cleaning produces a new versioned dataset.
- Teams MAY use Declarative Automation Bundles (formerly Databricks Asset Bundles) to manage ML datasets, pipelines, and models as versioned infrastructure code, enabling `bundle plan` previews before deployment.

---

## Reproducibility

- Teams MUST seed all random operations (data shuffling, train/val splits, model init) and log seeds with experiment metadata.
- Teams MUST pin model versions explicitly. Deploying against a floating alias (e.g., `gpt-4-latest`) without version pinning breaks reproducibility when the upstream model changes.
- Teams MUST record the full dependency graph: model version, framework versions, dataset version, prompt template hash, and hardware/compute configuration.
- Teams SHOULD use Dev Containers or equivalent to define reproducible, containerized training and evaluation environments. Declarative environment configuration eliminates "works on my machine" failures and reduces supply chain risk.
- Teams SHOULD store prompt templates in version control alongside eval definitions. A prompt template hash MUST be part of any experiment record.
- Teams MAY store prompts with semantic versioning (e.g., `customer-support-system.v3.2.md`) and link template version to all downstream evals and experiments.

---

## Model Registry

- Teams MUST register every model artifact before deployment with: model ID, version, training dataset version, eval scores at registration time, and approval status.
- Teams MUST support rollback. The registry MUST retain prior versions and enable redeployment within one business day.
- Teams MUST implement approval gates: new model versions MUST pass automated evals and receive explicit sign-off before promotion to the production slot.
- Teams SHOULD implement model version management at the gateway layer, so consumer applications are decoupled from model version changes. The gateway handles routing, version pinning, and controlled rollout to subsets of consumers.
- Teams SHOULD tag each registered model with: base model, fine-tuning dataset, eval suite version, use case, and risk classification.
- Teams MAY use platforms such as Azure ML, MLflow Model Registry, or Neutree (Assess, ThoughtWorks Radar) for model lifecycle management, access control, and usage accounting across heterogeneous hardware.

**Model card minimum fields:**
```yaml
model_id: customer-support-finetuned-v4
base_model: claude-sonnet-4-6
training_dataset: customer-support-pairs.v12
eval_suite: customer-support-quality.test.v1
eval_scores:
  accuracy: 0.89
  faithfulness: 0.93
  p95_latency_ms: 740
approved_by: ml-platform-team
approved_at: 2026-06-10
risk_classification: medium
use_case: customer-facing chat
```

---

## Rollouts

- Teams MUST execute a comprehensive eval suite before any broader rollout. Evals MUST cover performance, reliability, safety, and compatibility with the existing system.
- Teams MUST use progressive rollouts with explicit traffic thresholds. A new model version MUST NOT serve 100% traffic on day one.
- Teams MUST define rollback criteria in advance. If error rate increases by more than X% or eval score drops below Y within the first Z hours, automatic rollback MUST trigger.
- Teams SHOULD gate promotion between environments (dev → staging → production) on passing eval scores AND DORA stability metrics. A model that improves accuracy but increases change failure rate MUST NOT advance.
- Teams SHOULD use A/B testing (shadow scoring or traffic splitting) to compare candidate vs. baseline before full promotion. Compare on production traffic, not just held-out test sets.
- Teams SHOULD implement priority-based spillover for high-concurrency deployments: route high-priority requests to primary model endpoints; queue or degrade low-priority requests when capacity is constrained rather than applying uniform throttling.
- Teams MAY implement circuit-breaker patterns at the model gateway layer: when the backend returns 429s or error bursts, non-prioritized consumers receive extended backoff while prioritized consumers resume quickly.

**Rollout thresholds (example):**
```
Phase 1 (canary):     1% traffic, 24h observation
Phase 2 (limited):   10% traffic, 48h observation
Phase 3 (majority):  50% traffic, 72h observation
Phase 4 (full):     100% traffic
Rollback trigger:    p95 latency +20% OR error rate +2pp OR eval score -5pp
```

---

## Monitoring

- Teams MUST instrument all production ML systems with the three telemetry pillars: logs (events), traces (request lifecycle), and metrics (quantitative measures).
- Teams MUST log: input prompts (anonymized), model responses, request parameters (model, temperature, max tokens, finish reason), and correlation IDs. If prompts or responses exceed log size limits, store in a separate data store and log a reference ID.
- Teams MUST track model-specific metrics alongside operational metrics: accuracy drift, response quality scores (automated), user satisfaction signals (session length, abandonment rate), and cost per request (tokens consumed).
- Teams SHOULD use structured tags on all telemetry for correlation: model version, prompt template, deployment environment, interaction type, and agent/tool identifier for multi-agent systems.
- Teams SHOULD implement distributed tracing with spans for: API call, service processing, model inference, and data fetching (RAG retrieval). Inference spans SHOULD capture token counts and eval scores where available.
- Teams SHOULD emit custom events to a real-time messaging system (Kafka, EventHub, or equivalent) for near-real-time dashboarding and alerting that does not depend on Azure Monitor's 30s–15m ingestion latency.
- Teams MAY use SigNoz (Trial, ThoughtWorks Radar) as a self-hosted, OpenTelemetry-native observability platform for unified logs, metrics, and traces without vendor lock-in.

**Key monitoring metrics:**
```
Operational: RPS, error_rate, p50/p95/p99_latency_ms, tokens_per_request (prompt + completion)
Quality:     eval_score (rolling), faithfulness, answer_relevancy, user_abandonment_rate
Cost:        cost_per_request, daily_token_spend, cost_per_quality_point
Capacity:    PTU_utilization_pct, queue_depth, throttle_rate
```

---

## Drift Detection

- Teams MUST monitor for data drift and model performance drift continuously in production. Models decay as the real-world distribution shifts away from training data.
- Teams MUST set alert thresholds on automated eval scores. When rolling eval scores drop below a defined threshold (e.g., faithfulness < 0.85 over a 24h window), an incident MUST be opened.
- Teams SHOULD track embedding distance distributions over time. A sustained shift in the distribution of retrieval distances signals input distribution drift before it manifests in downstream quality metrics.
- Teams SHOULD monitor context switching frequency in conversational systems as a proxy for coherence degradation: high rates of mid-session context switches indicate the model is failing to maintain topic consistency.
- Teams SHOULD use semantic entropy as an early-warning signal for confabulation drift. If entropy for a tracked prompt set increases over time, the model is becoming less confident and more likely to hallucinate.
- Teams SHOULD run reference eval suites on a scheduled basis against production model endpoints (not just at deployment time). Model provider updates to underlying weights can silently degrade task-specific performance.
- Teams MAY implement architecture drift reduction using deterministic analysis tools (ArchUnit, Spectral) combined with LLM-powered evaluation to detect both structural and semantic violations as the model's behavior drifts from intended architectural zones.

**Drift detection checklist:**
```
[ ] Automated eval suite runs daily in production (not only at deploy time)
[ ] Input distribution monitored via embedding distance histograms
[ ] Rolling quality score dashboarded with alert threshold
[ ] Semantic entropy tracked on canary prompt set
[ ] Model provider changelog reviewed on every upstream version bump
```

---

## Human Review

- Teams MUST route a defined sample of production outputs to human reviewers. Automated evals are necessary but not sufficient; human review catches subtle failure modes that LLM judges miss due to positional bias, verbosity bias, and self-enhancement bias.
- Teams MUST use human review for high-stakes decisions, safety-critical outputs, and any case where automated eval confidence is below threshold.
- Teams MUST include human-labeled ground truth ("choice labels") in model-graded eval datasets to calibrate the LLM judge. A meta-eval accuracy below 0.9 indicates the judge itself is unreliable and MUST be recalibrated.
- Teams SHOULD implement structured human review workflows that distinguish: (a) output quality review, (b) safety review, and (c) eval calibration review. Each has different sampling rates and reviewer expertise requirements.
- Teams SHOULD collect reviewer feedback in a structured format (rubric scores + free-text rationale) and feed high-signal failures back into the eval dataset. This closes the data flywheel.
- Teams SHOULD implement human-in-the-loop (HITL) gates for high-impact agentic actions. Any action that modifies production data, sends external communications, or involves financial transactions MUST require explicit human approval.
- Teams MAY use HITLC (Human In The Loop Calibration) to mitigate positional and verbosity bias in LLM evaluators: present the same completion in different positions across multiple review sessions and calibrate scores accordingly.

**Human review sampling policy (example):**
```
Random sample:          2% of all production requests
Flagged by eval score:  100% of requests where faithfulness < 0.7
Flagged by sentinel:    100% of requests matching safety-rule triggers
Post-incident review:   100% of requests in the 1h window around anomalies
Eval calibration:       100 labeled samples per quarter per eval dimension
```

---

## Summary of Normative Keywords

| Keyword | Meaning |
|---|---|
| MUST | Required in all production ML systems without exception |
| SHOULD | Strongly recommended; deviation requires documented justification |
| MAY | Optional; adopt when the use case justifies the trade-off |
