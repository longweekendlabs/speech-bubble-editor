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
subprocess.run([str(executable), '--smoke-test', str(report)],
               env=env, check=True, timeout=120)
result = json.loads(report.read_text(encoding='utf-8'))
print(json.dumps(result, indent=2))
if not result.get('ok'):
    raise SystemExit(1)
