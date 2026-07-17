# Research: Testing Quality Standards for Code Review

Date: 2026-07-16
Question: What testing standards should a PR review skill use to assess test quality?

## Findings

### Kent Beck's Test Desiderata

12 properties as sliders: Isolated, Composable, Deterministic, Specific, Behavioral, Structure-insensitive, Fast, Writable, Readable, Automated, Predictive, Inspiring. For PR review: **Structure-insensitive** — "too much mocking is a structure sensitivity nightmare"; **Behavioral** — should fail on accidental behavior change; **Specific** — failure points to short code of interest.

Source: https://tidyfirst.substack.com/p/desirable-unit-tests

### ISTQB Black-Box Test Design Techniques

**Equivalence Partitioning (EP):** Divides input into partitions processed identically. One test per partition suffices. Reviewer check: is each valid and invalid partition tested?

**Boundary Value Analysis (BVA):** Tests boundaries of partitions — min, max, and just outside. "Developers are more likely to make errors with boundary values." Flag numeric/range logic tested only with mid-range values.

Source: https://astqb.org/4-2-black-box-test-techniques/ (ISTQB CTFL v4.0, §4.2)

### Google SMURF Framework

5 trade-off dimensions beyond the pyramid: **Speed, Maintainability, Utilization, Reliability, Fidelity**. Key tension for review: Fidelity vs Maintainability — mocks improve speed but reduce fidelity. A test that mocks everything may not catch real bugs.

Source: https://testing.googleblog.com/2024/10/smurf-beyond-test-pyramid.html

### Mutation Testing as Quality Signal

Injects small faults (flipping `>` to `>=`, swapping `+` for `-`) and checks if tests catch them. Survived mutants = assertion gaps that line coverage misses. Applicable as a mental heuristic in review: could a simple operator flip in new code survive without any test failing?

Source: https://ar5iv.labs.arxiv.org/html/2309.02395

### Martin Fowler on Test Coverage

"Test coverage is a useful tool for finding untested parts of a codebase. Test coverage is of little use as a numeric statement of how good your tests are." Use coverage to spot gaps, never to approve quality.

Source: https://martinfowler.com/bliki/TestCoverage.html

## Mock Quality Heuristics

Synthesized from Google Testing Blog (2013, 2020, 2024) and Fowler's "Mocks Aren't Stubs":

**Mocks are legitimate when:**
- Dependency is non-deterministic (clock, network, randomness)
- Dependency is slow/expensive (external API, heavy computation)
- Testing a specific error path hard to trigger naturally (timeouts, rate limits)
- Verifying a side-effect call was made (analytics, audit logging)

**Mocks are harmful when:**
- They replicate implementation details, coupling tests to internals (Google 2013: "you're leaking implementation details into your test")
- They mock types you don't own — assumptions drift from real behavior (Google 2020)
- A real implementation or fake is available and practical (Google 2024: prefer real > fake > mock)
- They assert on call order or exact arguments unrelated to tested behavior

**Rule of thumb:** If using the real thing would make the test more trustworthy without making it meaningfully slower or flakier, the mock is hurting.

Sources:
- https://testing.googleblog.com/2013/05/testing-on-toilet-dont-overuse-mocks.html
- https://testing.googleblog.com/2020/07/testing-on-toilet-dont-mock-types-you.html
- https://testing.googleblog.com/2024/02/increase-test-fidelity-by-avoiding-mocks.html
- https://martinfowler.com/articles/mocksArentStubs.html

## Recommended Checklist

For a PR review skill to assess test quality, check these concrete items:

| # | Check | Severity | Source |
|---|-------|----------|--------|
| 1 | New behavior has at least one test | blocker | Beck (Behavioral) |
| 2 | Happy path AND at least one unhappy/error path tested | high | ISTQB EP (valid + invalid partitions) |
| 3 | Boundary values tested for numeric/range/collection-size logic | medium | ISTQB BVA |
| 4 | Test would fail if key operators were flipped (mental mutation test) | high | Mutation testing heuristic |
| 5 | Assertions check outcomes, not implementation steps | medium | Beck (Structure-insensitive), Google SMURF (Fidelity) |
| 6 | Mocks used only for non-deterministic/slow/external deps | medium | Google mock guidelines |
| 7 | No mocking of types the team doesn't own without a wrapper | low | Google TotT 2020 |
| 8 | Test is readable — intent clear from name + arrange section | low | Beck (Readable, Writable) |
| 9 | Coverage of new lines exists (not 0%) — but high % alone isn't approval | info | Fowler on coverage |
| 10 | Test is deterministic — no sleep(), no uncontrolled randomness | high | Beck (Deterministic), SMURF (Reliability) |

## Summary

No single standard like OWASP exists for test quality. The strongest framework combines ISTQB's systematic techniques (EP + BVA) for identifying *what* to test, Beck's Test Desiderata for *properties* good tests should have, Google's SMURF + mock guidelines for *trade-off* decisions, and mutation testing as a mental model for assertion strength. Coverage is a gap-finder, not a quality measure.

## Open Questions

- Should the skill run actual mutation testing on diffs, or only apply it as a heuristic? (Stryker/PIT exist but are slow)
- How to weight severity for safety-critical vs. cosmetic code paths?
- Should mock rules differ between unit test and integration test PRs?
- What threshold of untested new lines triggers blocker vs. warning?
