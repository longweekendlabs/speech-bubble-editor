"""
version.py — Single source of truth for the application version and branding.

History:
  v2.0.0 — Video support (MP4, AVI, WebM, MOV, MKV), video scrubber,
            trim / cut / reverse editing, dual video mode, audio-preserving
            export via FFmpeg, app icon, Long Weekend Labs branding.
  v2.1.0 — LRU frame cache for responsive scrubbing; playback respects
            trim markers; export pre-renders bubble overlay once (fast);
            export dialog is modal; player stops before export; welcome
            screen with click-to-open; + Bubble toolbar button (Ctrl+B);
            Instagram-style slim semi-transparent scrim/caption bar;
            scrim bubble compact height; shape preserved on style switch;
            bubbles clamped to canvas; meme bar resize fix; lock aspect
            ratio on by default.
  v2.1.10 — Production release: Caption bubble style (stroke text overlay,
             Anton font, 8-direction outline, optional fill background);
             step frame / first / last frame controls; time label shows
             trim selection range; reverse playback live in GUI (not just
             export); meme bar position fixed after resize; dual mode right
             pane layout fixed (placeholder tracked through all moves).
"""

__version__  = "2.1.10"
__app_name__ = "Speech Bubble Editor"
__org_name__ = "Long Weekend Labs"
__copyright__ = "© 2026 Long Weekend Labs"
