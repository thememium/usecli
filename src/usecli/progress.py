"""Theme-aware progress indicators for usecli commands.

Both indicators write to stderr and are suppressed automatically in JSON mode,
quiet mode, and non-interactive terminals. Prefer importing them from the
package root (``from usecli import ProgressBar, Spinner``).
"""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

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
    """Indeterminate progress indicator for work with no known total.

    Renders a transient spinner and status message to stderr using the active
    usecli theme. Rendering is suppressed automatically in JSON mode, in quiet
    mode, when ``quiet=True``, or when stderr is not a terminal, so commands
    can keep the block in place in every environment.

    Use it as a context manager; the spinner line is erased on exit. Call
    :meth:`update` to change the message while the block runs.

    Args:
        message: Initial status message.
        quiet: Suppress rendering regardless of the terminal.
        spinner: Rich spinner style name, for example ``"dots"`` or ``"line"``.

    Attributes:
        message: Current status message.
        quiet: Whether rendering was explicitly suppressed.
        spinner: Rich spinner style name.

    Example:
        >>> with Spinner("Loading records") as spinner:
        ...     load_records()
        ...     spinner.update("Indexing records")

    Note:
        Instances are not thread-safe.
    """

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

    def __enter__(self) -> Self:
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
        """Change the status message shown while the block runs.

        Safe to call before entering the context manager: the message is
        applied when the spinner starts. The message is still recorded when
        rendering is suppressed, so later ``update`` calls remain consistent.
        """
        self.message = message
        if self._progress is not None and self._task_id is not None:
            self._progress.update(self._task_id, description=message)


class ProgressBar:
    """Determinate progress bar for work with a known total.

    Renders the description, a bar, and a percentage to stderr using the active
    usecli theme. Advance it with :meth:`advance`, or set absolute progress
    with :meth:`update`. Rendering is suppressed automatically in JSON mode, in
    quiet mode, when ``quiet=True``, or when stderr is not a terminal; counters
    still update, so command logic never branches on the environment.

    Args:
        total: Number of steps expected.
        description: Label shown before the bar.
        quiet: Suppress rendering regardless of the terminal.

    Attributes:
        total: Number of steps expected.
        description: Current label.
        completed: Steps recorded so far.

    Example:
        >>> with ProgressBar(total=len(items), description="Processing") as bar:
        ...     for item in items:
        ...         process(item)
        ...         bar.advance()

    Note:
        Not thread-safe; update from the thread that entered the context.
    """

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

    def __enter__(self) -> Self:
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
        """Record ``amount`` completed steps.

        ``amount`` may be fractional when ``total`` is fractional. The local
        counter is always updated; the rendered bar refreshes only while the
        context manager is active and rendering is enabled.
        """
        self.completed += amount
        if self._progress is not None and self._task_id is not None:
            self._progress.advance(self._task_id, amount)

    def update(
        self,
        *,
        completed: float | None = None,
        description: str | None = None,
    ) -> None:
        """Set completed steps, the description, or both.

        ``None`` leaves the corresponding field unchanged. Local state is
        always updated; the rendered bar refreshes only while the context
        manager is active and rendering is enabled.
        """
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


__all__ = ["ProgressBar", "Spinner"]
