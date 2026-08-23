# AI-Assisted Development Workflow

This is the master index. It covers the **shared phases** every project goes through, then routes you into a **track-specific workflow** for your area of development.

```
                          ┌─────────────────────────────┐
   Phase 0  ──────────►   │  Universal Principles        │  (always loaded)
                          └─────────────────────────────┘
                                       │
   Phase 1  ──────────►   Planning      (discuss → spec.md)
                                       │
   Phase 2  ──────────►   Architecture  (plan → todo.md → AGENTS.md → ADRs)
                                       │
   Phase 3  ──────────►   PICK YOUR TRACK
                          │
          ┌───────────────┼────────────────┬────────────────┐
          ▼               ▼                ▼                ▼
   workflows/        workflows/       workflows/       workflows/
   frontend.md       backend.md       ml.md            devops.md
          │               │                │                │
          └───────────────┴────────────────┴────────────────┘
                                       │
   Phase 4  ──────────►   Release & Operate  (see workflows/devops.md)
```

Each track file is **self-contained**: it has its own setup, design step, build loop, prompts, and quality gates tailored to that area. You only open the one you need.

---

## How to use this repo

- **`rules/`** — Normative engineering standards (MUST/SHOULD/MAY) per area. These are the *quality bar*. Attach the relevant ones as context for every prompt.
- **`sources/`** — Upstream references the rules are distilled from (Google, Stripe, OWASP, etc.). Consult when you need the deeper "why."
- **`workflows/`** — The step-by-step playbooks (this folder). These are the *process*.
- **`Workflow.md`** (this file) — Shared phases + routing.

**Model note:** Default to the most capable Claude model for planning, architecture, and security review (e.g. `claude-opus-4-8`); a faster model (e.g. `claude-sonnet-4-6`) is fine for mechanical build-loop steps once the design is locked.

---

# Phase 0: Universal Principles

These apply to **every** track. Distilled from `rules/agentic.md` and `rules/general.md`. Paste this block (or reference these files) at the start of any session.

```
- The repo is the contract. AGENTS.md / CLAUDE.md and the rules/ files outrank any
  verbal instruction in a session prompt.
- Constraints beat instructions. A failing CI gate catches more than a thousand lines
  of prose. Encode fixes as lint rules, tests, or CI gates — not longer prompts.
- Plan before code. Separate planning from execution. Produce a plan for anything
  larger than a single-function change.
- Adversarial by default. Flag design flaws, ambiguous requirements, and risky
  assumptions BEFORE implementing. Do not be purely agreeable.
- Small, reviewable units. One logical concern per change. Complex logic stays under
  ~500 changed lines; mechanical changes under ~800.
- Every change leaves code health equal or better. Delete dead code. No "just in case."
- AI-generated code is held to the same bar as human code. Do not submit code you
  cannot explain; do not approve code you do not understand.
- Verify before commit, in order: format → lint → type-check → unit tests → integration tests.
  Fix root causes; never bypass a check.
- Off-limits without explicit confirmation: force-push, history rewrites, CI/CD config
  changes, migration-file edits, committing secrets, skipping hooks (--no-verify).
```

---

# Phase 1: Planning

**Goal:** turn a raw idea into a developer-ready `spec.md`. Track-agnostic.

## Prompt 1.1 — Discuss with the LLM

```
You are a senior Product Strategist, UX Researcher, and Technical Analyst.
Your goal is to help me develop a complete, detailed, developer-ready specification
for a new app idea.

Working rules:
1. Ask me strictly ONE question at a time. Never ask multiple questions in one turn.
2. Each question must build directly on my previous answer.
3. Follow a structured path of exploration:
   - Problem & pain points
   - Target users & segments
   - Core use cases
   - Key features & functional scope
   - User journey & UX flows
   - Technical considerations (architecture, integrations, constraints)
   - Data model & edge cases
   - Monetization strategy
   - Risks, limitations, dependencies
   - Final consolidated specification
4. Do NOT propose features or assumptions unless you have asked about them first.
5. Do NOT skip ahead in the structure — proceed logically, guided by my answers.
6. When exploration is complete, produce a full formal specification document.

Start by asking the first question:
"What is the core idea of your app in one or two sentences?"
```

→ *Answer the questions and refine the product until the model has enough to write the spec.*

## Prompt 1.2 — Compile spec.md

