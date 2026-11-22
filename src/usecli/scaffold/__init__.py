"""Scaffold usecli commands, themes, and skills from Python.

The ``make:*`` CLI commands are thin wrappers around these functions. Import
them to generate artifacts from your own CLI or script while still honoring the
project's ``usecli.config.toml`` paths and templates.

Example:
    .. code-block:: python

        from usecli.scaffold import make_command, make_theme, make_skill

        make_command("deploy")
        make_theme("dusk")
        make_skill("deploy-checks", description="Check deployments")

Every ``make_*`` function returns the path it wrote. Pass ``force=True`` to
overwrite an existing command or skill, or an existing theme file.
"""

from __future__ import annotations

from pathlib import Path

from caseconverter import pascalcase, snakecase
from jinja2 import Template

from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.validators import validate_skill_name
from usecli.shared.config.globals import TEMPLATES_DIR
from usecli.shared.config.manager import (
    ConfigManager,
    find_project_root,
    get_config,
    reset_config,
)

DEFAULT_COMMAND_NAME = "usecli"

_COMMAND_TEMPLATE = "command.py.j2"
_THEME_TEMPLATE = "theme.toml.j2"
_SKILL_TEMPLATE = "project_skill.md.j2"


class ScaffoldError(ValueError):
    """Raised when a scaffold name is invalid or its target already exists."""


def _resolve_config(
    config: ConfigManager | None,
    project_root: str | Path | None,
) -> ConfigManager:
    """Return the config for the current (or requested) project."""
    if config is not None:
        return config

    if project_root is not None:
        return ConfigManager(start_dir=Path(project_root))

    start = Path.cwd()
    root = find_project_root(start) or start.resolve()
    current = get_config()
    if current.get_project_root().resolve() != root:
        reset_config()
        current = get_config()
    return current


def _resolve_dir(value: str | Path | None, fallback: Path) -> Path:
    """Use an explicit output directory when one was supplied."""
    return Path(value) if value is not None else fallback


def _select_template(templates_dir: Path | None, filename: str) -> Path:
    """Prefer a project template over the framework's built-in template."""
    if templates_dir is not None:
        candidate = templates_dir / filename
        if candidate.exists():
            return candidate
    return TEMPLATES_DIR / filename


def _command_parts(name: str) -> tuple[str, str, str]:
    """Return the class name, signature, and filename for a command name."""
    clean_name = name.replace("Command", "").replace("command", "")
    class_name = pascalcase(clean_name.replace(":", "_").replace(" ", "_")) + "Command"
    if ":" in clean_name or " " in clean_name:
        command_name = clean_name
    else:
        command_name = snakecase(clean_name)
    file_name = (
        f"{snakecase(clean_name.replace(':', '_').replace(' ', '_'))}_command.py"
    )
    return class_name, command_name, file_name


def _frontmatter_description(value: str) -> str:
    """Normalize a skill description for a double-quoted YAML scalar."""
    normalized = " ".join(value.split())
    return normalized.replace("\\", "\\\\").replace('"', '\\"')


def _theme_target(themes_dir: Path, name: str, force: bool) -> Path:
    """Resolve the theme path, incrementing duplicate names unless forced."""
    clean_name = name.strip()
    if not clean_name:
        raise ScaffoldError("Theme name cannot be empty.")

    base_name = Path(clean_name).name.removesuffix(".toml")
    if not base_name:
        raise ScaffoldError("Theme name cannot be empty.")

    target = themes_dir / f"{base_name}.toml"
    if force:
        return target

    counter = 1
    while target.exists():
        target = themes_dir / f"{base_name}_{counter}.toml"
        counter += 1
    return target


