"""Hacker News plugin for browsing and querying HN content."""

from .hackernews import HackerNewsPlugin

# Import templates to register them
from . import templates

__all__ = ["HackerNewsPlugin"]
