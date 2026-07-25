"""Theme-aware progress indicators for usecli commands."""

from __future__ import annotations

from types import TracebackType

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
)

from usecli.cli.config.colors import COLOR
from usecli.cli.core.runtime import is_json_mode, is_quiet


def _is_disabled(console: Console, *, quiet: bool) -> bool:
    """Return whether progress rendering must be suppressed."""
    return is_json_mode() or is_quiet() or quiet or not console.is_interactive


class Spinner:
    """Indeterminate progress indicator that renders only to terminal stderr."""

    def __init__(
        self,
        message: str,
        *,
        quiet: bool = False,
        spinner: str = "dots",
    ) -> None:
        self.message = message
        self.quiet = quiet
        self.spinner = spinner
        self.console = Console(stderr=True)
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None

    def __enter__(self) -> Spinner:
        progress = Progress(
            SpinnerColumn(
                spinner_name=self.spinner,
                style=COLOR.PRIMARY,
            ),
            TextColumn(
                "{task.description}",
                style=COLOR.INFO,
            ),
            console=self.console,
            disable=_is_disabled(self.console, quiet=self.quiet),
            redirect_stdout=False,
            redirect_stderr=False,
            transient=True,
        )
        progress.__enter__()
        self._task_id = progress.add_task(self.message, total=None)
        self._progress = progress
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._progress is not None:
            self._progress.__exit__(exc_type, exc_value, traceback)
            self._progress = None
            self._task_id = None

    def update(self, message: str) -> None:
        """Replace the status message without changing command behavior."""
        self.message = message
        if self._progress is not None and self._task_id is not None:
            self._progress.update(self._task_id, description=message)


class ProgressBar:
    """Determinate progress bar that renders only to terminal stderr."""

    def __init__(
        self,
        total: float,
        description: str = "Working",
        *,
        quiet: bool = False,
    ) -> None:
        self.total = total
        self.description = description
        self.quiet = quiet
        self.completed: float = 0
        self.console = Console(stderr=True)
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None

    def __enter__(self) -> ProgressBar:
        progress = Progress(
            TextColumn(
                "[progress.description]{task.description}",
                style=COLOR.INFO,
            ),
            BarColumn(
                style=COLOR.FOREGROUND_MUTED,
                complete_style=COLOR.PRIMARY,
                finished_style=COLOR.SUCCESS,
            ),
            TaskProgressColumn(
                text_format=(
                    f"[{COLOR.SUCCESS}]{{task.percentage:>3.0f}}%[/{COLOR.SUCCESS}]"
                )
            ),
            console=self.console,
            disable=_is_disabled(self.console, quiet=self.quiet),
            redirect_stdout=False,
            redirect_stderr=False,
        )
        progress.__enter__()
        self._task_id = progress.add_task(
            self.description,
            total=self.total,
        )
        self._progress = progress
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._progress is not None:
            self._progress.__exit__(exc_type, exc_value, traceback)
            self._progress = None
            self._task_id = None

    def advance(self, amount: float = 1) -> None:
        """Advance the tracked task by ``amount`` steps."""
        self.completed += amount
        if self._progress is not None and self._task_id is not None:
            self._progress.advance(self._task_id, amount)

    def update(
        self,
        *,
        completed: float | None = None,
        description: str | None = None,
    ) -> None:
        """Update completed work and/or the displayed description."""
        if completed is not None:
            self.completed = completed
        if description is not None:
            self.description = description
        if (
            self._progress is not None
            and self._task_id is not None
            and (completed is not None or description is not None)
        ):
            self._progress.update(
                self._task_id,
                completed=completed,
                description=description,
            )


__all__ = ["Spinner", "ProgressBar"]
