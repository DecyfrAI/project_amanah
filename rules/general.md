# Engineering Rules

Repository-wide rules for humans and AI coding agents. Apply these across every language, framework, and team.

RFC terminology: **MUST** = mandatory, **SHOULD** = strongly preferred, **MAY** = permitted but not required.

---

## General Principles

1. Every change MUST leave overall code health equal to or better than it found it. Any change that demonstrably degrades code health MUST NOT be merged except in a documented emergency.

2. Every change MUST solve a problem that exists today, with requirements that are visible today. Do not build for speculative future needs.

3. Changes MUST be decomposed into small, independently reviewable units. A unit addresses one logical concern.

4. Code is a shared team asset. Contributors MUST NOT treat any file or module as personally owned. Phrases like "my code" or "your code" have no place in technical decisions.

5. When two approaches produce equivalent outcomes, contributors MUST prefer the one that is simpler, easier to delete, and easier to understand.

6. Contributors MUST NOT duplicate functionality that already exists in a standard library or an already-imported dependency.

7. Contributors SHOULD consult the person most familiar with an area before making significant structural changes to it.

8. These rules MAY be violated with explicit, documented justification at the point of deviation.

---

## Simplicity

9. Code MUST be written at the lowest level of complexity that correctly solves the stated problem. Cleverness that obscures intent is a defect.

10. Contributors MUST NOT add abstraction for fewer than three concrete, distinct use cases. Abstractions introduced for one or two cases MUST be removed.

    ```
    # Bad: abstraction for a single caller
    def build_request(builder: RequestBuilder) -> Request: ...

    # Good until a second format appears: just build the request inline
    request = Request(method="POST", url=url, body=payload)
    ```

11. Contributors MUST NOT add an optional "mode" or "type" parameter to a function to make it do two conceptually different things. Write two functions.

12. Functions and methods SHOULD be short enough that the entire body is visible without scrolling on a standard screen. If they are not, decompose them.

13. Contributors MUST NOT add conditional logic for code paths that will never be exercised. Handle only states the system can actually reach.

14. If a contributor cannot explain in one sentence what a function does, the function is too complex and MUST be refactored before submission.

15. Contributors MUST NOT keep code "just in case." Delete unused code. Version control preserves history.

16. Contributors MUST NOT introduce a design pattern where a direct implementation is shorter and equally clear.

---

## Code Quality

17. Readability MUST come before optimization. Make code correct and clear first; only then optimize when a measured bottleneck justifies it.

18. All non-trivial logic MUST be covered by automated tests. Coverage gaps MUST be documented with a reason.

19. Test code MUST be held to the same quality standards as production code. Duplication, obscure naming, and missing assertions are defects in tests.

20. Tests MUST be deterministic. A test that fails intermittently provides negative value and MUST be fixed or deleted.

21. Tests MUST NOT depend on execution order. Every test MUST be able to run in isolation.

22. A change that adds or modifies logic MUST include new or updated tests for that logic in the same commit or pull request.

23. A test MUST actually be capable of failing. Tests that always pass regardless of the code under test MUST be removed.

    ```
    # Bad: assertion can never fail
    assert result is not None

    # Good: assertion validates the actual value
    assert result == {"status": "ok", "count": 3}
    ```

24. Contributors MUST NOT leave commented-out code in the codebase without an inline explanation of why it is preserved.

25. Contributors MUST NOT leave `TODO` or `FIXME` markers that are not linked to a tracked ticket.

26. Input validation MUST happen at system boundaries: user-supplied data, external API responses, file contents, and environment variables. Internal invariants guaranteed by the code itself MUST NOT be defensively re-validated.

27. Contributors MUST NOT rely on undefined behavior or implementation-specific behavior that is not guaranteed by the language specification.

28. Global mutable state MUST be avoided. When it cannot be avoided, access to it MUST be documented and controlled through a single, well-known interface.

29. Magic numbers and magic strings MUST be replaced with named constants. The constant's name MUST explain the meaning, not just restate the value.

    ```
    # Bad
    if retries > 3:

    # Good
    MAX_DELIVERY_RETRIES = 3
    if retries > MAX_DELIVERY_RETRIES:
    ```

