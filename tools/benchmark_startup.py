"""Time process launch through first Qt window paint, including extraction.

Examples:
  python tools/benchmark_startup.py .venv/bin/python main.py
  python tools/benchmark_startup.py dist/SpeechBubbleEditor/SpeechBubbleEditor

No filesystem-cache flushing is attempted. Report first and subsequent runs;
these are local measurements, not another OS's cold-launch guarantees.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--runs', type=int, default=3)
parser.add_argument('command', nargs='+')
args = parser.parse_args()
results = []
with tempfile.TemporaryDirectory(prefix='sbe-startup-') as directory:
    for index in range(args.runs):
        report = Path(directory) / f'{index}.json'
        env = dict(os.environ)
        env.setdefault('QT_QPA_PLATFORM', 'offscreen')
        env['SBE_LAUNCH_STARTED_NS'] = str(time.perf_counter_ns())
        subprocess.run([*args.command, '--startup-test', str(report)], env=env,
                       check=True, timeout=60)
        results.append(json.loads(report.read_text(encoding='utf-8')))
print(json.dumps({'runs': results, 'median_ms': statistics.median(
    row['launch_to_first_paint_ms'] for row in results)}, indent=2))
