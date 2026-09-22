import dagger
from dagger import check, dag, function, object_type


@object_type
class Ci:
    """Checks for usecli, run by `dagger check` locally and by Dagger Cloud Checks on every push and PR."""

    source: dagger.Directory
    base_image_address: str

    @classmethod
    def create(
        cls,
        ws: dagger.Workspace,
        base_image_address: str = "ghcr.io/astral-sh/uv:python3.12-bookworm",
    ) -> "Ci":
        return cls(
            source=ws.directory(
                "/",
                exclude=[
                    "**/.dagger",
                    "**/.git",
                    "**/.venv",
                    "**/__pycache__",
                    "**/node_modules",
                    "**/dist",
                    "**/build",
                    "**/.ruff_cache",
                    "**/.pytest_cache",
                    "**/.coverage",
                    "**/.env",
                    "**/.auto",
                    "**/.omo",
                ],
            ),
            base_image_address=base_image_address,
        )

    def env(self) -> dagger.Container:
        """Project environment: source + locked dependencies, uv package cache persisted.

        Runs as uid 1001 (not root) so tests that depend on file permissions
        (e.g. unwritable-file handling) behave like they do on a real machine.
        """
        return (
            dag.container()
            .from_(self.base_image_address)
            .with_workdir("/app")
            .with_directory("/app", self.source, owner="1001")
            .with_mounted_cache("/home/app/.cache/uv", dag.cache_volume("uv"), owner="1001")
            .with_env_variable("UV_CACHE_DIR", "/home/app/.cache/uv")
            .with_user("1001")
            .with_exec(["uv", "sync", "--frozen"])
        )

    @function
    @check
    async def lint(self) -> str:
        """Run ruff checks (poe lint)."""
        return await self.env().with_exec(["uv", "run", "ruff", "check", "."]).stdout()

    @function
    @check
    async def sort(self) -> str:
        """Verify import ordering (poe sort, check-only)."""
        return await (
            self.env().with_exec(["uv", "run", "isort", "--check-only", "."]).stdout()
        )

    @function
    @check
    async def format(self) -> str:
        """Verify ruff formatting (poe format, check-only)."""
        return await (
            self.env().with_exec(["uv", "run", "ruff", "format", "--check", "."]).stdout()
        )

    @function
    @check
    async def deptry(self) -> str:
        """Verify dependencies are used and declared (poe deptry)."""
        return await self.env().with_exec(["uv", "run", "deptry", "."]).stdout()

    @function
    @check
    async def typecheck(self) -> str:
        """Run ty type checks (poe typecheck)."""
        return await self.env().with_exec(["uv", "run", "ty", "check"]).stdout()

    @function
    @check
    async def test(self) -> str:
        """Run the full test suite with coverage (poe test-cov)."""
        return await self.env().with_exec(["uv", "run", "poe", "test-cov"]).stdout()

    @function
    @check
    async def build(self) -> str:
        """Build the wheel and sdist (poe build)."""
        return await (
            self.env()
            .with_exec(["sh", "-c", "uv build --no-sources && ls dist"])
            .stdout()
        )