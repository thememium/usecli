"""Coverage-focused tests for usecli.cli.commands.custom.

The package ``__init__`` only contains a module docstring and a
``from __future__ import annotations`` statement (line 3). Importing the
package executes that statement.
"""

from __future__ import annotations


def test_custom_package_imports():
    """Importing the custom commands package executes its module body."""
    from usecli.cli.commands import custom

    assert custom.__name__ == "usecli.cli.commands.custom"
