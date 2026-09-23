"""Compatibility entry point for the relocated strategy worker."""

from .infrastructure.worker import load_class, main

__all__ = ["load_class", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
