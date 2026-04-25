# sandbox/trust_zones.py
"""Defines TRUSTED / SANDBOXED / ISOLATED execution contexts.

Every code execution happens within a trust zone that determines:
- What filesystem access is allowed
- What network access is allowed
- What imports are permitted
- Timeout constraints
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional


class TrustZone(Enum):
    """Execution trust levels.

    TRUSTED: Code we wrote, full access
    SANDBOXED: User code, limited access
    ISOLATED: Untrusted code, minimal access
    """
    TRUSTED = 1
    SANDBOXED = 2
    ISOLATED = 3


@dataclass(frozen=True)
class ExecutionContext:
    """Context for a code execution.

    Determines what the executed code is allowed to do.
    """
    zone: TrustZone = TrustZone.SANDBOXED
    timeout_seconds: int = 30
    allowed_imports: list[str] = field(default_factory=list)
    working_dir: Optional[Path] = None
    env_vars: dict[str, str] = field(default_factory=dict)
    memory_limit_mb: Optional[int] = None
    network_allowed: bool = False
    file_write_allowed: bool = False


# Preset contexts for common operations
TRUSTED_CONTEXT = ExecutionContext(
    zone=TrustZone.TRUSTED,
    timeout_seconds=60,
    network_allowed=True,
    file_write_allowed=True,
)

SANDBOXED_CONTEXT = ExecutionContext(
    zone=TrustZone.SANDBOXED,
    timeout_seconds=30,
    allowed_imports=["os", "sys", "json", "re", "math", "random", "datetime", "collections", "itertools"],
    network_allowed=False,
    file_write_allowed=True,  # But only in working_dir
)

ISOLATED_CONTEXT = ExecutionContext(
    zone=TrustZone.ISOLATED,
    timeout_seconds=10,
    allowed_imports=[],
    network_allowed=False,
    file_write_allowed=False,
)
