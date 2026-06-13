"""Help command for displaying CLI help information."""

from __future__ import annotations

from usecli.cli.core.base_command import BaseCommand


class HelpCommand(BaseCommand):
    """Command for displaying help information."""

    def signature(self) -> str:
        """Return the command signature."""
        return "help"

    def description(self) -> str:
        """Return the command description."""
        return "Show help information"

    def handle(self) -> None:
        """Handle the command execution."""
        from usecli.cli.core.ui.list import list_commands

        list_commands(self.app)
