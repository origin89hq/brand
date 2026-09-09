"""Use the shared-source handoff pipeline; prevent a stale standalone Buddy kit."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
subprocess.run([sys.executable,ROOT/'source/package_brand.py'],check=True)
