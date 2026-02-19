"""Inspire command for displaying random inspirational quotes."""

from __future__ import annotations

import json
import urllib.request

from rich.console import Console
from rich.panel import Panel

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.shared.config.manager import get_config

console = Console()


class InspireCommand(BaseCommand):
    """Command for displaying random inspirational quotes."""

    def visible(self) -> bool:
        config = get_config()
        return not config.get("hide_inspire", False)

    def signature(self) -> str:
        """Return the command signature."""
        return "inspire"

    def description(self) -> str:
        """Return the command description."""
        return "Show a random inspirational quote"

    def handle(self) -> None:
        """Handle the command execution."""
        try:
            with urllib.request.urlopen(
                "https://zenquotes.io/api/random/inspiration"
            ) as response:
                data: list[dict[str, str]] = json.loads(response.read().decode())
                quote = data[0]["q"]
                author = data[0]["a"]

                console.print(
                    Panel(
                        f"{quote}\n\n[{COLOR.FOREGROUND_MUTED}]— {author}[/{COLOR.FOREGROUND_MUTED}]",
                        border_style=COLOR.PANEL_PRIMARY,
                        title="Inspire",
                        title_align="left",
                    )
                )
        except Exception as e:
            console.print(f"[{COLOR.ERROR}]Error fetching quote: {e}[/{COLOR.ERROR}]")
