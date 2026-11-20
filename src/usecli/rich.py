# ruff: noqa: F401
# This module exists to re-export Rich's public API.
"""Rich components re-exported under the ``usecli`` namespace.

Use this when a project should not import ``rich`` directly::

    from usecli.rich import Markdown, Syntax, Table, Tree

Every name here is also available from the package root, lazily::

    from usecli import Markdown, Syntax, Table, Tree

The imports below are static on purpose: PyInstaller's ``collect_all("usecli")``
then discovers the Rich submodules for frozen CLI bundles.
"""

from __future__ import annotations

from rich import box, get_console, inspect, print, print_json, reconfigure
from rich.align import Align
from rich.bar import Bar
from rich.columns import Columns
from rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    Group,
    RenderableType,
    RenderHook,
    RichCast,
)
from rich.control import Control
from rich.json import JSON
from rich.layout import Layout, LayoutRender
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.pretty import Pretty, pprint
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TotalFileSizeColumn,
    TransferSpeedColumn,
    track,
)
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.rule import Rule
from rich.screen import Screen
from rich.segment import Segment
from rich.status import Status
from rich.style import Style, StyleType
from rich.syntax import Syntax
from rich.table import Column, Table
from rich.text import Span, Text, TextType
from rich.theme import Theme
from rich.traceback import Traceback
from rich.tree import Tree

from usecli._rich_exports import RICH_EXPORT_NAMES

__all__ = list(RICH_EXPORT_NAMES)
