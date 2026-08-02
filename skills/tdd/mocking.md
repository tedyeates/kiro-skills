# Mocking Guidelines

## When to Mock

Mock **only** at the boundaries of your system — things you don't own or can't control:

| Mock | Don't Mock |
|------|-----------|
| External HTTP APIs | Your own modules |
| Third-party services (Stripe, SendGrid) | Internal collaborators |
| System clock (for time-dependent tests) | Database (use a real test DB) |
| File system (when testing non-FS logic) | Your own utility functions |
| Random number generators | Internal state machines |

## The Rule

**If you wrote it, don't mock it.** Test through it.

Mocking your own code creates tests that verify *wiring*, not *behavior*. When you refactor the wiring, tests break even though behavior is unchanged.

## Good: Mock External Boundaries

```typescript
// Mock the HTTP boundary, test everything else real
const mockWeatherAPI = setupMockServer({
  "GET /forecast": { temp: 72, condition: "sunny" }
});

test("recommendation engine suggests outdoor activity in good weather", async () => {
  const recommendation = await getActivityRecommendation({ location: "NYC" });
  expect(recommendation.type).toBe("outdoor");
  expect(recommendation.reason).toContain("sunny");
});
```

## Bad: Mock Internal Collaborators

```typescript
// DON'T mock your own RecommendationEngine internals
test("controller calls engine correctly", async () => {
  const mockEngine = { recommend: jest.fn().mockReturnValue({ type: "outdoor" }) };
  const controller = new ActivityController(mockEngine);
  await controller.handle({ location: "NYC" });
  expect(mockEngine.recommend).toHaveBeenCalledWith("NYC");
});
```

## Test Database Strategy

Use a real database in tests. Options:
1. **In-memory DB** (SQLite `:memory:`) — fast, isolated
2. **Test container** — real Postgres/MySQL in Docker
3. **Transaction rollback** — wrap each test in a transaction, rollback after

Real DB tests catch:
- Schema mismatches
- Query bugs
- Constraint violations
- Migration issues

Mocked DB tests catch nothing useful.

## When Mocking is Unavoidable

If you must mock (external service, rate limits, cost):
1. Mock at the **thinnest possible adapter layer**
2. Keep the mock's interface identical to the real thing
3. Have at least one integration test that hits the real service (can be slow/skipped in CI)
4. Never mock more than one layer deep

## Async & Mock-State Hygiene

When mocks are shared across tests (module-level or hoisted) and return async values,
state leaks between tests and produces the maddening "passes alone, fails in the
suite" class of flake. The failure is almost always attributed to the wrong test.

### Clearing ≠ resetting ≠ draining

Know exactly what your reset does. In Vitest (Jest is analogous):

- `clearMocks` / `mockClear()` — clears **call history only** (`.mock.calls`,
  `.mock.results`). Does NOT reset implementations or drain one-time queues.
- `resetMocks` / `mockReset()` — clears history **and** wipes implementations and
  the `mockResolvedValueOnce`/`mockImplementationOnce` queue. Wiping implementations
  means you must re-seed base behavior or every mock returns `undefined`.
- `restoreMocks` / `mockRestore()` — only meaningful for spies (`spyOn`); restores
  the original implementation.

Two consequences bite repeatedly:

1. **Queued one-time returns leak.** A `mockResolvedValueOnce` / `mockImplementationOnce`
   that no code path consumes stays in the queue and is handed to the *first* matching
   call in a **later** test. Rules: re-seed base implementations in `beforeEach`;
   ensure every `*Once` you queue is actually consumed by that test; and prefer a
   persistent `mockResolvedValue` override when call *ordering* is not what you're
   testing.

2. **A dropped rejection bleeds.** Code that intentionally ignores a stale/slow
   response (e.g. a request-token guard) still leaves a **rejected promise**. If
   nothing handles it, the rejection surfaces on a later tick and the runner blames
   whichever test is running then. Attach `.catch(() => {})` to any promise you
   reject-on-purpose but expect the code under test to drop.

### Testing racy async deterministically

For overlapping async work (two concurrent fetches, a stale response losing a race),
control settle order with a **deferred** — a promise you resolve/reject from the test
— and drain the microtask queue before asserting:

```ts
function deferred<T>() {
  let resolve!: (v: T) => void, reject!: (e?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  promise.catch(() => {}); // pre-handle: a dropped rejection can't bleed to next test
  return { promise, resolve, reject };
}
const flush = (n = 3) => Array.from({ length: n }).reduce((p) => p.then(() => {}), Promise.resolve());
```

Route calls by order (call #1 wins fast, call #2 hangs until you settle it), trigger
both paths, assert the winner rendered, then settle the loser and `await flush()`.

**Do not** substitute an empty `await waitFor(() => {})` for a real flush — it passes
on the first synchronous check and never waits for a rejection to propagate.

### Verify the test can fail

A regression test is worthless until you've seen it go **red**. Revert the fix and
confirm the test fails; then restore the fix. If it stays green with the fix reverted,
the harness isn't reproducing the bug — check that the second async path actually
fires and that your settle order is right, rather than piling on more `flush`/`waitFor`
calls. And if a bug can't be reproduced after a couple of focused attempts, stop and
flag "not reproducible — needs repro/triage" instead of building an artificial test.
