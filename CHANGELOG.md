# Changelog

All notable user-facing changes are tracked here. Release downloads are published on the [GitHub Releases page](https://github.com/longweekendlabs/speech-bubble-editor/releases).

## v4.5.1 - 2026-09-02

### Changed

- Reworked the editor chrome around a consistent blue-and-orange Night Desk theme with clearer surface hierarchy, spacing, contrast, and interaction states.
- Made the main workspace responsive with a resizable inspector, labelled and compact tool-rail modes, and top-bar controls that adapt at narrower window sizes.
- Unified the Shape, Text, FX, and Layers inspectors with matching introductions, section structure, control styling, and orange active states.
- Restyled the Layers tab with a proper layer stack, useful empty state, drag ordering, visibility controls, and integrated move actions while preserving all existing layer behavior.
- Refined the opening canvas with a focused speech-bubble composition card and direct open/drop guidance.

### Fixed

- Prevented selecting or deselecting a bubble from changing the context-toolbar height, refitting the canvas, or causing visible zoom and image-position jumps.
- Reduced oversized default bubbles on low-resolution media while preserving proportional sizing on larger images.
- Kept resize handles, tail handles, and selection outlines at a stable on-screen size across zoom levels.
- Prevented the Long Weekend Labs byline from clipping in the application header.
- Preserved the complete set of bubble styles and editor tools throughout the interface overhaul.

## v4.5.0 - 2026-08-05

### Added

- Comic Maker with hand-inked 4, 6, 7, and 8-panel page layouts, live layout tuning, right-to-left reading order, and nondestructive regeneration.
- Photo Collage with 2–9 photos, visual layout choices, multiple canvas orientations, shuffle, and editable named presets.
- Magnetic photo reordering while preserving in-frame crop dragging, mouse-wheel zoom, a 10–500% scale range, and Fit.
- Frame-specific lines, blur, and pixelate effects with a visible active-frame outline.
- Solid-color and blurred fill choices when a fitted image does not cover its frame.

### Changed

- Consolidated Comic and Collage controls into dedicated right-pane tabs with live sliders, concise tooltips, and editable background/frame colors.
- Renamed Manga Maker to Comic Maker and promoted the former experimental workspace into the main application.
- Restored the complete Windows x64 setup/portable and Linux x64 AppImage/DEB/RPM/portable release matrix.

### Fixed

- Restored video opening, playback, and timeline controls in normal and dual modes after using Comic or Collage mode.
- Kept generated pages fitted to the canvas after layout and orientation changes.
- Prevented page-mode inspectors, layers, and effects from colliding with normal editing controls.
- Fixed bidirectional image scaling so photos can shrink below their cover size.

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
