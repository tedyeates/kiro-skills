# Vitest Browser Mode Guide

Correct patterns for vitest browser mode tests. Follow these when writing component or integration tests that run in a real browser via `@vitest/browser`.

---

## Keyboard Interactions

Vitest browser locators support `.click()`, `.dblClick()`, `.fill()`, `.clear()` — but **not** `.press()`.

For keyboard events, use `userEvent.keyboard()` from `@vitest/browser/context`:

```typescript
import { page, userEvent } from '@vitest/browser/context';

// ✅ Fill input then press Enter
await page.getByRole('textbox').fill('search term');
await userEvent.keyboard('{Enter}');

// ✅ Press Escape to close a modal
await userEvent.keyboard('{Escape}');

// ✅ Tab to next element
await userEvent.keyboard('{Tab}');
```

`userEvent.keyboard()` acts on the currently focused element. Focus is set implicitly by preceding interactions (`.fill()`, `.click()`).

**Do not use `.press()` on locators** — this method exists on Playwright's native locator API but is not exposed through vitest-browser-playwright's wrapper.

Reference: https://vitest.dev/guide/browser/interactivity-api#userevent-keyboard

---

## Pre-bundle Dependencies for Tests

When adding a dependency that is imported by components under test, add it to `optimizeDeps.include` in `vite.config.ts`:

```typescript
// vite.config.ts
export default defineConfig({
  optimizeDeps: {
    include: ['svelte-sonner', 'mode-watcher', /* other deps used by tested components */],
  },
  // ...
});
```

**Why:** Vite lazily discovers and bundles dependencies during dev/test. When a full test suite runs in order, a late-discovered dependency triggers mid-run re-optimization — Vite invalidates modules, causing hot-reload-like behavior during test execution. Tests that were passing individually then fail with stale references or unmounted components.

**Symptoms:**
- Tests pass in isolation (`vitest run src/path/to/file.test.ts`) but fail in full suite
- Console shows "new dependencies optimized: <package>" mid-run
- Errors about missing elements or stale component state

**Rule:** When you `pnpm add` a package that will be imported (directly or transitively) by any component that has tests, also add it to `optimizeDeps.include`. This forces Vite to pre-bundle it at startup instead of discovering it mid-run.