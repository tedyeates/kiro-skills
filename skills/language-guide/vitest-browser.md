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
