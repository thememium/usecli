"""UpgradeCommand - upgrade the running application to the latest version.

A built-in default command available in every generated CLI. Installation
discovery, checking, and mutation are delegated to
``usecli.shared.upgrades.UpgradeService``; this command owns only the
interaction: flag handling, confirmation, and output formatting.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.core.exceptions.base import UsecliError
from usecli.shared.config.manager import get_config
from usecli.shared.upgrades import UpgradeService
from usecli.shared.upgrades.checker import UpgradeStatus
from usecli.shared.upgrades.discovery import InstallInfo
from usecli.ui import Confirm


class _LazyConsole:
    _console: Any | None = None

    def _get_console(self) -> Any:
        if self._console is None:
            from rich.console import Console

            self._console = Console()
        return self._console

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_console(), name)


console = _LazyConsole()


def _short_commit(commit: str | None) -> str:
    """Render a commit id for display; version labels pass through intact."""
    if not commit:
        return "-"
    import re

    if re.fullmatch(r"[0-9a-fA-F]{8,40}", commit):
        return commit[:7]
    return commit


class UpgradeCommand(BaseCommand):
    """Upgrade the running application from its original install source."""

    def visible(self) -> bool:
        config = get_config()
        return bool(config.get("upgrade.enabled", True))

    def signature(self) -> str:
        return "upgrade"

    def description(self) -> str:
        return "Upgrade the application to the latest version"

    def handle(
        self,
        check: Annotated[
            bool,
            typer.Option(
                "--check",
                help="Only check for updates; do not install anything.",
            ),
        ] = False,
        force: Annotated[
            bool,
            typer.Option(
                "--force",
                help=(
                    "Upgrade even when already up to date and skip the "
                    "confirmation prompt."
                ),
            ),
        ] = False,
    ) -> dict[str, object]:
        """Handle the command execution."""
        from usecli.cli.core.runtime import is_json_mode

        config = get_config()
        install = UpgradeService.discover(config)
        status = UpgradeService.check(install, config)

        data: dict[str, object] = {
            "mode": "check" if check else "apply",
            "package": install.package,
            "current": install.version,
            "latest": status.latest,
            "source": install.source,
            "source_detail": status.detail,
            "installer": install.installer,
            "url": install.url,
            "revision": install.revision,
            "commit": install.commit,
            "pinned": install.pinned,
            "pinned_reason": install.pinned_reason,
            "frozen": install.frozen,
            "update_available": status.update_available,
            "upgraded": None,
            "error": status.error,
            "latest_tag": status.latest_tag,
            "latest_tag_commit": status.latest_tag_commit,
            "note": status.note,
            "pyproject_path": None,
            "pyproject_previous_version": None,
            "pyproject_new_version": None,
            "pyproject_updated": None,
            "pyproject_reason": None,
        }

        if check:
            if status.error:
                raise UsecliError(
                    status.error,
                    suggestion="Check your network connection and try again.",
                )
            if is_json_mode():
                return data
            self._print_check(status)
            return data

        # Mutations are impossible for these installations; fail loudly.
        if (
            install.frozen
            or install.pinned
            or install.source
            in (
                "editable",
                "unknown",
            )
        ):
            raise UsecliError(
                self._blocked_message(install),
                suggestion=self._blocked_suggestion(install),
            )

        if status.error is None and not status.update_available and not force:
            data["upgraded"] = False
            data["message"] = "Already up to date."
            if is_json_mode():
                return data
            console.print(
                f"[{COLOR.INFO}]Already up to date ({install.version}).[/{COLOR.INFO}]"
            )
            return data

        if not is_json_mode() and not force:
            confirmed = Confirm.ask(
                f"[{COLOR.WARNING}]Upgrade {install.package} from "
                f"{install.version} to "
                f"{_short_commit(status.latest) if status.latest else 'latest'}?"
                f"[/{COLOR.WARNING}]",
                default=False,
            )
            if not confirmed:
                data["upgraded"] = False
                data["message"] = "Aborted."
                console.print(
                    f"[{COLOR.INFO}]Aborted. Re-run with --force to skip "
                    f"confirmation.[/{COLOR.INFO}]"
                )
                return data

        result = self._run_upgrade(install, config, status)
        data["upgraded"] = result.success
        data["message"] = result.message

        if result.pyproject is not None:
            data["pyproject_path"] = result.pyproject.path
            data["pyproject_previous_version"] = result.pyproject.previous_version
            data["pyproject_new_version"] = result.pyproject.new_version
            data["pyproject_updated"] = result.pyproject.updated
            data["pyproject_reason"] = result.pyproject.reason

        if not result.success:
            raise UsecliError(
                result.message or "Upgrade failed.",
                suggestion="Run the upgrade command manually.",
            )

        if is_json_mode():
            return data

        console.print(f"[{COLOR.SUCCESS}]✓ Upgrade complete.[/{COLOR.SUCCESS}]")

        if result.pyproject is not None:
            if result.pyproject.updated:
                console.print(result.pyproject.summary)
            elif result.pyproject.reason:
                console.print(
                    f"[{COLOR.WARNING}]⚠ {result.pyproject.reason}[/{COLOR.WARNING}]"
                )

        from usecli.cli.core.ui.title import get_project_name

        console.print(
            f"Run `[bold {COLOR.PRIMARY}]{get_project_name()} --version"
            f"[/bold {COLOR.PRIMARY}]` to verify."
        )
        return data

    def _run_upgrade(
        self,
        install: InstallInfo,
        config: Any,
        status: UpgradeStatus,
    ):
        """Run the upgrade behind a spinner (auto-disabled in JSON mode)."""
        from usecli import Spinner

        target = status.latest or "latest"
        with Spinner(f"Upgrading {install.package}") as spinner:
            spinner.update(
                f"Upgrading {install.package} ({install.version} → {target})"
            )
            return UpgradeService.upgrade(
                install,
                config,
                target_revision=status.latest_tag,
            )

    def _print_check(self, status: UpgradeStatus) -> None:
        """Render the non-mutating check report."""
        install = status.install
        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Upgrade Check[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)
        self._print_row("Package", install.package or "unknown")
        self._print_row("Installed", install.version)
        self._print_row("Source", status.detail or install.source)
        if install.source == "git":
            if install.revision:
                self._print_row("Ref", install.revision)
            self._print_row("Commit", _short_commit(install.commit))
            if status.latest:
                self._print_row("Latest", _short_commit(status.latest))
        elif status.latest:
            self._print_row("Latest", status.latest)
        self._print_row("Installer", install.installer or "unknown")
        console.print()

        if install.pinned:
            console.print(
                f"[{COLOR.WARNING}]This installation is pinned "
                f"({install.pinned_reason}); no automatic upgrade."
                f"[/{COLOR.WARNING}]"
            )
        elif status.update_available:
            from usecli.cli.core.ui.title import get_project_name

            console.print(
                f"[{COLOR.SUCCESS}]Update available: {install.version} → "
                f"{_short_commit(status.latest)}. Run "
                f"`{get_project_name()} upgrade` to update.[/{COLOR.SUCCESS}]"
            )
        else:
            if status.note:
                console.print(f"[{COLOR.INFO}]{status.note}[/{COLOR.INFO}]")
            else:
                console.print(f"[{COLOR.INFO}]You are up to date.[/{COLOR.INFO}]")
        console.print()

    def _print_row(self, label: str, value: str) -> None:
        visible_value = console.render_str(value).plain
        right_align_column = 76
        indent_width = 2
        padding_spaces = 2
        dots_length = (
            right_align_column
            - indent_width
            - len(label)
            - padding_spaces
            - len(visible_value)
        )
        dots = "." * max(dots_length, 1)
        console.print(
            f"  [{COLOR.FOREGROUND}]{label}[/{COLOR.FOREGROUND}] {dots} {value}"
        )

    def _blocked_message(self, install: InstallInfo) -> str:
        if install.frozen:
            return "This application runs from a frozen bundle and cannot self-upgrade."
        if install.source == "editable":
            return "This is an editable install and cannot self-upgrade."
        if install.pinned:
            return (
                f"This installation is pinned ({install.pinned_reason}) and "
                "will not automatically upgrade."
            )
        return (
            "Could not determine how this application was installed; "
            "automatic upgrade is unavailable."
        )

    def _blocked_suggestion(self, install: InstallInfo) -> str:
        if install.frozen:
            return "Download the latest release or rebuild the bundle."
        if install.source == "editable":
            return "Update the source repository and re-sync (e.g. `uv sync`)."
        if install.source == "git" and install.url:
            revision = f"@{install.revision}" if install.revision else ""
            return (
                "Reinstall from the source you want, e.g. "
                f'`uv tool install --force "{install.package} @ '
                f'git+{install.url}{revision}"`.'
            )
        return "Reinstall the package with your package manager to upgrade."
