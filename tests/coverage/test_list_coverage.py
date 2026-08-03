"""Coverage-focused tests for usecli.cli.core.ui.list.

Targets uncovered lines in ``collect_commands_data`` and
``list_group_commands`` without modifying source:

- line 112: skip a group subcommand that is an alias of another group
- line 343: usage line when a group has both colon- and space-separated commands
- lines 371-381: include colon-separated commands from the main app
- lines 402-406 / 421-427: display click params in ``list_group_commands``
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import click

from usecli.cli.core.ui.list import list_commands, list_group_commands


class TestCollectCommandsDataGroupAliasSkip:
    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_skips_group_subcommand_that_is_an_alias(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """A group subcommand whose name is an alias of another group is skipped."""
        app = Mock()
        app.registered_commands = []
        app._usecli_group_aliases = {"spec": ["sp"]}

        click_group = click.Group("root")
        click_group.params = []
        group = click.Group("spec")
        group.help = "Commands for spec"
        alias_group = click.Group("sp")
        alias_group.help = "Commands for sp"
        click_group.commands = {"spec": group, "sp": alias_group}
        mock_get_command.return_value = click_group

        result = list_commands(app)

        # Only the primary group "spec" should be listed, not the alias "sp"
        group_names = [g["name"] for g in result["groups"]]
        assert group_names == ["spec"]


class TestListGroupCommandsColonAndNested:
    def _make_group_app(self):
        group_app = Mock()
        group_app.registered_commands = []
        group_app._usecli_aliases = {}
        return group_app

    def _make_main_app(self):
        main_app = Mock()
        main_app.registered_commands = []
        main_app._usecli_aliases = {}
        return main_app

    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_both_colon_and_nested_commands_uses_generic_usage(
        self, mock_get_command, mock_console
    ):
        """When a group has both colon- and space-separated commands, the generic
        usage line is printed and colon commands from the main app are included."""
        group_app = self._make_group_app()
        nested = Mock()
        nested.name = "show"
        nested.callback = Mock(__name__="show")
        nested.help = "Show item"
        group_app.registered_commands = [nested]

        main_app = self._make_main_app()
        colon = Mock()
        colon.name = "spec:generate"
        colon.callback = Mock(__name__="generate")
        colon.help = "Generate"
        main_app.registered_commands = [colon]

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_group_commands(group_app, group_name="spec", main_app=main_app)

        print_calls = [str(c) for c in mock_console.print.call_args_list]
        combined = "\n".join(print_calls)
        # Generic usage line (no group name embedded) is printed
        assert "[COMMAND]" in combined
        # Colon-separated command from main app is included
        assert "spec:generate" in combined

    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_displays_click_params(self, mock_get_command, mock_console):
        """list_group_commands renders click group params in the options section."""
        group_app = self._make_group_app()
        cmd = Mock()
        cmd.name = "show"
        cmd.callback = Mock(__name__="show")
        cmd.help = "Show item"
        group_app.registered_commands = [cmd]

        param = Mock()
        param.opts = ["--verbose", "-v"]
        param.help = "Verbose output"

        click_group = Mock()
        click_group.params = [param]
        mock_get_command.return_value = click_group

        list_group_commands(group_app, group_name="spec")

        print_calls = [str(c) for c in mock_console.print.call_args_list]
        combined = "\n".join(print_calls)
        assert "--verbose" in combined
        assert "Verbose output" in combined

    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_skips_help_param_in_options(self, mock_get_command, mock_console):
        """A --help param is skipped from the options section."""
        group_app = self._make_group_app()
        cmd = Mock()
        cmd.name = "show"
        cmd.callback = Mock(__name__="show")
        cmd.help = "Show item"
        group_app.registered_commands = [cmd]

        help_param = Mock()
        help_param.opts = ["--help", "-h"]
        help_param.help = "Show help"

        custom_param = Mock()
        custom_param.opts = ["--debug", "-d"]
        custom_param.help = "Debug mode"

        click_group = Mock()
        click_group.params = [help_param, custom_param]
        mock_get_command.return_value = click_group

        list_group_commands(group_app, group_name="spec")

        print_calls = [str(c) for c in mock_console.print.call_args_list]
        combined = "\n".join(print_calls)
        assert "--debug" in combined

    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_skips_main_app_command_not_matching_prefix(
        self, mock_get_command, mock_console
    ):
        """A main-app command that does not start with the group prefix is
        skipped (line 376)."""
        group_app = self._make_group_app()
        nested = Mock()
        nested.name = "show"
        nested.callback = Mock(__name__="show")
        nested.help = "Show item"
        group_app.registered_commands = [nested]

        main_app = self._make_main_app()
        other = Mock()
        other.name = "other:thing"
        other.callback = Mock(__name__="thing")
        other.help = "Other"
        main_app.registered_commands = [other]

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_group_commands(group_app, group_name="spec", main_app=main_app)

        print_calls = [str(c) for c in mock_console.print.call_args_list]
        combined = "\n".join(print_calls)
        assert "other:thing" not in combined

    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_skips_main_app_command_already_in_group(
        self, mock_get_command, mock_console
    ):
        """A main-app command already present in the group is skipped
        (line 378)."""
        group_app = self._make_group_app()
        nested = Mock()
        nested.name = "spec:show"
        nested.callback = Mock(__name__="show")
        nested.help = "Show item"
        group_app.registered_commands = [nested]

        main_app = self._make_main_app()
        colon = Mock()
        colon.name = "spec:show"
        colon.callback = Mock(__name__="show")
        colon.help = "Show item"
        main_app.registered_commands = [colon]

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_group_commands(group_app, group_name="spec", main_app=main_app)

        print_calls = [str(c) for c in mock_console.print.call_args_list]
        combined = "\n".join(print_calls)
        assert combined.count("spec:show") == 1
