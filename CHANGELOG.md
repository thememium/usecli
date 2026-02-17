# Changelog


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

