# UI Prototype

Generate **several radically different UI variations** on a single route, switchable from a floating bottom bar. The user flips between variants, picks one (or steals bits from each), then throws the rest away.

## When this is the right shape

- "What should this page look like?"
- "I want to see a few options for this dashboard before committing."
- "Try a different layout for the settings screen."

If the question is about logic/state — wrong branch. Use [LOGIC.md](LOGIC.md).

## Two sub-shapes — prefer sub-shape A

### Sub-shape A — adjustment to an existing page (preferred)

The route already exists. Variants are rendered on the same route, gated by a `?variant=` URL search param. Existing data fetching, params, and auth all stay — only the rendering swaps.

### Sub-shape B — a new page (last resort)

Only when the thing being prototyped has no existing page to live inside. Create a throwaway route following the project's routing convention. Name it so it's obviously a prototype.

## Process

### 1. State the question and pick N

Default to **3 variants**. Cap at 5. Write down the plan:
> "Three variants of the settings page, switchable via `?variant=`, on the existing `/settings` route."

### 2. Generate radically different variants

Each variant must be **structurally different** — different layout, different information hierarchy, different primary affordance. Not just different colours.

Hold each one to:
- The page's purpose and available data
- The project's component library / styling system
- A clear exported component name: `VariantA`, `VariantB`, `VariantC`

### 3. Wire them together

Single switcher component on the route:

```tsx
const variant = searchParams.get('variant') ?? 'A';
return (
  <>
    {variant === 'A' && <VariantA />}
    {variant === 'B' && <VariantB />}
    {variant === 'C' && <VariantC />}
    <VariantSwitcher current={variant} />
  </>
);
```

### 4. Build the floating switcher

Fixed-position bar at bottom-centre with:
- **Left/right arrows** — cycle variants (update URL search param)
- **Variant label** — shows current key and name
- Keyboard: `←` and `→` arrow keys cycle (don't intercept when input focused)
- Hidden in production builds

### 5. Hand it over

Surface the URL and `?variant=` keys. Typical feedback: "I want the header from B with the sidebar from C."

### 6. Capture and clean up

Record which variant won and why. Then:
- **Sub-shape A** — delete losing variants and switcher; fold winner into existing page
- **Sub-shape B** — promote winner to real route; delete throwaway route and switcher

## Anti-patterns

- Variants that differ only in colour or copy — that's a tweak, not a prototype
- Sharing too much code between variants — defeats the point
- Wiring variants to real mutations — use stubs
- Promoting prototype directly to production — rewrite properly when folding in
