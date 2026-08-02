# Svelte Component Tests (jsdom + @testing-library/svelte) Guide

Correct patterns for Svelte 5 component/page tests that run under **jsdom** via
`@testing-library/svelte` (files named `*.svelte.spec.ts`). This is distinct from
vitest **browser** mode — see [vitest-browser.md](vitest-browser.md) for that. Prefer
`screen`/`within` + `@testing-library/user-event`; there is no `page` locator here.

Every entry below comes from a real cross-test-pollution or async-race failure.

---

## Mock reset: clearing ≠ resetting ≠ draining

`clearMocks` / `vi.clearAllMocks()` clears **call history only** — it does NOT drain
`mockResolvedValueOnce`/`mockImplementationOnce` queues and does NOT reset
implementations. A module-level or `vi.hoisted` mock is shared across every test in
the file, so leftover state bleeds forward.

```typescript
beforeEach(() => {
  vi.clearAllMocks();
  mockQuery.mockResolvedValue([]); // re-seed the base impl every test
});
```

- Re-seed base implementations in `beforeEach` (clearing wiped only history, but be explicit).
- Consume every `*Once` you queue **within its own test** — an unconsumed one is handed to the first matching call in a *later* test.
- Prefer a persistent `mockResolvedValue` override when call *ordering* isn't what you're testing.

## "Passes alone, fails in the suite" = a leaked promise or Once-queue

If a test passes in isolation but fails after another test runs, suspect cross-test
bleed, not a logic bug. The usual carriers: an unconsumed `*Once`, or a **late-rejecting
promise** the component intentionally dropped (a stale request) surfacing as an
unhandled rejection that the runner blames on the *next* test.

**Rule:** any promise you reject on purpose but expect the code under test to ignore
must be pre-handled. Build controlled deferrals with a pre-`.catch()`'d helper:

```typescript
function deferred<T>() {
  let resolve!: (v: T) => void, reject!: (e?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  promise.catch(() => {}); // pre-handle so a dropped rejection can't bleed to the next test
  return { promise, resolve, reject };
}
const flushMicrotasks = async (n = 3) => { for (let i = 0; i < n; i++) await Promise.resolve(); };
```

(If the project has these in its test-utils, import them instead of re-declaring.)

## Testing racy async (request-token / stale-response guards)

For overlapping async work (two concurrent fetches, a stale response losing a race),
route calls by order with deferreds and settle them explicitly. **The fetch that
starts last holds the newest token and wins** — order your calls accordingly:

```typescript
const stale = deferred<Row[]>();   // call #1: older token, will reject
const fresh = deferred<Row[]>();   // call #2: newer token, resolves
let n = 0;
mockQuery.mockImplementation(() => (++n === 1 ? stale.promise : fresh.promise));
// ...trigger #1, then #2, resolve fresh, then reject stale, then:
await flushMicrotasks();
```

Write a one-line **mechanism note** in the test naming which call is which token and
what the guard should do — it forces the ordering understanding these bugs hinge on.
Never substitute an empty `await waitFor(() => {})` or a `setTimeout` for a real flush.

## `loading` state hides the DOM you want to interact with

A refetch that flips `loading = true` typically swaps the list for a spinner — so you
**can't** fire a background refetch first and then click a row/button that's now gone.
To make the *second* fetch the newer-token one while keeping the UI interactive, gate
the upstream async instead of the fetch:

```typescript
const gate = deferred<void>();
mockCompleteCheck.mockReturnValueOnce(gate.promise); // hold the action open
// click the (still-visible) button → its refetch hasn't started yet
// fire the background/realtime refetch first (older token)
gate.resolve();                                       // now the action's refetch runs (newer token)
```

## Prove regression tests actually fail

For a bug-fix test, revert the fix and confirm the test goes **red** before trusting
it; then restore. A test that stays green with the fix reverted isn't reproducing the
bug — fix the harness (check call routing and settle order) rather than piling on more
`flush`/`waitFor` calls. See the `tdd` skill's mocking.md ("Async & Mock-State Hygiene").
