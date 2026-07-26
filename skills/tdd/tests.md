# Test Examples

## Good Tests (Behavior-Based)

```typescript
// Tests WHAT the system does, not HOW
test("user can create an account with valid email", async () => {
  const result = await createAccount({ email: "user@example.com", password: "secure123" });
  expect(result.success).toBe(true);
  expect(result.user.email).toBe("user@example.com");
});

test("duplicate email returns clear error", async () => {
  await createAccount({ email: "taken@example.com", password: "pass1" });
  const result = await createAccount({ email: "taken@example.com", password: "pass2" });
  expect(result.success).toBe(false);
  expect(result.error).toContain("already exists");
});

test("checkout calculates total with tax", async () => {
  const cart = await addItems([
    { sku: "WIDGET-1", qty: 2, price: 10.00 },
    { sku: "GADGET-1", qty: 1, price: 25.00 },
  ]);
  const checkout = await calculateCheckout(cart, { taxRate: 0.08 });
  expect(checkout.subtotal).toBe(45.00);
  expect(checkout.tax).toBe(3.60);
  expect(checkout.total).toBe(48.60);
});
```

Why these are good:
- Test through public API (`createAccount`, `calculateCheckout`)
- Describe user-visible behavior
- Would survive any internal refactor
- Read like specifications

## Bad Tests (Implementation-Coupled)

```typescript
// Tests HOW the system works internally — AVOID
test("UserService calls repository.save", async () => {
  const mockRepo = { save: jest.fn() };
  const service = new UserService(mockRepo);
  await service.createAccount({ email: "user@example.com" });
  expect(mockRepo.save).toHaveBeenCalledWith(expect.objectContaining({ email: "user@example.com" }));
});

test("calculateTotal uses TaxCalculator", () => {
  const mockTax = { calculate: jest.fn().mockReturnValue(3.60) };
  const checkout = new CheckoutService(mockTax);
  checkout.calculateTotal(45.00);
  expect(mockTax.calculate).toHaveBeenCalledWith(45.00);
});

test("internal state is updated correctly", () => {
  const cart = new Cart();
  cart.addItem({ sku: "X", qty: 1 });
  // Reaching into private state:
  expect(cart._items.length).toBe(1);
  expect(cart._items[0]._sku).toBe("X");
});
```

Why these are bad:
- Coupled to internal class names and method signatures
- Break when you refactor (rename `UserService` → tests fail, behavior unchanged)
- Test the *shape* of collaboration, not the *result*
- Mock internal collaborators instead of testing through the real path

## Test Stable Contracts, Not Implementation Details

Use semantic selectors that represent **state or role** — not framework output that can change without behavior changing.

**Good selectors:**
```typescript
// Semantic CSS class representing state
screen.getByRole("row", { name: /overdue/i })
container.querySelector(".highlight-overdue")

// Data attributes for test hooks
screen.getByTestId("invoice-row-overdue")
```

**Bad selectors:**
```typescript
// Tailwind utility classes — change when design changes, behavior unchanged
container.querySelector("tr.bg-red-100")
expect(row).toHaveClass("text-amber-600")

// Framework-generated IDs or internal DOM structure
document.getElementById("radix-:r2:")
container.querySelector("div > div:nth-child(3) > span")
```

**Rule:** If the thing you're querying could change without the behaviour changing, it's an implementation detail. Define semantic classes or data attributes that represent the *state* and test against those.

This applies to any framework output: Tailwind classes, generated IDs, CSS-in-JS classnames, framework-internal DOM structure.

## The Litmus Test

Ask: "If I completely rewrote the internals but kept the same external behavior, would this test still pass?"

- **Yes** → Good test
- **No** → Implementation-coupled test, rewrite it

## Test-Tier Topology

The guidance above covers test *quality* — writing behavior-based tests, not implementation-coupled ones. This section covers tier *topology* — which layer to write the test in, so agents stop defaulting to slow, flaky browser-mode tests for things a faster tier already proves.

Four tiers, each proving a different seam:

| Tier | Proves | Typical file suffix | Runner |
|------|--------|---------------------|--------|
| jsdom component | Component behavior — render, user interaction, DOM assertions | `*.svelte.spec.ts` (Svelte) / framework-equivalent | `@testing-library/*` + `user-event`, Node + jsdom — no real browser |
| SSR page-wiring | Page-wiring — does a page actually connect its loaded data + child components into the rendered output | `*.ssr.spec.ts` | Server-side render call (e.g. `render` from `svelte/server`), plain Node env |
| pgTAP (or equivalent) | DB — schema, RLS/permissions, views, constraints | SQL test files | In-DB test runner (e.g. pgTAP) against a real local instance |
| Thin human e2e | Real-stack smoke — flows that need a genuine browser + genuine backend together | e2e spec files | Full browser (e.g. Playwright), run by a human, not in the agent loop |

**Why jsdom over browser-mode for component tests:** shared-browser test runners (e.g. vitest browser mode) discover app dependencies lazily at runtime; each discovery triggers a dev-server dep re-optimize + full page reload that kills in-flight tests, producing non-deterministic timeouts in an unattended agent loop. Rendering through Node/jsdom transforms dependencies ahead of time instead, so there's no mid-run reload — component tests become deterministic. Reserve real-browser rendering for the thin e2e tier below, where it's unavoidable.

**Why a separate SSR tier:** "component builds but is never wired into its page" is a common bug class that jsdom component tests don't catch (they render the component in isolation, not the page). A cheap server-render assertion — does the page's rendered HTML actually contain the data and child components it's supposed to wire in — catches this without a browser.

### e2e-authoring bar (thin by principle)

Author an e2e test only when the jsdom, SSR, and DB tiers genuinely cannot prove the flow — i.e. it needs a real authenticated session, real file/object storage, or a redirect that crosses layers (e.g. auth middleware → route). If a faster tier can prove it, prove it there instead; don't reach for e2e by default.

Implementers **author** e2e specs as part of a feature but **never run them in the agent loop** — e2e is a human-run smoke layer, kept intentionally small, out of the deterministic test loop that gates agent PRs.

### Applying this to a project

The suffix/runner names above are illustrative (Svelte + Vitest + Playwright); adapt to the project's actual stack. Check the project's own testing docs or steering for the concrete tier mapping before assuming these exact names apply.
