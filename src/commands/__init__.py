"""Command modules for SmartClip AI CLI."""

from src.commands.clip import execute_clip
from src.commands.setup import run_setup_wizard

__all__ = [
    "execute_clip",
    "run_setup_wizard",
]
