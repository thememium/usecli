# Changelog


## v0.1.41

[compare changes](https://github.com/thememium/usecli/compare/v0.1.40...v0.1.41)

### 🚀 Enhancements

- **about:** Include primary script command in About output ([def27da](https://github.com/thememium/usecli/commit/def27da))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.40

[compare changes](https://github.com/thememium/usecli/compare/v0.1.39...v0.1.40)

### 💅 Refactors

- **cli:** Retrieve script command name using explicit cwd ([04ab51a](https://github.com/thememium/usecli/commit/04ab51a))

### 🏡 Chore

- **usecli:** Deduplicate command_name and move it before title for proper config parsing ([349d614](https://github.com/thememium/usecli/commit/349d614))
- **pyproject:** Add `--fix` flag to ruff check in clean‑full task ([b6cf9d1](https://github.com/thememium/usecli/commit/b6cf9d1))

### 🎨 Styles

- **usecli:** Reorder command_name key in config template ([5b536c3](https://github.com/thememium/usecli/commit/5b536c3))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.39

[compare changes](https://github.com/thememium/usecli/compare/v0.1.38...v0.1.39)

### 🚀 Enhancements

- **config:** Add `command_name` option to CLI configuration ([f3b475a](https://github.com/thememium/usecli/commit/f3b475a))
- **init_command.py:** Include command_name when creating usecli configuration ([4566b0b](https://github.com/thememium/usecli/commit/4566b0b))

### ✅ Tests

- **cli:** Add assertions for command_name in generated pyproject.toml ([3abda08](https://github.com/thememium/usecli/commit/3abda08))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.38

[compare changes](https://github.com/thememium/usecli/compare/v0.1.37...v0.1.38)

### 🚀 Enhancements

- **cli:** Resolve pyproject path via ConfigManager when present ([9daa980](https://github.com/thememium/usecli/commit/9daa980))

### 💅 Refactors

- **usecli.config.toml:** Update command, template, and theme directories to relative paths ([1f8b413](https://github.com/thememium/usecli/commit/1f8b413))
- **init:** Generate relative paths for config directories ([064beed](https://github.com/thememium/usecli/commit/064beed))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.37

[compare changes](https://github.com/thememium/usecli/compare/v0.1.36...v0.1.37)

### 🚀 Enhancements

- **usecli:** Add default configuration file for the CLI tool ([68a0174](https://github.com/thememium/usecli/commit/68a0174))
- **config:** Add console‑script discovery and improve config precedence ([ecef67e](https://github.com/thememium/usecli/commit/ecef67e))

### 🩹 Fixes

- **config:** Prevent locating package config when outside UseCLI package ([25fdc36](https://github.com/thememium/usecli/commit/25fdc36))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.36

[compare changes](https://github.com/thememium/usecli/compare/v0.1.35...v0.1.36)

### 🚀 Enhancements

- **config:** Detect usecli config in package and prefer it over project config ([a3cdf4a](https://github.com/thememium/usecli/commit/a3cdf4a))
- **colors:** Add package config discovery and venv exclusion ([d6eec7b](https://github.com/thememium/usecli/commit/d6eec7b))

### ❤️ Contributors

- Edward Boswell <thememium@gmail.com>

## v0.1.35

[compare changes](https://github.com/thememium/usecli/compare/v0.1.34...v0.1.35)

### 🚀 Enhancements

- **config:** Ignore virtual environment directories when searching config files ([2a2dba0](https://github.com/thememium/usecli/commit/2a2dba0))
- **init_command:** Let user choose config file location and resolve path ([a7db952](https://github.com/thememium/usecli/commit/a7db952))

### 🩹 Fixes

- **config:** Skip venv and .venv when searching for config ([180eb29](https://github.com/thememium/usecli/commit/180eb29))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.34

[compare changes](https://github.com/thememium/usecli/compare/v0.1.33...v0.1.34)

### 🚀 Enhancements

- **usecli:** Add Jinja2 template for usecli.config.toml ([5230c68](https://github.com/thememium/usecli/commit/5230c68))
- **config:** Support usecli.config.toml and enhance config discovery ([d8c2ab1](https://github.com/thememium/usecli/commit/d8c2ab1))
- **usecli:** Add default configuration file for CLI ([d68e14a](https://github.com/thememium/usecli/commit/d68e14a))
- **cli:** Store usecli configuration in its own TOML file ([8076c73](https://github.com/thememium/usecli/commit/8076c73))
- **config:** Rename config file to usecli.config.toml and add nested support ([27398ee](https://github.com/thememium/usecli/commit/27398ee))

### 🩹 Fixes

- **tests:** Update resource path to renamed template file ([7cc3bfc](https://github.com/thememium/usecli/commit/7cc3bfc))

### 💅 Refactors

- **init:** Rename config file to usecli.config.toml and simplify init flow ([5c5824f](https://github.com/thememium/usecli/commit/5c5824f))
- **globals.py:** Rename configuration constant to match filename ([4a444bb](https://github.com/thememium/usecli/commit/4a444bb))
- **config:** Rename usecli.toml to usecli.config.toml and update discovery logic ([ce9e319](https://github.com/thememium/usecli/commit/ce9e319))

### 🏡 Chore

- Move usecli config out of pyproject and update README ([1429e30](https://github.com/thememium/usecli/commit/1429e30))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.33

[compare changes](https://github.com/thememium/usecli/compare/v0.1.32...v0.1.33)

### 🚀 Enhancements

- **config:** Add usecli.toml fallback support ([a9eaafd](https://github.com/thememium/usecli/commit/a9eaafd))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.32

[compare changes](https://github.com/thememium/usecli/compare/v0.1.31...v0.1.32)

### 🚀 Enhancements

- **cli:** Add group alias resolution to fzf command ([afd2f18](https://github.com/thememium/usecli/commit/afd2f18))
- **cli:** Add group alias support for nested commands and UI ([c526026](https://github.com/thememium/usecli/commit/c526026))
- **cli:** Add group alias support to PrefixMatchingGroup ([2455c85](https://github.com/thememium/usecli/commit/2455c85))

### ✅ Tests

- **cli:** Add tests for nested command aliases and group alias listing ([cd13bd8](https://github.com/thememium/usecli/commit/cd13bd8))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.31

[compare changes](https://github.com/thememium/usecli/compare/v0.1.30...v0.1.31)

### 🚀 Enhancements

- **cli:** Add command alias support and UI enhancements ([2c33dce](https://github.com/thememium/usecli/commit/2c33dce))
- **cli:** Add aliases method to command template ([a66e671](https://github.com/thememium/usecli/commit/a66e671))
- **ui/list:** Centralize option description handling and add custom text for --show-completion ([0bcaaeb](https://github.com/thememium/usecli/commit/0bcaaeb))

### 💅 Refactors

- **cli:** Unify spacing logic for list command output ([fbf457d](https://github.com/thememium/usecli/commit/fbf457d))
- **list.py:** Order completion flags consistently for better UI ([b3acf00](https://github.com/thememium/usecli/commit/b3acf00))

### 📖 Documentation

- **usecli:** Add trailing period to interactive mode help messages ([f3ec46f](https://github.com/thememium/usecli/commit/f3ec46f))

### ✅ Tests

- **cli:** Add comprehensive tests for command aliases and improve BaseCommand references ([887b2d9](https://github.com/thememium/usecli/commit/887b2d9))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.30

[compare changes](https://github.com/thememium/usecli/compare/v0.1.29...v0.1.30)

### 🚀 Enhancements

- **cli:** Use dynamic script command name in usage and error messages ([b532635](https://github.com/thememium/usecli/commit/b532635))

### 📖 Documentation

- **readme:** Update install instructions to recommend uv and add pip alternative ([318ccc0](https://github.com/thememium/usecli/commit/318ccc0))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.29

[compare changes](https://github.com/thememium/usecli/compare/v0.1.28...v0.1.29)

### 🚀 Enhancements

- **cli:** Make Typer help text configurable via project config ([62bf895](https://github.com/thememium/usecli/commit/62bf895))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.28

[compare changes](https://github.com/thememium/usecli/compare/v0.1.27...v0.1.28)

### 🚀 Enhancements

- **cli:** Add Nord theme configuration ([dc21539](https://github.com/thememium/usecli/commit/dc21539))
- **cli:** Add gruvbox_dark theme configuration ([848a2a0](https://github.com/thememium/usecli/commit/848a2a0))
- **theme:** Add Dracula theme configuration ([75073ce](https://github.com/thememium/usecli/commit/75073ce))
- **init_command:** Add interactive theme selection with preview and config rendering ([722083d](https://github.com/thememium/usecli/commit/722083d))
- **init:** Enhance init command prompts and streamline pyproject template ([ff20721](https://github.com/thememium/usecli/commit/ff20721))
- **cli:** Replace section headers with console.rule for clearer UI ([27d1548](https://github.com/thememium/usecli/commit/27d1548))
- **cli:** Add explanatory hints to init prompts ([035b268](https://github.com/thememium/usecli/commit/035b268))

### 💅 Refactors

- **init:** Prioritize default theme and dedupe prompt ([430813e](https://github.com/thememium/usecli/commit/430813e))

### 📖 Documentation

- **themes:** Add semantic sections and inline comments to theme files ([34ada09](https://github.com/thememium/usecli/commit/34ada09))

### 🎨 Styles

- **themes:** Update color palette for several CLI themes ([075597d](https://github.com/thememium/usecli/commit/075597d))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.27

[compare changes](https://github.com/thememium/usecli/compare/v0.1.26...v0.1.27)

### 🚀 Enhancements

- **usecli:** Expose colors module and use theme constants in CLI templates ([427df74](https://github.com/thememium/usecli/commit/427df74))

### 🎨 Styles

- **command.py.j2:** Split long console.print statements across lines for readability ([afd38bf](https://github.com/thememium/usecli/commit/afd38bf))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.26

[compare changes](https://github.com/thememium/usecli/compare/v0.1.25...v0.1.26)

### 🚀 Enhancements

- **cli:** Parse dependency specifiers and show them in `about` output ([578d591](https://github.com/thememium/usecli/commit/578d591))
- **cli:** Add optional packaging.requirements parser for dependency parsing ([66bd7e8](https://github.com/thememium/usecli/commit/66bd7e8))

### 💅 Refactors

- **about_command:** Remove unused packaging parser and related imports ([4ac0259](https://github.com/thememium/usecli/commit/4ac0259))

### 📖 Documentation

- **readme:** Improve project description for better clarity ([ffee54b](https://github.com/thememium/usecli/commit/ffee54b))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.25

[compare changes](https://github.com/thememium/usecli/compare/v0.1.24...v0.1.25)

### 🏡 Chore

- **release.sh:** Add uv lock step, include uv.lock in commit, push tag separately, make release idempotent ([9d75a29](https://github.com/thememium/usecli/commit/9d75a29))
- **release:** Add uv sync step after version bump ([48ad3a2](https://github.com/thememium/usecli/commit/48ad3a2))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.24

[compare changes](https://github.com/thememium/usecli/compare/v0.1.23...v0.1.24)

### 🚀 Enhancements

- **scripts/release.sh:** Generate GitHub release notes from CHANGELOG ([78aad58](https://github.com/thememium/usecli/commit/78aad58))

### 🏡 Chore

- **uv:** Update version ([77993f9](https://github.com/thememium/usecli/commit/77993f9))
- **release:** Bump version, tag and create GitHub release ([4860d57](https://github.com/thememium/usecli/commit/4860d57))

### 🎨 Styles

- **tests:** Reorder Confirm import to top‑level import block ([f867ed5](https://github.com/thememium/usecli/commit/f867ed5))

### 🤖 CI

- **publish.yml:** Add Python 3.10 installation step ([83ad623](https://github.com/thememium/usecli/commit/83ad623))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.23

[compare changes](https://github.com/thememium/usecli/compare/v0.1.22...v0.1.23)

### 🏡 Chore

- **uv:** Update version ([5393123](https://github.com/thememium/usecli/commit/5393123))

### 🤖 CI

- **publish:** Trigger on release published and verify version matches tag ([bf22c13](https://github.com/thememium/usecli/commit/bf22c13))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.22

[compare changes](https://github.com/thememium/usecli/compare/v0.1.21...v0.1.22)

### 📖 Documentation

- **readme:** Clarify installation and usage instructions ([3ba6b63](https://github.com/thememium/usecli/commit/3ba6b63))
- **readme:** Update guide links to absolute URLs ([f204ad8](https://github.com/thememium/usecli/commit/f204ad8))

### 🏡 Chore

- **uv:** Update version ([3057b46](https://github.com/thememium/usecli/commit/3057b46))

### ✅ Tests

- **tests:** Add smoke test suite for basic package validation ([d339975](https://github.com/thememium/usecli/commit/d339975))

### 🎨 Styles

- **tests:** Relocate PLC0415 noqa comment to Confirm import line ([f9532d1](https://github.com/thememium/usecli/commit/f9532d1))

### 🤖 CI

- **publish:** Add GitHub Actions workflow to publish package on version tags ([23ce721](https://github.com/thememium/usecli/commit/23ce721))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.21

[compare changes](https://github.com/thememium/usecli/compare/v0.1.20...v0.1.21)

### 📖 Documentation

- Add dark‑background logo image for usecli documentation ([9f58deb](https://github.com/thememium/usecli/commit/9f58deb))
- **readme:** Replace logo with dark‑background version for better contrast ([42ee144](https://github.com/thememium/usecli/commit/42ee144))
- **readme:** Replace logo image URL with absolute raw.githubusercontent.com link ([fe7ec0f](https://github.com/thememium/usecli/commit/fe7ec0f))
- **readme:** Update logo image URL to point to master branch ([7ce1b09](https://github.com/thememium/usecli/commit/7ce1b09))

### 🏡 Chore

- **uv:** Update version ([40667a7](https://github.com/thememium/usecli/commit/40667a7))
- **gitignore:** Add .DS_Store to ignore list ([9867b38](https://github.com/thememium/usecli/commit/9867b38))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.20

[compare changes](https://github.com/thememium/usecli/compare/v0.1.19...v0.1.20)

### 🏡 Chore

- **uv:** Update version ([5b2739c](https://github.com/thememium/usecli/commit/5b2739c))
- **pyproject:** Remove testpypi UV index configuration ([11a035c](https://github.com/thememium/usecli/commit/11a035c))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.19

[compare changes](https://github.com/thememium/usecli/compare/v0.1.18...v0.1.19)

### 📖 Documentation

- **pyproject:** Update description and add documentation URLs ([4d16fb8](https://github.com/thememium/usecli/commit/4d16fb8))

### 📦 Build

- **pyproject:** Add `uv build --no-sources` script ([0c63bcf](https://github.com/thememium/usecli/commit/0c63bcf))

### 🏡 Chore

- **uv:** Update version ([fe75676](https://github.com/thememium/usecli/commit/fe75676))
- **pyproject:** Remove Development Status :: 3 - Alpha classifier ([aa726ec](https://github.com/thememium/usecli/commit/aa726ec))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.18

[compare changes](https://github.com/thememium/usecli/compare/v0.1.17...v0.1.18)

### 🚀 Enhancements

- **colors:** Add dynamic theming support with TOML theme files ([731d1da](https://github.com/thememium/usecli/commit/731d1da))
- **usecli:** Add Catppuccin theme files (frappe, latte, macchiato, mocha) ([9c592a7](https://github.com/thememium/usecli/commit/9c592a7))
- **colors:** Generate ANSI palette from hex colors ([fd5767f](https://github.com/thememium/usecli/commit/fd5767f))
- **themes:** Add semantic color sections and UI semantics to themes ([7c7926e](https://github.com/thememium/usecli/commit/7c7926e))
- **cli:** Add ayu_dark theme configuration ([82a006e](https://github.com/thememium/usecli/commit/82a006e))
- **cli:** Add Tokyo Night theme configuration ([a3f9d8f](https://github.com/thememium/usecli/commit/a3f9d8f))
- **pyproject:** Add custom CLI configuration options ([1ced60d](https://github.com/thememium/usecli/commit/1ced60d))
- **pyproject:** Add themes_dir configuration for custom CLI themes ([7dd7f48](https://github.com/thememium/usecli/commit/7dd7f48))
- **cli:** Add themes directory handling to init command and config ([7a77db0](https://github.com/thememium/usecli/commit/7a77db0))
- **usecli:** Add theme.toml.j2 template with default color scheme ([bcc42d2](https://github.com/thememium/usecli/commit/bcc42d2))
- **make:theme:** Add CLI command to generate theme configuration files ([3994f66](https://github.com/thememium/usecli/commit/3994f66))
- **make-theme:** Add hide_make_theme config to control command visibility ([4e5b055](https://github.com/thememium/usecli/commit/4e5b055))

### 🩹 Fixes

- **init_command:** Preserve blank line before project.scripts on replace ([43f9c99](https://github.com/thememium/usecli/commit/43f9c99))

### 💅 Refactors

- **themes:** Drop unused ansi colour mappings from all theme files ([d324466](https://github.com/thememium/usecli/commit/d324466))
- **cli:** Deduplicate command listings and prevent duplicate command loading ([7d27ff4](https://github.com/thememium/usecli/commit/7d27ff4))

### 🏡 Chore

- **uv:** Update version ([b0990e4](https://github.com/thememium/usecli/commit/b0990e4))
- **pyproject.toml:** Add usecli configuration with default theme ([1797f98](https://github.com/thememium/usecli/commit/1797f98))

### ✅ Tests

- **cli:** Add comprehensive tests for command listing and loading ([3315c85](https://github.com/thememium/usecli/commit/3315c85))

### 🎨 Styles

- **theme:** Update Catppuccin Frappe color palette ([b948773](https://github.com/thememium/usecli/commit/b948773))
- **theme:** Update Catppuccin Latte palette ([9ddecdb](https://github.com/thememium/usecli/commit/9ddecdb))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.17

[compare changes](https://github.com/thememium/usecli/compare/v0.1.16...v0.1.17)

### 🚀 Enhancements

- **cli:** Add support for configurable title_file ([717acc5](https://github.com/thememium/usecli/commit/717acc5))
- **init_command:** Generate full pyproject.toml and auto‑sync environment ([65b8184](https://github.com/thememium/usecli/commit/65b8184))
- **init:** Store usecli configuration in pyproject.toml instead of a separate file ([5f37dfa](https://github.com/thememium/usecli/commit/5f37dfa))
- **init-command:** Extract env sync logic and use folder name for project ([8908772](https://github.com/thememium/usecli/commit/8908772))

### 🩹 Fixes

- **pyproject:** Update console script entry point to usecli:main ([936bd39](https://github.com/thememium/usecli/commit/936bd39))

### 💅 Refactors

- **config:** Drop usecli.config.toml support and rely on pyproject.toml only ([acc3213](https://github.com/thememium/usecli/commit/acc3213))
- **init:** Check for uv before .venv existence ([e8e96af](https://github.com/thememium/usecli/commit/e8e96af))
- **cli:** Rename run_app to main and update public API ([d396b45](https://github.com/thememium/usecli/commit/d396b45))

### 📖 Documentation

- **readme:** Rename “Key Features” to “Features”, add new TOC items, and expand sections ([b918ce3](https://github.com/thememium/usecli/commit/b918ce3))
- Extract Development section to docs/development.md and simplify README ([29fd224](https://github.com/thememium/usecli/commit/29fd224))
- **readme:** Simplify README, update quick‑start and usage sections ([e088ef2](https://github.com/thememium/usecli/commit/e088ef2))

### 🏡 Chore

- **uv:** Update version ([82694d3](https://github.com/thememium/usecli/commit/82694d3))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.16

[compare changes](https://github.com/thememium/usecli/compare/v0.1.15...v0.1.16)

### 🚀 Enhancements

- **init:** Infer command name and title from pyproject name ([1a35afd](https://github.com/thememium/usecli/commit/1a35afd))

### 🏡 Chore

- **uv:** Update version ([e86e576](https://github.com/thememium/usecli/commit/e86e576))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.15

[compare changes](https://github.com/thememium/usecli/compare/v0.1.14...v0.1.15)

### 🚀 Enhancements

- **command_service:** Prefer config version over package metadata ([3ba132c](https://github.com/thememium/usecli/commit/3ba132c))
- **cli:** Make about command use project config for name, version, description ([fb3d764](https://github.com/thememium/usecli/commit/fb3d764))
- **cli:** Read project dependencies from pyproject.toml via ConfigManager ([5bdec7e](https://github.com/thememium/usecli/commit/5bdec7e))

### 🏡 Chore

- **uv:** Update version ([0666e62](https://github.com/thememium/usecli/commit/0666e62))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.14

[compare changes](https://github.com/thememium/usecli/compare/v0.1.13...v0.1.14)

### 🚀 Enhancements

- **cli:** Support project‑specific command templates ([b9e3755](https://github.com/thememium/usecli/commit/b9e3755))
- **cli:** Resolve init command paths relative to project root ([46b780d](https://github.com/thememium/usecli/commit/46b780d))
- **init_command:** Prompt user for templates directory ([300c44a](https://github.com/thememium/usecli/commit/300c44a))
- **terminal_menu:** Add Vim‑style page navigation keys ([698ff6c](https://github.com/thememium/usecli/commit/698ff6c))
- **cli:** Add J/K navigation keys and update status bar hints ([921c738](https://github.com/thememium/usecli/commit/921c738))

### 🏡 Chore

- **uv:** Update version ([f4a559a](https://github.com/thememium/usecli/commit/f4a559a))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.13

[compare changes](https://github.com/thememium/usecli/compare/v0.1.12...v0.1.13)

### 🚀 Enhancements

- **config:** Add dynamic project root and commands directory resolution ([efbaee9](https://github.com/thememium/usecli/commit/efbaee9))
- **config:** Support hierarchical script command lookup and config overrides ([593628e](https://github.com/thememium/usecli/commit/593628e))

### 🏡 Chore

- **uv:** Update version ([61e5b30](https://github.com/thememium/usecli/commit/61e5b30))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.12

[compare changes](https://github.com/thememium/usecli/compare/v0.1.11...v0.1.12)

### 🚀 Enhancements

- **cli:** Add hidden flag support for default commands ([d8f8803](https://github.com/thememium/usecli/commit/d8f8803))
- **cli:** Add hide_init, hide_inspire and hide_make_command config options ([1e693a8](https://github.com/thememium/usecli/commit/1e693a8))

### 💅 Refactors

- **about_command:** Comment out Features section in AboutCommand output ([3a4c173](https://github.com/thememium/usecli/commit/3a4c173))

### 📖 Documentation

- **readme:** Add “Hide Default Commands” section ([e1d6cdb](https://github.com/thememium/usecli/commit/e1d6cdb))

### 🏡 Chore

- **uv:** Update version ([e88f232](https://github.com/thememium/usecli/commit/e88f232))

### ✅ Tests

- **cli:** Assert new hide_* defaults in init command output ([399c8d7](https://github.com/thememium/usecli/commit/399c8d7))

### 🎨 Styles

- **init:** Indent figlet title output for better visual alignment ([decda35](https://github.com/thememium/usecli/commit/decda35))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.11

[compare changes](https://github.com/thememium/usecli/compare/v0.1.10...v0.1.11)

### 🚀 Enhancements

- **ui:** Add blank line before title output for better readability ([6a11d61](https://github.com/thememium/usecli/commit/6a11d61))
- **cli:** Default title uses command name when placeholder is generic ([57d1ca9](https://github.com/thememium/usecli/commit/57d1ca9))
- **usecli:** Read project name from config before falling back to metadata ([bd90a3d](https://github.com/thememium/usecli/commit/bd90a3d))
- **usecli:** Detect interactive flag in any argv position ([1cbcaec](https://github.com/thememium/usecli/commit/1cbcaec))

### 🏡 Chore

- **uv:** Update version ([fcf14a4](https://github.com/thememium/usecli/commit/fcf14a4))

### 🎨 Styles

- **title.py:** Indent each line of the rendered title for improved readability ([0fd9b20](https://github.com/thememium/usecli/commit/0fd9b20))
- **cli:** Remove unnecessary f‑string from command template ([bd23f2e](https://github.com/thememium/usecli/commit/bd23f2e))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.10

[compare changes](https://github.com/thememium/usecli/compare/v0.1.9...v0.1.10)

### 🚀 Enhancements

- **cli:** Enhance init command title font selection and preview ([5863e35](https://github.com/thememium/usecli/commit/5863e35))
- **init:** Add search hint to status bar in init command ([4d46e93](https://github.com/thememium/usecli/commit/4d46e93))

### 🩹 Fixes

- **template:** Remove duplicate title_font entry and place it after title ([45956f0](https://github.com/thememium/usecli/commit/45956f0))

### 📖 Documentation

- **readme:** Improve command example with arguments and prompts ([58c7bfa](https://github.com/thememium/usecli/commit/58c7bfa))

### 🏡 Chore

- **uv:** Update version ([fe04671](https://github.com/thememium/usecli/commit/fe04671))

### 🎨 Styles

- **list:** Remove bold styling from command names in UI output ([3c50a5c](https://github.com/thememium/usecli/commit/3c50a5c))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.9

[compare changes](https://github.com/thememium/usecli/compare/v0.1.8...v0.1.9)

### 🚀 Enhancements

- **cli:** Add configurable figlet title font ([9f93051](https://github.com/thememium/usecli/commit/9f93051))
- **terminal_menu:** Add search, status bar, and preview support ([6e700a2](https://github.com/thememium/usecli/commit/6e700a2))
- **cli:** Add safe search length handling and dynamic preview sizing to terminal_menu ([c67dd17](https://github.com/thememium/usecli/commit/c67dd17))
- **init_command:** Replace Menu with terminal_menu for richer interactive UI ([7517482](https://github.com/thememium/usecli/commit/7517482))
- **init_command:** Show font selection prompt and echo chosen font ([c4ae7d9](https://github.com/thememium/usecli/commit/c4ae7d9))

### 📖 Documentation

- **readme:** Add “Create Your Own CLI” guide and document `init` command ([a5a98b5](https://github.com/thememium/usecli/commit/a5a98b5))

### 🏡 Chore

- **uv:** Update version ([f3e666b](https://github.com/thememium/usecli/commit/f3e666b))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.8

[compare changes](https://github.com/thememium/usecli/compare/v0.1.7...v0.1.8)

### 🚀 Enhancements

- **cli:** Enable interspersed arguments in custom help command ([90ae906](https://github.com/thememium/usecli/commit/90ae906))

### 🏡 Chore

- **uv:** Update version ([f3e70b4](https://github.com/thememium/usecli/commit/f3e70b4))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.7

[compare changes](https://github.com/thememium/usecli/compare/v0.1.6...v0.1.7)

### 🚀 Enhancements

- **cli:** Expose core UI components and refactor command template ([3e1c357](https://github.com/thememium/usecli/commit/3e1c357))
- **menu:** Add Menu wrapper for terminal_menu utility ([05af0ab](https://github.com/thememium/usecli/commit/05af0ab))
- **usecli:** Add Argument and Option wrappers for typer parameters ([c56bb7b](https://github.com/thememium/usecli/commit/c56bb7b))
- **usecli:** Add UI component wrappers for Rich ([186d6aa](https://github.com/thememium/usecli/commit/186d6aa))
- **cli:** Add interactive prompts and rich console output to command template ([9d4e568](https://github.com/thememium/usecli/commit/9d4e568))
- **cli:** Add interactive prompts for missing boolean flags ([b2d25f6](https://github.com/thememium/usecli/commit/b2d25f6))
- **fzf_command:** Replace hard‑coded “usecli” with dynamic script name ([a9c45d0](https://github.com/thememium/usecli/commit/a9c45d0))
- **about:** Display script commands from pyproject.toml ([191dd81](https://github.com/thememium/usecli/commit/191dd81))

### 💅 Refactors

- **cli:** Improve option handling and remove interactive wrapper ([fc0afc2](https://github.com/thememium/usecli/commit/fc0afc2))
- **cli:** Skip interactive flags in optional options and drop unused Confirm import ([bb67c63](https://github.com/thememium/usecli/commit/bb67c63))

### 🏡 Chore

- **uv:** Update version ([9fca435](https://github.com/thememium/usecli/commit/9fca435))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.6

[compare changes](https://github.com/thememium/usecli/compare/v0.1.5...v0.1.6)

### 🚀 Enhancements

- **cli:** Add interactive fzf command for command discovery ([6650412](https://github.com/thememium/usecli/commit/6650412))
- **init:** Add automatic management of [project.scripts] in pyproject.toml ([d269813](https://github.com/thememium/usecli/commit/d269813))
- **cli:** Allow custom command name for entry point ([33c198c](https://github.com/thememium/usecli/commit/33c198c))
- **cli:** Add interactive prompting for init command parameters and validation ([1fefcd8](https://github.com/thememium/usecli/commit/1fefcd8))
- **init_command:** Detect existing usecli script in pyproject.toml and reuse it ([10cce33](https://github.com/thememium/usecli/commit/10cce33))

### 🩹 Fixes

- **test:** Update patch target for run_interactive after module relocation ([e9abc6f](https://github.com/thememium/usecli/commit/e9abc6f))

### 💅 Refactors

- **cli:** Update fzf_command import path to internal module ([9a130dd](https://github.com/thememium/usecli/commit/9a130dd))
- **usecli:** Relocate fzf command to internal package and skip internal modules ([3f39087](https://github.com/thememium/usecli/commit/3f39087))
- **config:** Remove deprecated `show_setup` option from config and tests ([2ce6409](https://github.com/thememium/usecli/commit/2ce6409))

### 📖 Documentation

- **readme:** Rename Interactive FZF to Interactive Mode and remove FZF references ([dc53631](https://github.com/thememium/usecli/commit/dc53631))
- **pyproject, cli:** Update project description and CLI help text for clarity ([0302658](https://github.com/thememium/usecli/commit/0302658))

### 🏡 Chore

- **uv:** Update version ([a26113a](https://github.com/thememium/usecli/commit/a26113a))

### ✅ Tests

- **cli:** Mock Prompt.ask in InitCommand fixture to avoid interactive prompts ([f7ad1a3](https://github.com/thememium/usecli/commit/f7ad1a3))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.5

[compare changes](https://github.com/thememium/usecli/compare/v0.1.4...v0.1.5)

### 🚀 Enhancements

- **init_command:** Add automatic build‑system section and uv environment sync ([ef12db5](https://github.com/thememium/usecli/commit/ef12db5))
- **cli/ui:** Infer project name from pyproject scripts ([caa8c47](https://github.com/thememium/usecli/commit/caa8c47))
- **config:** Set default commands_dir to "cli/commands" ([171f540](https://github.com/thememium/usecli/commit/171f540))
- **cli:** Add setuptools package discovery to pyproject.toml and improve build‑system insertion ([2064a3a](https://github.com/thememium/usecli/commit/2064a3a))
- **init_command:** Add automatic creation of __init__.py files ([79c787d](https://github.com/thememium/usecli/commit/79c787d))
- **fzf_command:** Add graceful fallback when fzf is unavailable or not a TTY ([1210cb2](https://github.com/thememium/usecli/commit/1210cb2))
- **usecli:** Add --interactive flag to run CLI in interactive mode ([93e00fa](https://github.com/thememium/usecli/commit/93e00fa))
- **cli:** Display Typer group command options in list output ([8128dc8](https://github.com/thememium/usecli/commit/8128dc8))
- **cli:** Add interactive mode flag to commands and groups ([0f101bf](https://github.com/thememium/usecli/commit/0f101bf))

### 🩹 Fixes

- **base_command:** Ensure params attribute exists to prevent attribute errors ([3b5312f](https://github.com/thememium/usecli/commit/3b5312f))

### 💅 Refactors

- **cli:** Centralize script command name handling and drop legacy command_name option ([c1e9e9f](https://github.com/thememium/usecli/commit/c1e9e9f))
- **fzf_command:** Extract helper functions and simplify FzfCommand class ([1ad605e](https://github.com/thememium/usecli/commit/1ad605e))

### 🏡 Chore

- **uv:** Update version ([b438735](https://github.com/thememium/usecli/commit/b438735))

### ✅ Tests

- **cli:** Update default commands directory to cli/commands in tests ([e97e70b](https://github.com/thememium/usecli/commit/e97e70b))
- **cli:** Add unit tests for interactive option handling ([0f92a07](https://github.com/thememium/usecli/commit/0f92a07))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.4

[compare changes](https://github.com/thememium/usecli/compare/v0.1.3...v0.1.4)

### 🚀 Enhancements

- **init_command:** Add automatic [project.scripts] entry for custom command name ([0bafe99](https://github.com/thememium/usecli/commit/0bafe99))

### 🏡 Chore

- **uv:** Update version ([deee776](https://github.com/thememium/usecli/commit/deee776))

### ✅ Tests

- **init_command:** Adds project scripts tests ([08075dc](https://github.com/thememium/usecli/commit/08075dc))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.3

[compare changes](https://github.com/thememium/usecli/compare/v0.1.2...v0.1.3)

### 🚀 Enhancements

- **config:** Add usecli.toml Jinja2 template and simplify defaults ([35d57d6](https://github.com/thememium/usecli/commit/35d57d6))
- **cli:** Add InitCommand to initialise usecli projects and tests ([5bebf42](https://github.com/thememium/usecli/commit/5bebf42))
- **init:** Add interactive overwrite prompts and --force flag ([a78ecca](https://github.com/thememium/usecli/commit/a78ecca))
- **cli:** Add configurable command name option ([59e98d9](https://github.com/thememium/usecli/commit/59e98d9))

### 💅 Refactors

- **globals.py:** Rename config constants to file name constants and update docstring ([912cbab](https://github.com/thememium/usecli/commit/912cbab))
- **config:** Replace YAML global/local config with TOML project config ([73ebcdc](https://github.com/thememium/usecli/commit/73ebcdc))
- **init_command:** Use centralized color constants for console output ([b326ad4](https://github.com/thememium/usecli/commit/b326ad4))
- **tests:** Use keyword argument `force` for init_command.handle calls ([d978004](https://github.com/thememium/usecli/commit/d978004))

### 📖 Documentation

- **readme:** Increase logo height, lower Python version requirement, revise install guide ([d6dbb58](https://github.com/thememium/usecli/commit/d6dbb58))
- **readme:** Reduce logo image dimensions ([f2f8937](https://github.com/thememium/usecli/commit/f2f8937))

### 📦 Build

- **pyproject:** Add tomli dependency ([c3630d2](https://github.com/thememium/usecli/commit/c3630d2))

### 🏡 Chore

- **uv:** Update version ([4018d70](https://github.com/thememium/usecli/commit/4018d70))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.2

[compare changes](https://github.com/thememium/usecli/compare/v0.1.1...v0.1.2)

### 🏡 Chore

- **uv:** Update version ([0ddb579](https://github.com/thememium/usecli/commit/0ddb579))
- **pyproject:** Lower Python requirement from >=3.12 to >=3.10 ([58a7537](https://github.com/thememium/usecli/commit/58a7537))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

## v0.1.1


### 🚀 Enhancements

- **cli:** Load commands from project directory ([d0c5de8](https://github.com/thememium/usecli/commit/d0c5de8))

### 🩹 Fixes

- **title:** Make title comparison case‑insensitive ([7a3705c](https://github.com/thememium/usecli/commit/7a3705c))

### 💅 Refactors

- **title.py:** Normalize project name to “useCli” and simplify documentation ([9652b31](https://github.com/thememium/usecli/commit/9652b31))
- **make_command:** Use PROJECT_COMMANDS_DIR for generated commands and drop dev‑only visibility ([4340d34](https://github.com/thememium/usecli/commit/4340d34))
- **command_service:** Consolidate command loading to a single directory and update docstring ([028ed1d](https://github.com/thememium/usecli/commit/028ed1d))

### 📖 Documentation

- Add bug report issue template and contributing guide ([c12c840](https://github.com/thememium/usecli/commit/c12c840))
- **readme:** Add comprehensive project documentation ([8a93a1b](https://github.com/thememium/usecli/commit/8a93a1b))

### 🏡 Chore

- **scripts:** Add automated release script ([91b1ef3](https://github.com/thememium/usecli/commit/91b1ef3))

### ✅ Tests

- **conftest:** Add shared pytest fixtures for CLI tests ([e230715](https://github.com/thememium/usecli/commit/e230715))
- **config:** Add extensive ConfigManager unit tests ([2fb469d](https://github.com/thememium/usecli/commit/2fb469d))
- **cli:** Add comprehensive test suite for error handling, exceptions, and make command ([caaf1d7](https://github.com/thememium/usecli/commit/caaf1d7))
- **cli:** Update load_commands tests to assert three directory loads and rename test ([971655d](https://github.com/thememium/usecli/commit/971655d))
- **cli:** Simplify MakeCommand test suite ([a7ffd10](https://github.com/thememium/usecli/commit/a7ffd10))
- **cli:** Adjust load_commands tests for new commands directory layout ([acc236f](https://github.com/thememium/usecli/commit/acc236f))

### 🎨 Styles

- **title.py:** Add space around equality check in print_title ([32a9075](https://github.com/thememium/usecli/commit/32a9075))

### ❤️ Contributors

- Edward Boswell ([@thememium](https://github.com/thememium))

