"""Run the frozen integration check with a timeout on Windows/Linux/macOS."""
import json
import os
from pathlib import Path
import subprocess
import sys

executable = Path(sys.argv[1]).resolve()
report = Path(sys.argv[2]).resolve()
report.parent.mkdir(parents=True, exist_ok=True)
report.unlink(missing_ok=True)
env = dict(os.environ, QT_QPA_PLATFORM='offscreen',
           SBE_DISABLE_SAVED_COLLAGE_DEFAULTS='1')
process = subprocess.run([str(executable), '--smoke-test', str(report)],
               env=env, timeout=120)
if not report.is_file():
    log = Path.home() / 'speechbubble_debug.log'
    if log.is_file():
        print(log.read_text(encoding='utf-8', errors='replace')[-16000:])
    raise SystemExit(f'Frozen app exited {process.returncode} without a smoke report')
result = json.loads(report.read_text(encoding='utf-8'))
print(json.dumps(result, indent=2))
if process.returncode or not result.get('ok'):
    raise SystemExit(1)
