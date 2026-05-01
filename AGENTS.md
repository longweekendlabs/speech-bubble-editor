# Speech Bubble Editor — Agent Instructions

You are working on a Long Weekend Labs project. Follow these rules strictly.

## Read first every session
1. `PROJECT.md` — what this app is, stack, constraints, key decisions
2. `ROADMAP.md` — current state and active tasks

Confirm you've read both before writing any code. **Do not read the `archive/` folder** unless explicitly asked.

## Critical rules — do not violate

### Git & CI (cost protection)
- **Do not `git push`** unless explicitly told to with the word "push"
- **Do not merge to `main`** unless explicitly told to
- Work on the current branch. Create a new branch only if asked.
- For docs/config-only commits, append `[skip ci]` to the commit message
- Never force-push, never rewrite history
- Never trigger a release workflow manually

### Scope discipline
- Surgical edits only — do not refactor unrelated code
- Do not add dependencies without asking first
- Do not rename files, restructure folders, or change build config without asking
- If a task is bigger than expected, stop and report — don't expand scope silently

### Reporting done
- Always run the build/test command listed below before claiming done
- Update `ROADMAP.md` with what changed (one line under the relevant task)
- Do not push, do not open a PR, do not tag a release — just report

## ROADMAP.md auto-archive

Before writing any update to `ROADMAP.md`, count the non-blank lines.

**If `ROADMAP.md` has more than 150 non-blank lines, do this first:**

1. Stop. Do not edit `ROADMAP.md` yet.
2. Tell the user: *"ROADMAP.md is at [N] lines. I want to archive completed/stale entries, keeping the most recent ~40 lines of active and next-up work. OK to proceed?"*
3. Wait for explicit "yes" / "go" / "proceed" before continuing.
4. On approval:
   - Identify the oldest completed/done/shipped entries (status markers: ✅, `[x]`, "done", "shipped", "completed")
   - Cut them from `ROADMAP.md`
   - Append them to `archive/ROADMAP_archive.md` under a new heading: `## Archived YYYY-MM-DD`
   - If `archive/` doesn't exist, create it
   - The new `ROADMAP.md` should keep all active tasks, all next-up tasks, and ~40 lines total of recent context
5. Then proceed with the original update.

**Do not archive without explicit approval.** The 150-line check is a trigger, not permission.

## Archive folder
- `archive/` contains historical roadmap entries
- Do not read it during normal work
- Do not load it into context unprompted
- It exists for human reference only

## Stack
- Language: Python 3
- UI: PyQt6
- Video decode: OpenCV (`cv2`) + NumPy — lazy-imported, never at module top level
- Video export: FFmpeg (subprocess)
- Theme: QSS dark stylesheet (`theme/dark.qss`)
- Packaging: PyInstaller

## Build / test command
- TBD — fill in manually

## Performance constraints
- Cold startup target: < 2 seconds on a mid-spec machine
- Achieved by: lazy `cv2`/`numpy`, deferred `QFontComboBox` init, single-instance check before window build, font loading via `QTimer.singleShot`

## Project-specific notes
- No separate windows — everything lives inside the single main window; inspector is a docked sidebar, not a floating panel
- Lazy imports for cv2/numpy — imported inside functions that need them, never at module top level; non-negotiable for startup performance
- Single-instance check before `MainWindow()` construction — fail fast on duplicate launch
- All property changes go through undo commands — style, color, font, text color, opacity all undoable via Ctrl+Z
- QSS dark theme — single `theme/dark.qss` file; no in-code QPalette manipulation
- `constants.py` — single source of truth for `IMAGE_EXTENSIONS`, `VIDEO_EXTENSIONS`, undo merge IDs, and other shared constants
- Export at source resolution — always render at native pixmap/video dimensions, never at display/zoom size
- `PhotoScene` is a God Object (known) — do not extend it further; refactor toward `AppModel` + `EditorController` incrementally, not all at once
