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
