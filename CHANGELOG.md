# Changelog


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

