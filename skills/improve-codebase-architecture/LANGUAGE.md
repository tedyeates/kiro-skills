# Architecture Vocabulary

Use these terms exactly. Consistent language is the point — don't drift into "component", "service", "API", or "boundary".

## Core Terms

| Term | Definition |
|------|-----------|
| **Module** | Anything with an interface and an implementation — function, class, package, slice |
| **Interface** | Everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature |
| **Implementation** | The code inside the module |
| **Depth** | Leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation |
| **Seam** | Where an interface lives; a place behaviour can be altered without editing in place |
| **Adapter** | A concrete thing satisfying an interface at a seam |
| **Leverage** | What callers get from depth — more capability per unit of interface complexity |
| **Locality** | What maintainers get from depth — change, bugs, knowledge concentrated in one place |

## Principles

### Deletion Test

Imagine deleting the module. Two outcomes:
- **Complexity vanishes** → it was a pass-through (shallow, probably unnecessary)
- **Complexity reappears across N callers** → it was earning its keep (deep, valuable)

### The Interface is the Test Surface

If you can't test a module through its public interface alone, the interface is too narrow or the module is too shallow.

### One Adapter = Hypothetical Seam. Two Adapters = Real Seam.

Don't create seams speculatively. A seam earns its existence when a second adapter appears.

### Deep Over Shallow

Prefer fewer modules with richer implementations over many thin pass-through modules. A deep module:
- Has a simple interface
- Hides significant complexity
- Can be tested in isolation through its interface
- Concentrates related logic (high locality)
- Rarely needs its interface changed

### Shallow Module Warning Signs

- Interface has as many parameters as the implementation has lines
- Callers must understand internal state to use it correctly
- Changing the implementation always requires changing the interface
- The module just delegates to another module (pass-through)
- Tests require mocking the module's internals to be useful
