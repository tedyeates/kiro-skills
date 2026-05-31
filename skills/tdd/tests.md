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

## The Litmus Test

Ask: "If I completely rewrote the internals but kept the same external behavior, would this test still pass?"

- **Yes** → Good test
- **No** → Implementation-coupled test, rewrite it