```
Now that we've wrapped up the brainstorming process, compile our findings into a
comprehensive, developer-ready specification. Include all relevant requirements,
architecture choices, data handling details, error-handling strategies, and a testing
plan so a developer can immediately begin implementation.

Output as spec.md.
```

---

# Phase 2: Architecture & Task Breakdown

**Goal:** turn `spec.md` into a sequenced plan, a `todo.md` checklist, the `AGENTS.md` that governs all future sessions, and ADRs for the big decisions. Track-agnostic.

## Prompt 2.1 — Generate the plan + prompt pack

```
You are an expert software architect and prompt engineer.
Take a project description and produce a structured plan PLUS a pack of implementation
prompts for a code-generation LLM. Output everything in MARKDOWN.

=== INPUT ===
- Project description: {{project_description}}
- (Optional) Constraints or preferences: {{constraints_and_preferences}}

------------------------------------------------------------
PHASE 1 — PROJECT BLUEPRINT
------------------------------------------------------------
Produce a high-level blueprint as an ordered list of milestones. For each milestone:
- Name
- Short goal (1–2 sentences)
- Main components or modules involved
- Expected artifacts (API endpoints, components, schema, tests, etc.)
Keep it coherent, incremental, and free of implementation-level detail.

Output as:
## 1. Project Blueprint
- Milestone 1: ...

------------------------------------------------------------
PHASE 2 — REFINED IMPLEMENTATION STEPS
------------------------------------------------------------
Refine the blueprint into small steps, each safe to implement in a single short session
or PR. No "do nothing" steps; no large jumps in complexity. At most two refinement passes
(Pass 1: 2–7 steps per milestone; Pass 2: break down anything still too big).

For each step:
- Step ID (S1, S2, ... in execution order)
- Parent milestone
- Objective (1–2 sentences)
- Main changes (behavior/code, not exact syntax)
- Dependencies on previous steps
- TRACK: which development track this belongs to (frontend / backend / ml / devops)

Then verify coverage, smooth complexity ramp, and no overlaps.

Output as:
## 2. Refined Implementation Steps
- S1 (Milestone X) [backend]: Objective, main changes, dependencies

------------------------------------------------------------
PHASE 3 — CODE-GENERATION PROMPT PACK
------------------------------------------------------------
Create one prompt per refined step. Each prompt must be incremental (extend the current
state, never rewrite), produce no orphaned code, and end by wiring things together with
minimal tests.

Format each as:
### Step {{step_id}} — {{step_title}}  [track]
```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Recap of what previous steps produced.
- Relevant design decisions or constraints.

Task:
- The coding task for this step.

Requirements:
- Which files/modules to touch and how to connect them.
- Tests, error handling, and code-style expectations.
- Extend and integrate; do not rewrite working code.

Output:
- The updated or new code.
- A short note summarizing what changed.

If something is ambiguous, ask clarifying questions before producing code.
```

Tag every step with its TRACK so I can route it to the right workflow file.

Here is the spec:
[PASTE spec.md CONTENTS HERE]
```

## Prompt 2.2 — Create AGENTS.md (run once, governs all sessions)

```
You are setting up the agent configuration for a new project.
Based on the spec and plan, generate an AGENTS.md file for the repo root.

It MUST include:

# Commands
- Run tests / single test / lint / type check / format / dev server  (fill each in)

# Repo structure
<directory layout derived from the plan>

# Conventions
<naming, error-handling, and API conventions from the spec>

# Off-limits
- Migration files, CI/CD config: no changes without explicit instruction
- Never commit secrets/tokens/credentials
- Never skip pre-commit hooks (--no-verify)
- Never delete or skip existing tests to make CI pass

# Personas
## Implementation
Implement the spec. Fail fast. Run tests after every change. Surface blockers immediately.
## Adversarial reviewer
Find every problem: security holes, missing tests, incorrect assumptions, architectural
violations. List as a numbered checklist. Do not be encouraging.

Here is the spec:    [PASTE spec.md]
Here is the plan:    [PASTE plan.md]
```

## Prompt 2.3 — Architecture Decision Record (per significant decision)

```
You are a software architect. Generate an ADR using the Nygard+MADR structure from
rules/documentation.md §3. File path: docs/adr/NNNN-<imperative-phrase>.md

Sections: Status | Date | Deciders | Context and Problem Statement | Decision Drivers |
Considered Options | Decision Outcome (chosen + why) | Positive Consequences |
Negative Consequences/Trade-offs | Pros and Cons of each Option | Links

Rules:
- Be concrete; reference the spec and constraints directly.
- No "industry best practices" hand-waving — give specific reasons.
- Alternatives must explain why they LOST, not just be listed.
- ADRs are immutable once accepted; supersede, never edit.

Decision to document: [DESCRIBE THE DECISION AND CONTEXT]
Here is the spec: [PASTE spec.md]
```

