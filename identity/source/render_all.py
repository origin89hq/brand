"""Compatibility entry point for the shared brand image rebuild."""
from pathlib import Path
import subprocess,sys
subprocess.run([sys.executable,str(Path(__file__).resolve().parents[2]/'source/rebuild_images.py'),'--resume'],check=True)
