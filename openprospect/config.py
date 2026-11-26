"""Environment configuration with ZERO_HAWK names and legacy compatibility."""
from __future__ import annotations
import os

def env_value(name: str, default=None):
    """Read the new ZERO_HAWK_* name first, then the former OPENPROSPECT_* name."""
    if name.startswith("OPENPROSPECT_"):
        new_name = "ZERO_HAWK_" + name[len("OPENPROSPECT_"):]
        return os.getenv(new_name, os.getenv(name, default))
    if name.startswith("ZERO_HAWK_"):
        old_name = "OPENPROSPECT_" + name[len("ZERO_HAWK_"):]
        return os.getenv(name, os.getenv(old_name, default))
    return os.getenv(name, default)