## Prompt 2.4 — Create todo.md (source of truth)

```
Create a thorough todo.md I can use as a checklist, grouped by TRACK (frontend / backend /
ml / devops) and then by milestone. Each item is a checkbox with its Step ID. Include a
"Cross-cutting gates" section for security review, testing, and docs.

Attach: plan.md, spec.md, and the relevant rules/ files.
```

---

# Phase 3: Pick Your Track

Once `spec.md`, `plan.md`, `AGENTS.md`, and `todo.md` exist, route each tagged step to its workflow:

| Track | Workflow file | Use when the step involves… | Primary rules |
|-------|---------------|------------------------------|---------------|
| 🎨 **Frontend** | [workflows/frontend.md](workflows/frontend.md) | UI components, state, forms, styling, a11y, client perf | `frontend.md`, `security.md`, `testing.md` |
| ⚙️ **Backend** | [workflows/backend.md](workflows/backend.md) | APIs, services, business logic, database, migrations | `backend.md`, `api.md`, `database.md`, `security.md`, `testing.md` |
| 🤖 **ML / AI** | [workflows/ml.md](workflows/ml.md) | LLM features, RAG, evals, data pipelines, model rollout | `ml.md`, `testing.md`, `security.md` |
| 🚀 **DevOps / Release** | [workflows/devops.md](workflows/devops.md) | CI/CD, IaC, environments, observability, deploy, incidents | `devops.md`, `security.md` |

A typical feature touches multiple tracks. Do them in dependency order (usually: backend contract → backend → frontend; ml runs parallel; devops wraps it for release). Each track file tells you its prerequisites.

---

# Phase 4: Release & Operate

Shipping is its own track. After the feature tracks are green, follow [workflows/devops.md](workflows/devops.md) for CI/CD setup, progressive rollout, observability, and rollback.

---

# Cross-Cutting Gates

These run *inside* each track but share a common spine. Each track file contains an area-tailored version; the generic forms live here.

## Code Review (use before merging any non-trivial chunk)

```
You are a code reviewer applying the adversarial reviewer persona. Find problems — do not
approve. Be specific. For each finding output: Type (Bug/Security/Quality/Missing test) |
Severity (Critical/High/Medium/Low/Nit) | Location (file:line) | Issue | Fix.

Review against:
- Correctness: logic solves the stated problem; edge cases, concurrency, error paths handled
  (no swallowed errors).
- Security (rules/security.md): input validation at boundaries; parameterized queries; no
  secrets in code/logs; authz checked per request.
- Quality (rules/general.md): lowest complexity that works; no abstraction for <3 use cases;
  no commented-out code; no untracked TODO/FIXME; no magic numbers.
- Tests (rules/testing.md): every logic change has a test; tests can actually fail; behavior
  not implementation; regression test for any bug fix.

Code to review: [PASTE DIFF]
```

## Debug / Fix (use for any failing test or bug, in any track)

```
You are diagnosing and fixing a bug. Be methodical — do not guess.
1. Read the exact error and full stack trace.
2. Identify the minimal reproduction.
3. State your root-cause hypothesis BEFORE writing code.
4. Verify the hypothesis (read the code, check the data).
5. Write the smallest fix that addresses the root cause.
6. Add/Update a test that would have caught this (required).
7. Check for security/perf/correctness regressions introduced by the fix.

Do NOT: swallow errors to pass; add checks for unreachable states; refactor while fixing;
bump timeouts to "fix" flaky async tests.

Error/output: [PASTE EXACT ERROR + STACK TRACE]
Relevant code: [PASTE FILE CONTENTS]
```

---

## Directory map

```
md/
├── Workflow.md          ← you are here (shared phases + routing)
├── workflows/
│   ├── frontend.md      ← 🎨 UI track
│   ├── backend.md       ← ⚙️ API/services/data track
│   ├── ml.md            ← 🤖 ML/AI track
│   └── devops.md        ← 🚀 release/operate track
├── rules/               ← normative standards (the quality bar)
└── sources/             ← upstream references (the "why")
```
