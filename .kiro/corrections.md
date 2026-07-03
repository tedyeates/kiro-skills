# Corrections Log

- ❌ `"pytest"` exact match in allowedCommands blocks `pytest tests/ -v` → ✅ `"pytest.*"` (patterns need `.*` suffix to allow arguments)


