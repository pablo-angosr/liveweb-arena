"""Simple logging utility for LiveWeb Arena"""

import sys
from typing import Optional

# Global verbose flag
_verbose = False


def set_verbose(enabled: bool):
    """Enable or disable verbose logging"""
    global _verbose
    _verbose = enabled


def is_verbose() -> bool:
    """Check if verbose mode is enabled"""
    return _verbose


def log(tag: str, message: str, force: bool = False):
    """
    Print a log message if verbose mode is enabled.

    Args:
        tag: Component tag (e.g., "LLM", "Agent", "Actor")
        message: Log message
        force: Print even if verbose is disabled (for errors/warnings)
    """
    if _verbose or force:
        print(f"[{tag}] {message}", file=sys.stderr, flush=True)