---

## Refactoring

30. Refactoring MUST be separated from behavior changes. A single pull request MUST NOT both restructure existing code and modify what the system does.

31. Contributors MUST NOT refactor code that lacks test coverage without first adding tests that document existing behavior.

32. Opportunistic "while I'm here" refactors that grow unbounded MUST be extracted into a separate, tracked change.

33. Renaming, file moves, and automated reformatting SHOULD be submitted as standalone changes that can be trivially reviewed in seconds.

34. Every refactor MUST leave the observable behavior of the system identical to before, verified by the existing test suite.

35. Contributors SHOULD leave a targeted, measurable improvement in any file they substantially touch — even if only removing dead code or clarifying a name.

36. Refactors that change module or package structure MUST be reviewed by someone with knowledge of all affected consumers.

---

## Reviews

37. A reviewer MUST approve a change once it makes the codebase net-better, even if the change is not perfect. Continuous improvement is the goal, not perfection.

38. A reviewer MUST NOT block a change based solely on personal style preferences that are not covered by a documented standard.

39. Non-mandatory review comments MUST be prefixed with `Nit:` to distinguish polish suggestions from blocking issues.

    ```
    # Nit: consider renaming `r` to `response` for clarity.
    ```

40. When rejecting an approach, the reviewer MUST suggest a concrete alternative. Rejection without an alternative is not actionable.

41. The author MUST respond to every review comment, even if the response is only "done" or "intentionally left as-is because…".

42. A change MUST NOT stall indefinitely because the author and reviewer cannot agree. When consensus fails, escalate to a third party or technical lead within 24 hours.

43. Reviewers MUST read every line of human-written logic assigned to them. Spot-checking is not sufficient for non-generated code.

44. Reviewers MUST explicitly check for correctness. A readable, well-styled bug is still a bug.

45. Reviewers SHOULD check edge cases, concurrency, and security boundaries, and escalate to a specialist reviewer when they are not qualified to assess these.

46. The pull request or changelist description MUST explain both **what** the change does and **why** it was made. Descriptions like "fix bug" or "update code" are not acceptable.

    ```
    # Bad description
    Fix bug in payment flow.

    # Good description
    Prevent double-charge when payment gateway times out.

    The gateway returns a 504 on slow responses but still processes the charge.
    We now check for an existing successful transaction before retrying, using
    the idempotency key stored on the order.
    ```

47. Changes MUST NOT be submitted if they break the build or fail CI. No exceptions outside declared emergencies.

48. Style reformatting MUST NOT be combined with functional changes in the same commit.

49. Changes that touch UI or user-visible behavior SHOULD include screenshots or screen recordings that show the before and after state.

50. A change SHOULD stay under 400 lines of substantive diff. Reviewers MAY reject changes that exceed a size where thorough review becomes impractical and request that they be split.

51. Reviewers SHOULD acknowledge good choices explicitly, not only note problems. Recognition reinforces effective patterns.

---

## Dependencies

52. Before adding a new dependency, contributors MUST verify its maintenance status, license compatibility, and known security vulnerabilities.

53. Contributors MUST NOT add a dependency to solve a problem that can be adequately solved in under roughly 30 lines of focused, well-tested code.

54. External dependencies in production code MUST be pinned to an explicit version. Floating version specifiers (`latest`, `*`, `^`) are only acceptable in development tooling.

55. Contributors MUST NOT depend on the internal, non-public API of an external package. Depend only on the documented public interface.

56. Contributors MUST remove dependencies that are no longer used. Unused dependencies are security surface area.

57. When a standard library module is adequate, contributors SHOULD prefer it over a third-party alternative.

58. Dependency version upgrades SHOULD be submitted as standalone changes to make regressions easy to identify and revert.

---

## Naming

59. Names MUST reveal intent. A reader MUST be able to understand what a symbol represents or does from its name alone, without reading its implementation or documentation.

60. Abbreviations MUST NOT be used except for domain-universal terms that every contributor in this codebase will recognize (e.g., `id`, `url`, `api`, `db`).

