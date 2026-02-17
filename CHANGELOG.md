# Changelog


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

