"""Names of Rich components re-exported by :mod:`usecli`.

Kept import-free so the package root can test membership without pulling in
Rich. :mod:`usecli.rich` statically imports every name listed here, which also
lets PyInstaller discover the submodules (``collect_all("usecli")``).
"""

from __future__ import annotations

RICH_EXPORT_NAMES: tuple[str, ...] = (
    # Console and renderable plumbing
    "Console",
    "ConsoleOptions",
    "ConsoleRenderable",
    "Group",
    "RenderableType",
    "RenderHook",
    "RichCast",
    "get_console",
    "reconfigure",
    "print",
    "print_json",
    "inspect",
    "box",
    # Text, styles and themes
    "Span",
    "Style",
    "StyleType",
    "Text",
    "TextType",
    "Theme",
    # Renderables
    "Align",
    "Bar",
    "Column",
    "Columns",
    "Control",
    "JSON",
    "Layout",
    "LayoutRender",
    "Live",
    "Markdown",
    "Padding",
    "Panel",
    "Pretty",
    "Rule",
    "Screen",
    "Segment",
    "Status",
    "Syntax",
    "Table",
    "Traceback",
    "Tree",
    "pprint",
    # Progress
    "Progress",
    "ProgressColumn",
    "TaskID",
    "TextColumn",
    "BarColumn",
    "SpinnerColumn",
    "TimeElapsedColumn",
    "TimeRemainingColumn",
    "MofNCompleteColumn",
    "TaskProgressColumn",
    "DownloadColumn",
    "TransferSpeedColumn",
    "TotalFileSizeColumn",
    "track",
    # Prompts
    "Prompt",
    "Confirm",
    "IntPrompt",
    "FloatPrompt",
)
