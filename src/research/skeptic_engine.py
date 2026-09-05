"""Skeptic entry points for system-flow checks and statistical falsification."""

from src.validation.protocol import validate_dry_run
from src.validation.skeptic import run_skeptic

__all__ = ["validate_dry_run", "run_skeptic"]
