"""Opt-in integration check for the actual frozen app on each release OS.

SpeechBubbleEditor --smoke-test /absolute/path/report.json
The check uses temporary fixtures, never user media or saved preferences.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import traceback


def run_smoke_check(app, window, report_path):
    report = {'ok': False, 'qt_platform': app.platformName(), 'checks': []}
    result = 1
    try:
        import sys
        report['video_imported_on_launch'] = 'cv2' in sys.modules
        if report['video_imported_on_launch']:
            raise AssertionError('Video dependency imported during startup')
        from PyQt6.QtGui import QColor, QFontDatabase, QImage
        from PyQt6.QtCore import QEventLoop, QTimer
        from export import _find_ffmpeg, _render_single_photo
        from video_player import VideoPlayer
        import subprocess

        def import_media(path, target='left'):
            loop = QEventLoop()
            completed, failures = [], []
            def loaded(*args):
                completed.append(args)
                loop.quit()
            def failed(*args):
                failures.append(args)
                loop.quit()
            signal = (window.controller.media_loaded if target == 'left'
                      else window.controller.right_media_loaded)
            signal.connect(loaded)
            window.controller.import_failed.connect(failed)
            timer = QTimer(loop)
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            timer.start(30000)
            try:
                window.controller.open_media_async(str(path), target)
                loop.exec()
                if failures or not completed:
                    raise AssertionError(f'Background import failed: {failures or "timeout"}')
            finally:
                timer.stop()
                signal.disconnect(loaded)
                window.controller.import_failed.disconnect(failed)

        for family in ('Inter', 'Comic Neue', 'Klee One'):
            if family not in QFontDatabase.families():
                raise AssertionError(f'Missing bundled font: {family}')
        report['checks'].append('bundled fonts')
        with tempfile.TemporaryDirectory(prefix='sbe-smoke-') as directory, ExitStack() as cleanup:
            # Windows cannot delete fixtures still held by VideoCapture. Close
            # workers and scene media before TemporaryDirectory removes files.
            cleanup.callback(window.scene.reset_project)
            cleanup.callback(window.controller.shutdown)
            temp = Path(directory)
            source = QImage(640, 480, QImage.Format.Format_RGB32)
            source.fill(QColor('#63758a'))
            for extension in ('png', 'jpg', 'webp'):
                path = temp / f'photo.{extension}'
                if not source.save(str(path)) or QImage(str(path)).isNull():
                    raise AssertionError(f'Image codec failed: {extension}')
            import_media(temp / 'photo.png')
            bubble = window.controller.add_bubble(320, 240, style='cloud')
            bubble.set_text('Packaged build check')
            window.controller.undo_stack.undo()
            if bubble.scene() is not None:
                raise AssertionError('Undo failed')
            window.controller.undo_stack.redo()
            if bubble.scene() is not window.scene:
                raise AssertionError('Redo failed')
            rendered = _render_single_photo(window.scene, window.scene._photo_item)
            if rendered.size() != source.size() or rendered == source:
                raise AssertionError('Photo export lost the bubble or resolution')
            report['checks'].append('PNG/JPEG/WebP, bubble, undo/redo, full-size export')
            window.scene.enable_manga_mode()
            window.scene.load_manga_panel(0, str(temp / 'photo.png'))
            if not window.scene._manga_panels[0].has_image():
                raise AssertionError('Comic panel load failed')
            window.scene.disable_manga_mode()
            window.scene.enable_collage_mode()
            if not window.scene.is_collage_mode():
                raise AssertionError('Collage mode failed')
            window.scene.disable_collage_mode()
            report['checks'].append('comic and collage')

            ffmpeg = _find_ffmpeg()
            if not ffmpeg:
                raise AssertionError('FFmpeg missing')
            if hasattr(sys, '_MEIPASS') and Path(ffmpeg).parent != Path(sys._MEIPASS):
                raise AssertionError('Frozen app fell back to system FFmpeg')
            clip = temp / 'clip.mp4'
            subprocess.run([ffmpeg, '-v', 'error', '-f', 'lavfi', '-i',
                            'color=c=blue:s=160x120:r=10:d=1', '-f', 'lavfi',
                            '-i', 'sine=frequency=440:duration=1', '-c:v',
                            'mpeg4', '-c:a', 'aac', '-shortest', str(clip)],
                           check=True, capture_output=True, timeout=30)
            player = VideoPlayer()
            try:
                if not player.load(str(clip)) or player.get_frame_ndarray(0) is None:
                    raise AssertionError('Video decoding failed')
                # The GUI-free OpenCV wheel must still encode video.
                import cv2
                frame = player.get_frame_ndarray(0)
                output = temp / 'encoded.mp4'
                writer = cv2.VideoWriter(str(output),
                                         cv2.VideoWriter_fourcc(*'mp4v'),
                                         10, (160, 120))
                try:
                    if not writer.isOpened():
                        raise AssertionError('Video encoder missing')
                    writer.write(frame)
                finally:
                    writer.release()
                subprocess.run([ffmpeg, '-v', 'error', '-i', str(output),
                                '-i', str(clip), '-map', '0:v', '-map', '1:a',
                                '-c', 'copy', '-shortest', str(temp / 'audio.mp4')],
                               check=True, capture_output=True, timeout=30)
            finally:
                player.release()
            report['checks'].append('bundled FFmpeg, video decode/encode, audio mux')
            import_media(clip)
            if not window.scene.has_video():
                raise AssertionError('Background video import failed')
            window.scene.enable_dual_mode()
            import_media(clip, 'right')
            old_right = window.scene.video_player_right
            import_media(temp / 'photo.png', 'right')
            if old_right.is_loaded() or window.scene.video_player_right is not None:
                raise AssertionError('Photo did not release previous right video')
            report['checks'].append('background photo/video import and dual replacement')
            app.processEvents()
            screenshot = Path(report_path).with_suffix('.png')
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(screenshot))
        report['ok'] = True
        result = 0
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        destination = Path(report_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
        window.close()
        app.exit(result)
