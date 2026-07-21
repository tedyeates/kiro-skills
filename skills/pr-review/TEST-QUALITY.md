# Test Quality Review Checklist

Source: [Testing Quality Standards Research](../../docs/research/testing-quality-standards.md)

## Checklist

| # | Check | Severity | Source | Detection Guidance |
|---|-------|----------|--------|--------------------|
| 1 | New behavior has at least one test | critical | Beck (Behavioral) | Look for new functions/endpoints/routes in diff with no corresponding test file changes |
| 2 | Happy path AND at least one unhappy/error path tested | high | ISTQB EP | Check test files — are there only 'it should work' tests? Look for error handling, edge cases |
| 3 | Test would fail if key operators were flipped (mental mutation test) | high | Mutation testing heuristic | Check assertions — would flipping > to >=, + to -, true to false survive? Weak assertions = survived mutant |
| 4 | Test is deterministic — no sleep(), no uncontrolled randomness | high | Beck (Deterministic), SMURF (Reliability) | Look for setTimeout, sleep, Date.now(), Math.random() without mocking in tests |
| 5 | Boundary values tested for numeric/range/collection-size logic | medium | ISTQB BVA | Numeric params, array operations, string length checks — are 0, 1, max, max+1 tested? |
| 6 | Assertions check outcomes, not implementation steps | medium | Beck (Structure-insensitive), SMURF (Fidelity) | Tests that assert mock.calledWith() exact args, call counts, or internal method order = over-specified |
| 7 | Mocks used only for non-deterministic/slow/external deps | medium | Google mock guidelines | Mocking simple internal functions, mocking DB when in-memory DB available, mocking pure functions |
| 8 | No mocking types the team doesn't own without a wrapper | low | Google TotT 2020 | Direct mocks of third-party library internals (e.g., mock(stripe.charges.create)) without adapter layer |
| 9 | Test is readable — intent clear from name + arrange section | low | Beck (Readable, Writable) | Test names like 'test1', 'it works', unclear arrange sections, magic numbers without explanation |
| 10 | Coverage of new lines exists (not 0%) | low | Fowler on coverage | New code files have no corresponding test file at all — complete gap |

## Severity Levels

- **critical** — PR cannot merge until resolved. Missing tests for new behavior means regressions are invisible.
- **high** — Should be fixed before merge. Weak tests provide false confidence.
- **medium** — Fix recommended. Technical debt that compounds over time.
- **low** — Nice to have. Improves maintainability but not blocking.

## Detection Patterns

### 1. New behavior has at least one test (critical)

Look for:
- New exported functions, classes, or methods in source files
- New API endpoints/routes added
- New CLI commands or flags
- New event handlers or middleware

Red flag: Source file changes with zero test file changes in the same PR.

### 2. Happy + unhappy paths (high)

Look for:
- Test files with only success-case tests
- No tests for: null/undefined inputs, empty arrays, invalid formats, permission denied, network errors
- Missing `throws`/`rejects` assertions

Red flag: All test names describe what "should work" with none describing what "should fail" or "should reject".

### 3. Mental mutation test (high)

Look for:
- Assertions that only check truthiness (`toBeTruthy()`, `toBeDefined()`)
- Comparisons where flipping the operator wouldn't fail the test
- Tests that assert a value exists but not what it equals
- `expect(result).toHaveLength(...)` without checking contents

Red flag: Could you change `>` to `>=` or `+` to `-` in the source and all tests still pass?

### 4. Deterministic tests (high)

Look for in test files:
- `setTimeout`, `sleep`, `delay` without fake timers
- `Date.now()`, `new Date()` without mocking
- `Math.random()` without seeding
- Race conditions from real async operations
- Port binding without dynamic allocation

Red flag: Test uses real time or real randomness without controlling it.

### 5. Boundary values (medium)

Look for in source:
- Numeric comparisons (`<`, `>`, `<=`, `>=`)
- Array/string length checks
- Pagination logic (offset, limit)
- Range validations

Then check tests for: 0, 1, boundary, boundary±1, max values.

Red flag: Only "normal" values tested, no edge cases at boundaries.

### 6. Outcome-based assertions (medium)

Look for:
- `expect(mock).toHaveBeenCalledWith(exact, args)`
- `expect(mock).toHaveBeenCalledTimes(n)`
- Asserting internal method call order
- Testing private method behavior through mock verification

Red flag: Test breaks if you refactor internals without changing behavior.

### 7. Mock scope (medium)

Look for:
- Mocking pure utility functions
- Mocking simple data transformations
- Mocking in-process database when SQLite/in-memory option exists
- Mocking the module under test

Red flag: Mock exists for something that's fast, deterministic, and owned by the team.

### 8. Third-party mock wrappers (low)

Look for:
- `jest.mock('stripe')`, `mock(axios.get)`
- Direct mocks of SDK internals
- No adapter/wrapper layer between app code and third-party APIs

Red flag: Test mocks a type the team doesn't own without an intermediate interface.

### 9. Test readability (low)

Look for:
- Test names: `test1`, `it works`, `should do the thing`
- Magic numbers without explanation
- Arrange section longer than 20 lines without helpers
- No clear arrange/act/assert separation

Red flag: You can't understand what the test verifies from its name alone.

### 10. Coverage of new lines (low)

Look for:
- New source files with no corresponding `*.test.*` or `*.spec.*` file
- New modules with zero test imports

Red flag: Entire new file has no test file at all — complete coverage gap.
