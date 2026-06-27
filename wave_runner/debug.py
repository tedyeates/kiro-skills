"""Debug output for wave-runner. Enable with --debug flag."""

_enabled = False


def enable() -> None:
    global _enabled
    _enabled = True


def dbg(msg: str) -> None:
    if _enabled:
        print(f"[DEBUG] {msg}")