61. Type information MUST NOT be encoded in names. The type system, not the identifier, communicates type.

    ```
    # Bad
    user_list, email_string, is_bool_flag

    # Good
    users, email, is_active
    ```

62. A single concept MUST use a single term throughout the codebase. Do not alternate between `user` and `account`, or `fetch` and `get`, for the same operation.

63. Booleans MUST be named as verb phrases that answer a yes/no question: `is_active`, `has_permission`, `can_retry`, `was_found`.

64. Generic container nouns (`data`, `info`, `manager`, `handler`, `helper`, `util`, `misc`) MUST NOT appear in names without a qualifying noun that narrows the meaning.

    ```
    # Bad
    class DataManager:
    class UserHelper:

    # Good
    class SessionStore:
    class PasswordHasher:
    ```

65. Functions and methods MUST be named as verb phrases: `fetch_invoice`, `validate_address`, `render_summary`.

66. Acronyms in mixed-case identifiers MUST be treated as words: `XmlParser`, `HttpClient`, `DbConnection` — not `XMLParser`, `HTTPClient`, `DBConnection`.

67. A name MUST NOT be reused for a different concept in the same scope, including by shadowing an outer-scope variable.

68. Collection names MUST be plural nouns: `users`, `order_ids`, `active_sessions`.

---

## Error Handling

69. Exceptions MUST NOT be used for normal control flow. Exceptions represent unexpected, unrecoverable states, not expected branch conditions.

70. Every caught exception MUST be handled with intent: re-thrown, logged with context, converted to a domain error, or explicitly acknowledged as ignorable with an inline explanation.

71. Empty catch or except blocks are MUST NOT appear in the codebase.

    ```
    # Bad
    try:
        send_notification(user)
    except Exception:
        pass

    # Good
    try:
        send_notification(user)
    except NotificationServiceUnavailable as exc:
        logger.warning("Notification skipped; service unavailable", exc_info=exc)
    ```

72. Error messages MUST include enough context for an engineer to diagnose the failure without attaching a debugger. Minimally: what was attempted, what was found, and where.

73. User errors (invalid input) and program errors (unexpected state) MUST be distinguished and handled differently. User errors SHOULD produce a clear, actionable message. Program errors SHOULD fail loudly.

74. Errors MUST NOT be silently swallowed when a partial failure occurs. Callers MUST be informed of both what succeeded and what failed.

75. Errors SHOULD be logged at the architectural boundary where they cross between layers, not at every internal call site that propagates them.

76. Where the language supports typed errors or result types, contributors SHOULD use them to force callers to handle failure paths at compile time rather than at runtime.

77. Functions that can fail MUST communicate failure through their return type or exception contract, not through an out-of-band channel like a global flag or side-channel log.

---

## Definition of Done

78. A change MUST pass all automated tests and static analysis before it is marked ready for review.

79. A change MUST have at least one reviewer who understands the affected subsystem before it is merged.

80. A change MUST have no unresolved blocking comments at the time of merge.

81. Any change to a public interface, configuration schema, or observable behavior MUST update the relevant documentation before merge.

82. Any change that requires manual steps to deploy or operate MUST have those steps automated or captured in runbooks before merge.

83. Changes that touch service boundaries MUST include observability for the new code path: at minimum, a log line at the entry and exit of the operation, and a metric or trace if the operation is latency-sensitive.

84. A change MUST NOT knowingly introduce a security vulnerability. Vulnerabilities identified during review that cannot be fixed in the current change MUST be tracked in a security backlog with documented risk acceptance before the change is merged.

85. Changes that affect more than one component SHOULD have a rollback plan or a feature flag that allows the behavior to be disabled without a revert.

86. AI-generated code MUST be held to the same standards as human-written code. An AI agent MUST NOT submit code it cannot explain, and a reviewer MUST NOT approve code they do not understand simply because it was generated automatically.

87. A change is done when it is merged to the main branch, all follow-up tasks are tracked, and the system behaves correctly in the environment closest to production. "It works on my machine" is not done.
