"""Skill generator for OpenCode and Claude Code compatibility."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from typing import Any


class SkillGenerator:
    """Generates AI assistant skills for OpenCode and Claude Code."""

    SKILLS = [
        "usecli-new",
        "usecli-plan",
        "usecli-apply",
        "usecli-sync",
        "usecli-verify",
        "usecli-archive",
    ]

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialize the skill generator.

        Args:
            templates_dir: Directory containing Jinja2 templates.
                          Defaults to built-in templates.
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates" / "skills"

        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(),
        )
        self.env.filters["escape_yaml"] = self._escape_yaml
        self.env.filters["to_yaml"] = self._to_yaml

    def _escape_yaml(self, text: str) -> str:
        """Escape special YAML characters in text.

        Args:
            text: The text to escape.

        Returns:
            YAML-escaped text.
        """
        # Handle multi-line strings, quotes, special chars
        if "\n" in text or '"' in text or "'" in text or ":" in text:
            # Use literal block scalar for multi-line strings
            if "\n" in text:
                escaped = text.replace("\\", "\\\\")
                return f'"{escaped.replace(chr(34), chr(92) + chr(34))}"'
            # Escape quotes for single-line strings
            return f'"{text.replace(chr(34), chr(92) + chr(34))}"'
        return text

    def _to_yaml(self, obj: list[Any] | dict[str, Any]) -> str:
        """Convert object to YAML string.

        Args:
            obj: List or dictionary to convert.

        Returns:
            YAML-formatted string.
        """
        return yaml.dump(obj, default_flow_style=False).strip()

    def generate_skill(
        self,
        skill_name: str,
        target: str,
        context: dict[str, Any],
    ) -> str:
        """Generate a skill file for the specified target.

        Args:
            skill_name: Name of the skill (e.g., 'usecli-explore')
            target: Target platform ('opencode' or 'claude')
            context: Template variables

        Returns:
            Generated skill content as string

        Raises:
            ValueError: If target is not 'opencode' or 'claude'
            TemplateNotFound: If the skill template doesn't exist
        """
        if target not in ("opencode", "claude"):
            msg = f"Invalid target: {target}. Must be 'opencode' or 'claude'"
            raise ValueError(msg)

        template = self.env.get_template(f"{skill_name}/SKILL.md.j2")
        return template.render(target=target, **context)

    def generate_all_skills(
        self,
        target: str,
        output_dir: Path,
        version: str = "1.0.0",
        generated_by: str = "useCli",
    ) -> list[Path]:
        """Generate all skills for a target platform.

        Args:
            target: 'opencode' or 'claude'
            output_dir: Directory to write generated files
            version: Version string for metadata
            generated_by: Generator attribution string

        Returns:
            List of generated file paths

        Raises:
            ValueError: If target is not 'opencode' or 'claude'
        """
        if target not in ("opencode", "claude"):
            msg = f"Invalid target: {target}. Must be 'opencode' or 'claude'"
            raise ValueError(msg)

        generated = []
        context = {
            "version": version,
            "generated_by": generated_by,
        }

        for skill_name in self.SKILLS:
            content = self.generate_skill(
                skill_name=skill_name,
                target=target,
                context=context,
            )

            if target == "opencode":
                output_path = (
                    output_dir / ".opencode" / "skills" / skill_name / "SKILL.md"
                )
            else:  # claude
                output_path = (
                    output_dir / ".claude" / "skills" / skill_name / "SKILL.md"
                )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            generated.append(output_path)

        return generated