def make_command(
    name: str,
    *,
    config: ConfigManager | None = None,
    commands_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    project_root: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Create a new CLI command module and return its path.

    Args:
        name: The command name. Colons create grouped signatures, and spaces
            are accepted (``"my command"``).
        config: Config to use. Defaults to the config for ``project_root`` or
            the current working directory.
        commands_dir: Output directory. Defaults to the project's configured
            command package.
        templates_dir: Directory containing ``command.py.j2``. Defaults to the
            project's configured templates directory.
        project_root: Directory used to discover the project config.
        force: Overwrite an existing command file instead of raising
            :class:`ScaffoldError`.

    Returns:
        The path of the command module that was written.

    Raises:
        ScaffoldError: When the name is empty or the command already exists
            and ``force`` is false.
    """
    if not name.strip():
        raise ScaffoldError("Command name cannot be empty.")

    resolved = _resolve_config(config, project_root)
    project_paths = resolved.get_project_paths()
    target_dir = _resolve_dir(commands_dir, project_paths["commands_dir"])
    template_dir = _resolve_dir(templates_dir, project_paths["templates_dir"])

    class_name, command_name, file_name = _command_parts(name)
    target_file = target_dir / file_name
    if target_file.exists() and not force:
        raise ScaffoldError(f"Command file {target_file} already exists.")

    template = Template(_select_template(template_dir, _COMMAND_TEMPLATE).read_text())
    rendered_content = template.render(class_name=class_name, command_name=command_name)

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(rendered_content)
    return target_file


def make_theme(
    name: str,
    *,
    config: ConfigManager | None = None,
    themes_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    project_root: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Create a new theme file and return its path.

    Duplicate names get a numeric suffix (``dusk_1.toml``) unless ``force`` is
    true, which overwrites the base name.

    Args:
        name: The theme name. A ``.toml`` suffix and any parent path are
            stripped.
        config: Config to use. Defaults to the config for ``project_root`` or
            the current working directory.
        themes_dir: Output directory. Defaults to the project's configured
            theme directory.
        templates_dir: Directory containing ``theme.toml.j2``. Defaults to the
            project's configured templates directory.
        project_root: Directory used to discover the project config.
        force: Overwrite an existing theme file instead of adding a suffix.

    Returns:
        The path of the theme file that was written.

    Raises:
        ScaffoldError: When the name is empty.
    """
    resolved = _resolve_config(config, project_root)
    project_paths = resolved.get_project_paths()
    target_dir = _resolve_dir(themes_dir, project_paths["themes_dir"])
    template_dir = _resolve_dir(templates_dir, project_paths["templates_dir"])
    target_file = _theme_target(target_dir, name, force)

    template = Template(_select_template(template_dir, _THEME_TEMPLATE).read_text())
    rendered_content = template.render()

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(rendered_content)
    return target_file


def make_skill(
    name: str,
    description: str = "",
    *,
    config: ConfigManager | None = None,
    skills_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    project_root: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Create a bundled Agent Skill and return its ``SKILL.md`` path.

    Args:
        name: The skill name in lowercase-hyphen form.
        description: Short description for the skill frontmatter. When empty,
            a description is generated from the skill and CLI names.
        config: Config to use. Defaults to the config for ``project_root`` or
            the current working directory.
        skills_dir: Bundled skills directory. Defaults to the project's
            configured skills directory.
        templates_dir: Directory containing ``project_skill.md.j2``. Defaults
            to the project's configured templates directory.
        project_root: Directory used to discover the project config.
        force: Overwrite an existing skill instead of raising
            :class:`ScaffoldError`.

    Returns:
        The path of the ``SKILL.md`` file that was written.

    Raises:
        ScaffoldError: When the name is invalid or the skill already exists and
            ``force`` is false.
    """
    try:
        validate_skill_name(name)
    except UsecliBadParameter as error:
        raise ScaffoldError(str(error)) from error

    resolved = _resolve_config(config, project_root)
    skill_root = _resolve_dir(skills_dir, resolved.get_project_skills_dir())
    template_dir = _resolve_dir(templates_dir, resolved.get_project_templates_dir())

    target_file = skill_root / name / "SKILL.md"
    if target_file.exists() and not force:
        raise ScaffoldError(f"Skill {target_file} already exists.")

    command_name = resolved.get("command_name") or DEFAULT_COMMAND_NAME
    command_name = " ".join(str(command_name).split()) or DEFAULT_COMMAND_NAME
    description = _frontmatter_description(
        description or f"Use the {name} skill with the {command_name} CLI."
    )

    template = Template(
        _select_template(template_dir, _SKILL_TEMPLATE).read_text(encoding="utf-8"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    content = template.render(
        name=name,
        description=description,
        command_name=command_name,
    )

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")
    return target_file


def _ask(prompt: str, *, default: str | None = None) -> str:
    """Ask for a text value through usecli's prompt wrapper."""
    from usecli.ui import Prompt

    value = Prompt.ask(prompt, default=default)
    return "" if value is None else str(value)


def prompt_make_command(
    name: str | None = None,
    *,
    config: ConfigManager | None = None,
    commands_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    project_root: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Prompt for a command name, then create the command module.

    Pass ``name`` to skip the prompt. In JSON mode, omitting ``name`` raises
    :class:`~usecli.cli.core.runtime.NonInteractiveError`.
    """
    if name is None:
        name = _ask("Command name")
    return make_command(
        name,
        config=config,
        commands_dir=commands_dir,
        templates_dir=templates_dir,
        project_root=project_root,
        force=force,
    )


def prompt_make_theme(
    name: str | None = None,
    *,
    config: ConfigManager | None = None,
    themes_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    project_root: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Prompt for a theme name, then create the theme file.

    Pass ``name`` to skip the prompt. In JSON mode, omitting ``name`` raises
    :class:`~usecli.cli.core.runtime.NonInteractiveError`.
    """
    if name is None:
        name = _ask("Theme name")
    return make_theme(
        name,
        config=config,
        themes_dir=themes_dir,
        templates_dir=templates_dir,
        project_root=project_root,
        force=force,
    )


def prompt_make_skill(
    name: str | None = None,
    description: str | None = None,
    *,
    config: ConfigManager | None = None,
    skills_dir: str | Path | None = None,
    templates_dir: str | Path | None = None,
    project_root: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Prompt for a skill name and description, then create the skill.

    Pass ``name`` and ``description`` to skip their prompts. In JSON mode,
    omitting ``name`` raises
    :class:`~usecli.cli.core.runtime.NonInteractiveError`.
    """
    if name is None:
        name = _ask("Skill name (lowercase-with-hyphens)")
    if description is None:
        description = _ask("Description (optional)", default="")
    return make_skill(
        name,
        description,
        config=config,
        skills_dir=skills_dir,
        templates_dir=templates_dir,
        project_root=project_root,
        force=force,
    )


__all__ = [
    "ScaffoldError",
    "make_command",
    "make_skill",
    "make_theme",
    "prompt_make_command",
    "prompt_make_skill",
    "prompt_make_theme",
]
