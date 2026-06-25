# Changelog

All notable user-facing changes are tracked here. Release downloads are published on the [GitHub Releases page](https://github.com/longweekendlabs/speech-bubble-editor/releases).

## v4.0.4 - 2026-06-25

### Added

- Cross-platform release packaging for Windows x64, Linux x64, macOS Intel, and macOS Apple Silicon.
- GitHub Actions release workflow that builds platform packages and attaches source archives.
- Video slow-down control with magnetic stops at 10%, 25%, 35%, 50%, 75%, and 100%.
- Video audio mute option for preview and export.
- Reset action for starting a fresh project without restarting the app.
- Keyboard Shortcuts dialog from the top-right toolbar.
- Caption style as a first-class bubble style in the inspector.
- Updated website with live release downloads and clearer platform sections.

### Changed

- Renamed the app to v4.0.4 across the app metadata, About dialog, website, and release assets.
- Overhauled the inspector layout to be more compact and stable.
- Reworked toolbar and bubble-style icons to use cleaner SVG artwork.
- Improved speech, rectangle, and starburst bubble geometry and tail behavior.
- Improved layer list controls and object ordering behavior.
- Switched file opening to native platform file dialogs where available.
- Updated README with current download, source, and build instructions.

### Fixed

- Fixed crashes when media loading cleared the inspector state.
- Fixed right inspector pane overflow and unnecessary horizontal scrolling.
- Fixed canvas background mismatches in meme and dual modes.
- Fixed accidental zoom changes from mouse-wheel focus on launch.
- Fixed missing video controls when opening video media as a layer.
- Fixed non-working alignment, arrange, layer up/down, and caption actions.
- Fixed font selection so installed/system fonts are listed and applied.
- Fixed stale theme-switcher UI left over from older app versions.
- Removed unintended Linux ARM and Windows ARM release assets from v4.0.4.

### Known Notes

- macOS builds are unsigned; first launch may require right-clicking the app and choosing **Open**.
- Windows and Linux builds are x64 only. Apple Silicon is provided for macOS only.

### Planned

- Signed/notarized macOS builds.
- Cleaner installer experience for Windows.
- More realistic comic bubble shapes and presets.
- Project save/load format for editable sessions.
- More automated UI smoke tests before releases.

## v4.0.3 - 2026-06-24

- Major v4 UI redesign with context toolbar, inspector updates, and expanded bubble styles.
- Early pass at SVG icons, theme cleanup, and canvas behavior fixes.

## v4.0.2 - 2026-06-24

- Release workflow preparation and v4 packaging fixes.

## v4.0.1 - 2026-06-24

- Restored missing installer configuration for release packaging.

## v4.0.0 - 2026-06-24

- Initial v4 release preparation.
- Integrated the v4 feature work from the phase-based development branch.
